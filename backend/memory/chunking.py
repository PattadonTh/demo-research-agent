import uuid


def make_id(topic: str, chunk_type: str, suffix: str = "") -> str:
    base = f"{topic}::{chunk_type}::{suffix}".lower().replace(" ", "_")
    return base[:80] + "::" + str(uuid.uuid5(uuid.NAMESPACE_DNS, base))


def chunk_report(report, topic: str) -> list[dict]:
    """
    Chunk an AgentOutput into one vector per semantic field for precise retrieval.

    Splitting by field means a query like "what sources were used" hits the
    sources chunk, not the whole JSON blob — retrieval quality is much better
    than treating the report as a single flat string.
    """
    chunks = []

    def add(chunk_type: str, text: str):
        if text.strip():
            chunks.append({
                "id": make_id(topic, chunk_type, "0"),
                "text": f"Topic: {topic}\n{text.strip()}",
                "metadata": {"topic": topic, "chunk_type": chunk_type, "index": 0},
            })

    add("title", report.title)
    add("summary", report.summary)

    if report.key_findings:
        add("key_findings", "\n".join(f"- {f}" for f in report.key_findings))

    for section_name, content in (report.sections or {}).items():
        chunks.append({
            "id": make_id(topic, "section", section_name),
            "text": f"Topic: {topic}\nSection — {section_name}:\n{content.strip()}",
            "metadata": {"topic": topic, "chunk_type": "section", "index": section_name},
        })

    if report.sources:
        sources_text = "\n".join(
            f"- [{s.relevance}] {s.title} {s.url}" for s in report.sources
        )
        add("sources", sources_text)

    if report.limitations:
        add("limitations", report.limitations)

    return chunks
