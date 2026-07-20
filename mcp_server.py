from mcp.server.fastmcp import FastMCP
import httpx, os
from dotenv import load_dotenv
from pathlib import Path
import sys
from pathlib import Path
import json
import asyncio

LOG_FILE = Path(__file__).resolve().parent / "mcp_debug.log"

def debug_log(msg: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    with open(Path(__file__).resolve().parent / "debug_path_check.txt", "w") as f:
        f.write(str(LOG_FILE))
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

mcp = FastMCP("web-research")

SERPER_API_KEY = os.environ["SERPER_API_KEY"]

@mcp.tool()
async def search_google(query: str, num_results: int = 5) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Serper failed [{resp.status_code}]: {resp.text[:300]}")
        data = resp.json()
        debug_log(f"[search_google] raw response keys: {list(data.keys())}, organic count: {len(data.get('organic', []))}")
        debug_log(f"[search_google] snippets: {[r.get('snippet','')[:100] for r in data.get('organic', [])]}")
        if "organic" not in data:
            debug_log(f"[search_google] FULL response for debugging: {data}")
    return [
        {"title": r["title"], "snippet": r.get("snippet", ""), "url": r["link"]}
        for r in data.get("organic", [])
    ]

WIKI_HEADERS = {
    "User-Agent": "rag-bot/1.0 (https://github.com/GenGodsta/rag-bot; contact: your_email@example.com)"
}

async def _fetch_wiki_extract(client: httpx.AsyncClient, title: str) -> dict | None:
    content_resp = await client.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "prop": "extracts",
            "titles": title,
            "explaintext": True,
            "format": "json",
        },
    )
    if content_resp.status_code != 200:
        debug_log(f"[search_wikipedia] content_resp failed [{content_resp.status_code}] for title={title!r}")
        return None

    pages = content_resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract", "")
        if extract:
            debug_log(f"[search_wikipedia] title={page.get('title', title)!r} extract_len={len(extract)}")
            return {
                "title": page.get("title", title),
                "snippet": extract[:5000],
                "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            }
    return None

@mcp.tool()
async def search_wikipedia(query: str, num_results: int = 3) -> list[dict]:
    async with httpx.AsyncClient(headers=WIKI_HEADERS) as client:
        search_resp = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query, "format": "json"},
        )
        if search_resp.status_code != 200:
            raise RuntimeError(f"Wikipedia search failed [{search_resp.status_code}]: {search_resp.text[:300]}")
        titles = [r["title"] for r in search_resp.json()["query"]["search"][:num_results]]
        debug_log(f"[search_wikipedia] query={query!r} matched titles: {titles}")
        fetched = await asyncio.gather(*[_fetch_wiki_extract(client, title) for title in titles])
        results = [r for r in fetched if r is not None]

    debug_log(f"[search_wikipedia] returning {len(results)} results for query={query!r}")
    return results

@mcp.tool()
async def web_research(query: str, num_results: int = 15) -> str:
    google_results, wiki_results = await asyncio.gather(
        search_google(query, num_results=max(num_results - 3, 5)),
        search_wikipedia(query, num_results=3),
    )
    debug_log(f"[web_research] query={query!r} google={len(google_results)} wiki={len(wiki_results)}")
    return json.dumps(wiki_results + google_results)

if __name__ == "__main__":
    mcp.run(transport="stdio")