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

async def fetch_pin(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "html.parser")

    images = set()
    video = None

    # 🟢 Extract images from img tags
    for img in soup.find_all("img", src=True):
        if "pinimg.com" in img["src"]:
            images.add(img["src"].replace("236x", "originals"))

    # 🟢 Extract JSON from __PWS_DATA__
    for script in soup.find_all("script"):
        if script.string and "__PWS_DATA__" in script.string:
            json_text = re.search(r'__PWS_DATA__\s*=\s*({.*});', script.string, re.S)
            if not json_text:
                continue

            data = json.loads(json_text.group(1))

            # Traverse deeply
            def walk(obj):
                nonlocal video
                if isinstance(obj, dict):
                    if "video_list" in obj:
                        best = max(obj["video_list"].values(), key=lambda x: x.get("width", 0))
                        video = best.get("url")
                    for v in obj.values():
                        walk(v)
                elif isinstance(obj, list):
                    for i in obj:
                        walk(i)

            walk(data)

    return list(images), video        img_data = div.get("data-pin-chunk") or div.get("data-test-pin-wrapper")
        if img_data:
            try:
                data = json.loads(img_data)
                if "images" in data:
                    for img_key, img_info in data["images"].items():
                        if isinstance(img_info, dict) and "url" in img_info:
                            images.add(upgrade_image_url(img_info["url"]))
            except:
                pass

    # Method 3: Script JSON data - most reliable
    video = None
    for script in soup.find_all("script"):
        if script.string:
            # Look for pin data in Redux state
            pin_match = re.search(r'"pins":\s*({[^}]+})', script.string, re.S)
            if pin_match:
                try:
                    pins_data = json.loads(pin_match.group(1))
                    pin_id = next(iter(pins_data))
                    pin_data = pins_data[pin_id]
                    
                    # Images from pin data
                    if "images" in pin_data:
                        for img_key, img_info in pin_data["images"].items():
                            if isinstance(img_info, dict) and "url" in img_info:
                                images.add(upgrade_image_url(img_info["url"]))
                    
                    # Videos from pin data
                    if "videos" in pin_data and pin_data["videos"]:
                        video_list = pin_data["videos"].get("video_list", {})
                        if video_list:
                            best_video = max(video_list.values(), key=lambda x: x.get("width", 0))
                            video = best_video.get("url") or best_video.get("video_url")
                    
                except:
                    pass
            
            # Alternative video extraction
            if not video and "video_list" in script.string:
                video_match = re.search(r'"video_list":\s*({[^}]+})', script.string, re.S)
                if video_match:
                    try:
                        videos = json.loads(video_match.group(1))
                        if isinstance(videos, dict):
                            best_video = max(videos.values(), key=lambda x: x.get("width", 0))
                            video = best_video.get("url")
                    except:
                        pass

    # Convert to list and filter valid URLs
    images = [img for img in images if img and img.startswith('http')]
    
    return images, video, None

# 🔹 Usage example
async def main():
    test_urls = [
        "https://pin.it/ABC123",  # pin.it
        "https://www.pinterest.com/pin/1234567890/",  # direct pin
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing: {url}")
        images, video, error = await fetch_pin(url)
        print(f"Images ({len(images)}): {images[:2]}{'...' if len(images)>2 else ''}")
        print(f"Video: {video}")
        print(f"Error: {error}")

if __name__ == "__main__":
    asyncio.run(main())
