import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

async def fetch_pin(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, timeout=20) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "lxml")

    images = list({img["src"] for img in soup.find_all("img") 
                   if img.get("src") and "originals" in img["src"]})

    video = None
    meta_video = soup.find("meta", property="og:video")
    if meta_video:
        video = meta_video["content"]

    return images, video
