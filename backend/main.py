"""
main.py — LangGraph Orchestration + CLI
========================================
Graph:
  START → load_memory → agent → validate → human_review → save → END

  Auto-reject loop:  validate → agent (fail, max 3 retries with feedback)
  Human-reject loop: human_review → agent (max 3 retries with feedback)

Usage:
  python main.py --topic "LangGraph overview"
  python main.py --topic "LangGraph overview" --hitl
  python main.py --topic "AI frameworks" --parallel
  python main.py --topic "AI frameworks" --parallel --hitl
"""

import asyncio
import argparse
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent import create_research_agent, get_model, AgentOutput, print_report
from memory import get_memory_store

load_dotenv()

MAX_RETRIES = 3
OUTPUTS_DIR = Path("outputs")


def _url_reachable(url: str, timeout: float = 3.0) -> bool:
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code != 404
    except requests.exceptions.ConnectionError:
        return False  # domain doesn't resolve → invented
    except requests.exceptions.InvalidURL:
        return False
    except Exception:
        return True  # timeout / SSL / other 4xx → domain is real, page may just be protected


def _check_urls(sources) -> list[str]:
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_url_reachable, src.url): src.url for src in sources}
        return [url for future, url in futures.items() if not future.result()]


# ═══════════════════════════════════════════════════════
# 1. State
# ═══════════════════════════════════════════════════════


class AgentState(TypedDict):
    task: str
    past_memories: str
    result: Optional[AgentOutput]
    feedback: Optional[str]
    status: str
    retry_count: int


# ═══════════════════════════════════════════════════════
# 2. Nodes
# ═══════════════════════════════════════════════════════


def load_memory_node(state: AgentState) -> dict:
    """Node 1: Query vector memory for relevant context."""
    print(f"🧠 [Memory] Querying for: '{state['task']}'...")
    store = get_memory_store()
    memories = store.query(topic=state["task"], top_k=5)
    context = store.format_context(memories)
    if context:
        print("🧠 [Memory] Relevant context found.")
    else:
        print("🧠 [Memory] No relevant context found.")
    return {"past_memories": context}


async def agent_node(state: AgentState) -> dict:
    """Node 2: Two-phase agent — research via tool calls, then format into schema."""
    parts = [f"Task: {state['task']}"]
    if state.get("past_memories"):
        parts.append(f"--- PAST RESEARCH ---\n{state['past_memories']}")
    if state.get("feedback"):
        parts.append(f"--- FEEDBACK (fix this) ---\n{state['feedback']}")
    full_prompt = "\n\n".join(parts)

    # Phase 1: gather research with free web_search calls (no structured output)
    print("🤖 [Agent] Researching...")
    research_agent = create_research_agent()
    response = await research_agent.ainvoke(
        {"messages": [{"role": "user", "content": full_prompt}]}
    )
    messages = response.get("messages", [])
    last_content = messages[-1].content if messages else ""
    research_text = last_content if isinstance(last_content, str) else str(last_content)
    print(f"🔍 [Agent] Research gathered ({len(research_text)} chars)")

    if not research_text.strip():
        print("⚠️  [Agent] No research content returned.")
        return {
            "result": None,
            "status": "pending",
            "feedback": "No research content. Call web_search to gather real data.",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    # Phase 2: format research text into AgentOutput schema
    print("📐 [Agent] Formatting output...")
    format_prompt = (
        "Convert the research below into the required JSON schema.\n\n"
        "For the `sections` field, create 4-6 meaningfully named sections (e.g. 'Core Architecture', 'Key Features', 'Use Cases', 'Limitations') "
        "with detailed content for each — do NOT just copy key_findings into sections.\n\n"
        "IMPORTANT: Only include URLs that appear VERBATIM in the research — do not invent or modify URLs.\n\n"
        f"Research:\n{research_text}"
    )
    structured = await get_model().with_structured_output(AgentOutput).ainvoke(format_prompt)

    return {
        "result": structured,
        "status": "pending",
        "feedback": None,
        "retry_count": state.get("retry_count", 0) + 1,
    }


def validate_node(state: AgentState) -> dict:
    """Node 3: Validate agent output before human review."""
    result = state.get("result")

    if result is None:
        print("❌ [Validate] No result generated.")
        return {
            "status": "rejected",
            "feedback": "Agent returned no result. Try again.",
        }
    issues = []
    if len(result.sources) < 1:
        issues.append(f"Too few sources ({len(result.sources)}), need at least 1.")
    if len(result.key_findings) < 2:
        issues.append(f"Too few key findings ({len(result.key_findings)}), need at least 2.")

    if result.sources:
        bad_urls = _check_urls(result.sources)
        if bad_urls:
            issues.append(
                "Unreachable URLs (likely invented) — remove them: "
                + ", ".join(bad_urls)
            )

    if issues:
        feedback = (
            "Report failed validation:\n"
            + "\n".join(f"- {i}" for i in issues)
            + "\n\nCall web_search to gather real sources before returning."
        )
        print(f"❌ [Validate] {feedback}")
        return {"status": "rejected", "feedback": feedback}

    print("✅ [Validate] Passed.")
    return {}


def human_review_node(state: AgentState) -> dict:
    """Node 4: Auto-approve or interrupt for human review (--hitl)."""
    if state["status"] == "pending":
        return {"status": "approved"}
    return {}


def save_node(state: AgentState) -> dict:
    """Node 5: Save result to outputs/ and update vector memory."""
    result = state["result"]

    # Fallback: derive sections from key_findings if agent left sections empty
    if not result.sections and result.key_findings:
        result.sections = {f"Finding {i}": finding for i, finding in enumerate(result.key_findings, 1)}

    # Save to outputs/
    OUTPUTS_DIR.mkdir(exist_ok=True)
    slug = state["task"][:50].lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUTS_DIR / f"{slug}_{timestamp}.json"
    output_path.write_text(
        json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"📄 [Save] Output → {output_path}")

    # Update vector memory — only index reports that passed validation
    if result.sources:
        store = get_memory_store()
        num_chunks = store.save(report=result, topic=state["task"])
        print(f"💾 [Memory] Indexed {num_chunks} chunks.")
    else:
        print("⚠️  [Memory] Skipping index — report has no sources.")

    return {"status": "approved"}


# ═══════════════════════════════════════════════════════
# 3. Conditional Edge
# ═══════════════════════════════════════════════════════


def route_after_review(state: AgentState) -> str:
    if state["status"] == "approved":
        return "save"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        print(f"⚠️  [Route] Max retries reached — saving best result.")
        return "save"
    return "agent"


# ═══════════════════════════════════════════════════════
# 4. Build Graph
# ═══════════════════════════════════════════════════════


def build_graph(use_hitl: bool = False):
    workflow = StateGraph(AgentState)

    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("save", save_node)

    workflow.add_edge(START, "load_memory")
    workflow.add_edge("load_memory", "agent")
    workflow.add_edge("agent", "validate")
    workflow.add_edge("validate", "human_review")
    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {"save": "save", "agent": "agent"},
    )
    workflow.add_edge("save", END)

    interrupt_before = ["human_review"] if use_hitl else []
    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=interrupt_before,
    )


# ═══════════════════════════════════════════════════════
# 5. Runners
# ═══════════════════════════════════════════════════════


def _init_state(task: str) -> AgentState:
    return {
        "task": task,
        "past_memories": "",
        "result": None,
        "feedback": None,
        "status": "pending",
        "retry_count": 0,
    }


async def run_without_hitl(task: str) -> AgentOutput:
    app = build_graph(use_hitl=False)
    config = {"configurable": {"thread_id": "agent-1"}}
    final = await app.ainvoke(_init_state(task), config=config)
    return final["result"]


async def run_with_hitl(task: str) -> AgentOutput:
    app = build_graph(use_hitl=True)
    config = {"configurable": {"thread_id": "agent-1"}}

    await app.ainvoke(_init_state(task), config=config)

    while True:
        snapshot = app.get_state(config)
        result = snapshot.values.get("result")

        print(f"\n{result}")
        print("\n" + "─" * 50)
        decision = (
            input("✅ Approve (a) / ❌ Reject with feedback (r): ").strip().lower()
        )

        if decision == "a":
            app.update_state(config, {"status": "approved"}, as_node="human_review")
            await app.ainvoke(None, config=config)
            break
        else:
            feedback = input("📝 Enter feedback: ").strip()
            app.update_state(
                config,
                {"status": "rejected", "feedback": feedback},
                as_node="human_review",
            )
            await app.ainvoke(None, config=config)
            snapshot = app.get_state(config)
            if snapshot.next == ():
                break

    return app.get_state(config).values["result"]


# ═══════════════════════════════════════════════════════
# 6. CLI
# ═══════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main",
        description="Research Agent — LangGraph orchestration",
        epilog="""
examples:
  python main.py --task "LangGraph overview"
  python main.py --task "LangGraph overview" --hitl
  python main.py --task "AI frameworks" --parallel
  python main.py --task "AI frameworks" --parallel --hitl
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--task", required=True, help="Research task")
    parser.add_argument(
        "--hitl", action="store_true", help="Enable human-in-the-loop review"
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Use parallel subagents"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.hitl:
        result = asyncio.run(run_with_hitl(args.task))
    else:
        result = asyncio.run(run_without_hitl(args.task))

    print_report(result)


if __name__ == "__main__":
    main()
