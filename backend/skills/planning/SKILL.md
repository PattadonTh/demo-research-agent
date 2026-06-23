---
name: planning
description: Query planning discipline for research tasks — before calling any search tool, decompose the topic into targeted sub-queries that cover different angles (overview, technical depth, use cases, comparisons, recent updates). Trigger proactively whenever a research task starts.
---

# Research Query Planning

Decompose the topic before searching. Broad queries return noise; targeted queries return signal.

## Steps

1. **Identify angles** — break the topic into 3-5 distinct sub-topics (e.g. for "LangGraph overview": architecture, key features, use cases, comparisons, recent releases).
2. **Write one query per angle** — each query should be specific enough to return focused results.
3. **Order by dependency** — start with the overview query, then drill into specifics.
4. **Execute the queries** — call web_search for each planned query before synthesizing.

## Rules

- Plan mentally before the first web_search call — no need to write anything to a file.
- Aim for 3-5 queries minimum to get broad coverage.
- Avoid redundant queries — each should target a different aspect of the topic.
- Adjust the plan if early results reveal unexpected angles worth exploring.
