import aiohttp
import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup

app = FastAPI(title="Pinterest Image & Video Downloader")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# 🔹 resolve pin.it → pinterest.com
async def resolve_pin_url(url: str) -> str:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True, timeout=20) as resp:
            return str(resp.url)

async def fetch_pin_data(url: str):
    if "pin.it" in url:
        url = await resolve_pin_url(url)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, timeout=20) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "lxml")

    # 🔥 Images
    images = list({
        img["src"]
        for img in soup.find_all("img")
        if img.get("src") and ("originals" in img["src"] or "736x" in img["src"])
    })

    # 🔥 Video
    video = None
    scripts = soup.find_all("script")

    for script in scripts:
        if script.string and "video_list" in script.string:
            try:
                json_text = re.search(r'\{.*\}', script.string, re.S).group()
                data = json.loads(json_text)

                pin_data = (
                    data["props"]["initialReduxState"]["pins"]
                )
                pin_id = next(iter(pin_data))
                videos = pin_data[pin_id]["videos"]["video_list"]

                # Best quality video
                video = max(
                    videos.values(),
                    key=lambda x: x.get("width", 0)
                )["url"]
                break
            except Exception:
                pass

    return images, video


# 🔻 Request model
class PinRequest(BaseModel):
    url: str


# 🔻 API endpoint
@app.post("/download")
async def download_pin(data: PinRequest):
    try:
        images, video = await fetch_pin_data(data.url)

        return {
            "success": True,
            "images": images,
            "video": video
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
