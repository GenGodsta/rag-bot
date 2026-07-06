from mcp.server.fastmcp import FastMCP
import httpx, os
from dotenv import load_dotenv
load_dotenv()

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
        data = resp.json()
    return [
        {"title": r["title"], "snippet": r.get("snippet", ""), "url": r["link"]}
        for r in data.get("organic", [])
    ]

@mcp.tool()
async def search_wikipedia(query: str, num_results: int = 3) -> list[dict]:
    async with httpx.AsyncClient() as client:
        search_resp = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query, "format": "json"},
        )
        titles = [r["title"] for r in search_resp.json()["query"]["search"][:num_results]]
        results = []
        for title in titles:
            summary_resp = await client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
            )
            if summary_resp.status_code == 200:
                s = summary_resp.json()
                results.append({"title": s["title"], "snippet": s.get("extract", ""), "url": s.get("content_urls", {}).get("desktop", {}).get("page", "")})
    return results

@mcp.tool()
async def web_research(query: str) -> list[dict]:
    google_results = await search_google(query)
    wiki_results = await search_wikipedia(query)
    return wiki_results + google_results

if __name__ == "__main__":
    mcp.run(transport="stdio")