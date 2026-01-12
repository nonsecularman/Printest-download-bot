import aiohttp
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# 🔹 short link resolve (pin.it → pinterest.com/pin/...)
async def resolve_pin_url(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True, timeout=20) as resp:
            return str(resp.url)

async def fetch_pin(url):
    # 🔥 pin.it support
    if "pin.it" in url:
        url = await resolve_pin_url(url)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, timeout=20) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "lxml")

    # 🔥 images (high quality)
    images = list({
        img["src"]
        for img in soup.find_all("img")
        if img.get("src") and (
            "originals" in img["src"] or "736x" in img["src"]
        )
    })

    # 🔥 video support
    video = None
    meta_video = soup.find("meta", property="og:video")
    if meta_video and meta_video.get("content"):
        video = meta_video["content"]

    return images, video
