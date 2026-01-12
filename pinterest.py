import aiohttp
import json
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

async def resolve_pin_url(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as r:
            return str(r.url)

async def fetch_pin(url):
    if "pin.it" in url:
        url = await resolve_pin_url(url)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "lxml")

    images = list({
        img["src"]
        for img in soup.find_all("img")
        if img.get("src") and ("originals" in img["src"] or "736x" in img["src"])
    })

    video = None
    for script in soup.find_all("script"):
        if script.string and "video_list" in script.string:
            try:
                data = json.loads(
                    re.search(r'\{.*\}', script.string, re.S).group()
                )
                pins = data["props"]["initialReduxState"]["pins"]
                pin_id = next(iter(pins))
                videos = pins[pin_id]["videos"]["video_list"]

                video = max(videos.values(), key=lambda x: x["width"])["url"]
                break
            except:
                pass

    return images, video
