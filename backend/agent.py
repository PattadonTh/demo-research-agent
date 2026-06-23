"""
agent.py — Deep Agent Definition
==================================
Sections:
  1. Output Schema      — AgentOutput
  2. Model              — get_model()
  3. Paths & Setup      — SKILLS_DIR
  4. System Prompt      — SYSTEM_PROMPT
  5. Subagents          — get_subagent()
  6. Factory Functions  — create_research_agent()
  7. Print helper       — print_report()
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from tools import web_search
from typing import Literal

load_dotenv()

# ═══════════════════════════════════════════════════════
# 1. Output Schema
# ═══════════════════════════════════════════════════════


class Source(BaseModel):
    """Represents a single source used in the research report."""

    title: str = Field(description="Article/page title")
    url: str = Field(description="Source URL")
    relevance: Literal["high", "medium", "low"] = Field(
        description="How relevant this source is to the research topic"
    )


class AgentOutput(BaseModel):
    """
    Structured output schema for the research agent.
    The agent must return a valid JSON object matching this schema.
    """

    title: str = Field(description="Report title")
    summary: str = Field(description="Executive summary (2-3 sentences)")
    key_findings: list[str] = Field(description="List of 3-7 key findings")
    sections: dict[str, str] = Field(
        description="Section name → detailed content (e.g. {'Overview': '...', 'Trends': '...'})"
    )
    sources: list[Source] = Field(description="All sources used, with relevance rating")
    limitations: str = Field(description="Limitations of this research")


# ═══════════════════════════════════════════════════════
# 2. Model
# ═══════════════════════════════════════════════════════


def get_model(
    model: str = os.getenv("MODEL", "claude-haiku-4-5"),
    provider: str = os.getenv("PROVIDER", "anthropic"),
    max_retries: int = 3,
) -> BaseChatModel:
    """
    Initialize and return the LLM model.
    Defaults to Claude Haiku 4-5 — fast and cost-effective for research tasks.
    """
    return init_chat_model(
        model,
        model_provider=provider,
        max_retries=max_retries,
    )


# ═══════════════════════════════════════════════════════
# 3. Paths & Setup
# ═══════════════════════════════════════════════════════

SKILLS_DIR = Path(__file__).parent / "skills"


# ═══════════════════════════════════════════════════════
# 4. System Prompt
# ═══════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert research analyst.

## Process
1. Review PAST RESEARCH context if any — use it as background only, not as your primary source.
2. If PAST RESEARCH contains a sources list, copy those URLs verbatim into your sources list.
3. If past research is missing or insufficient, read /skills/planning/SKILL.md and follow it to plan and execute your searches.
4. Read /skills/reflection/SKILL.md and verify your output before returning.

## Rules
- Only include URLs that appeared verbatim in a web_search result or in PAST RESEARCH context — do not construct, guess, or modify URLs.
"""


# ═══════════════════════════════════════════════════════
# 5. Subagents (optional)
# ═══════════════════════════════════════════════════════


def get_subagent() -> dict:
    return {
        "name": "researcher",
        "description": "Research a specific subtopic in parallel.",
        "system_prompt": "Focused researcher. Search 2-3 queries. Return findings AND all source URLs.",
        "tools": [web_search],
        "model": f"{os.getenv('PROVIDER', 'anthropic')}:{os.getenv('MODEL', 'claude-haiku-4-5')}",
    }


# ═══════════════════════════════════════════════════════
# 6. Factory Function
# ═══════════════════════════════════════════════════════


def _make_backend():
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir=str(SKILLS_DIR), virtual_mode=True),
        },
    )


def create_research_agent(use_subagents: bool = False):
    """Phase-1 agent: calls web_search freely, returns a text research summary."""
    subagents = [get_subagent()] if use_subagents else None
    return create_deep_agent(
        model=get_model(),
        tools=[web_search],
        system_prompt=SYSTEM_PROMPT,
        backend=_make_backend(),
        skills=["/skills"],
        subagents=subagents,
        interrupt_on=None,
        checkpointer=None,
    )



# ═══════════════════════════════════════════════════════
# 7. Print helper
# ═══════════════════════════════════════════════════════


def print_report(report: AgentOutput) -> None:
    print(f"\n{'='*60}")
    print(f"📋 {report.title}")
    print(f"{'='*60}")
    print(f"\n📌 Summary\n{report.summary}")
    print(f"\n🔍 Key Findings")
    for i, f in enumerate(report.key_findings, 1):
        print(f"  {i}. {f}")
    if report.sections:
        print(f"\n📖 Sections")
        for name, content in report.sections.items():
            print(f"\n  ── {name} ──")
            print(f"  {content[:300]}{'...' if len(content) > 300 else ''}")
    print(f"\n⚠️  Limitations\n{report.limitations}")
    print(f"\n🔗 Sources ({len(report.sources)})")
    badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}
    for src in report.sources:
        print(f"  {badge[src.relevance]} {src.title}\n     {src.url}")
