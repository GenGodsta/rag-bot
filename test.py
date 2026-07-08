import httpx, os
from dotenv import load_dotenv
load_dotenv()

resp = httpx.post(
    "https://google.serper.dev/search",
    headers={"X-API-KEY": os.environ["SERPER_API_KEY"], "Content-Type": "application/json"},
    json={"q": "test query", "num": 5},
)
print(resp.status_code)
print(resp.text[:500])