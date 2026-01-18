import aiohttp
import asyncio
import json
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

async def resolve_redirect(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as r:
            return str(r.url)

async def fetch_pin(url):
    # Resolve pin.it
    if "pin.it" in url:
        url = await resolve_redirect(url)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as r:
            if r.status != 200:
                return [], None, f"HTTP_{r.status}"
            html = await r.text()

    soup = BeautifulSoup(html, "html.parser")

    images = set()
    video = None

    # 🔹 IMAGE EXTRACTION (100% reliable)
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if "pinimg.com" in src:
            src = re.sub(r"/\d+x/", "/originals/", src)
            images.add(src)

    # 🔹 VIDEO EXTRACTION (REAL METHOD)
    for script in soup.find_all("script"):
        if script.string and "__PWS_DATA__" in script.string:
            match = re.search(r'__PWS_DATA__\s*=\s*({.*?});', script.string, re.S)
            if not match:
                continue

            data = json.loads(match.group(1))

            def walk(obj):
                nonlocal video
                if isinstance(obj, dict):
                    if "video_list" in obj:
                        best = max(
                            obj["video_list"].values(),
                            key=lambda x: x.get("width", 0)
                        )
                        video = best.get("url")
                    for v in obj.values():
                        walk(v)
                elif isinstance(obj, list):
                    for i in obj:
                        walk(i)

            walk(data)

    return list(images), video, None


# 🔹 TEST
async def main():
    url = "https://pin.it/XXXXXXX"  # put real pin.it or pinterest pin
    images, video, error = await fetch_pin(url)

    print("\nIMAGES FOUND:", len(images))
    for i in images[:3]:
        print(i)

    print("\nVIDEO URL:")
    print(video)

    print("\nERROR:", error)

if __name__ == "__main__":
    asyncio.run(main())
