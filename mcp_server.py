from mcp.server.fastmcp import FastMCP
import httpx, os
from dotenv import load_dotenv
from pathlib import Path

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
    return [
        {"title": r["title"], "snippet": r.get("snippet", ""), "url": r["link"]}
        for r in data.get("organic", [])
    ]

WIKI_HEADERS = {
    "User-Agent": "rag-bot/1.0 (https://github.com/GenGodsta/rag-bot; contact: your_email@example.com)"
}

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
        results = []
        for title in titles:
            summary_resp = await client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
            )
            if summary_resp.status_code == 200:
                s = summary_resp.json()
                results.append({
                    "title": s["title"],
                    "snippet": s.get("extract", ""),
                    "url": s.get("content_urls", {}).get("desktop", {}).get("page", "")
                })
    return results

@mcp.tool()
async def web_research(query: str, num_results: int = 15) -> list[dict]:
    google_results = await search_google(query, num_results=max(num_results - 3, 5))
    wiki_results = await search_wikipedia(query, num_results=3)
    return wiki_results + google_results

@mcp.tool()
async def web_research(query: str) -> list[dict]:
    google_results = await search_google(query)
    wiki_results = await search_wikipedia(query)
    return wiki_results + google_results

if __name__ == "__main__":
    mcp.run(transport="stdio")