import aiohttp
import json
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# 🔹 resolve pin.it
async def resolve_pin_url(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as r:
            return str(r.url), await r.text()

# 🔹 extract first real /pin/ link from discover page
def extract_first_pin(html: str):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/pin/"):
            return "https://www.pinterest.com" + href
    return None


async def fetch_pin(url):
    html = None

    # 🔥 pin.it handling
    if "pin.it" in url:
        url, html = await resolve_pin_url(url)

    # ❌ not a direct pin → try extracting one
    if "/pin/" not in url:
        if not html:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url) as r:
                    html = await r.text()

        pin_url = extract_first_pin(html)
        if not pin_url:
            return [], None, "NO_PIN_FOUND"

        url = pin_url

    # 🔥 now guaranteed /pin/ page
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "lxml")

    # 🖼 images
    images = list({
        img["src"]
        for img in soup.find_all("img")
        if img.get("src") and ("originals" in img["src"] or "736x" in img["src"])
    })

    # 🎥 video
    video = None
    for script in soup.find_all("script"):
        if script.string and "video_list" in script.string:
            try:
                data = json.loads(
                    re.search(r"\{.*\}", script.string, re.S).group()
                )
                pins = data["props"]["initialReduxState"]["pins"]
                pin_id = next(iter(pins))
                videos = pins[pin_id]["videos"]["video_list"]

                video = max(videos.values(), key=lambda x: x["width"])["url"]
                break
            except:
                pass

    return images, video, None
