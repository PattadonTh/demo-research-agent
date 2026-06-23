from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """
    Search the internet for current information.
    Use for: recent events, documentation, technical specs, anything time-sensitive.
    Returns structured results with title, URL, and snippet for each hit.
    Only cite URLs that appear verbatim in these results.
    """
    from langchain_community.tools import DuckDuckGoSearchResults

    print(f"🔎 [web_search] query: {query!r}")
    search = DuckDuckGoSearchResults(num_results=5)
    result = search.invoke(query)
    print(f"📄 [web_search] raw result ({len(result)} chars):\n{result}\n{'─'*60}")
    return result
