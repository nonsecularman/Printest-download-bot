import aiohttp
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

async def resolve_pin_url(url):
    """Resolve pin.it and other short URLs to real pin URL"""
    async with aiohttp.ClientSession(
        headers=HEADERS, 
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        async with session.get(url, allow_redirects=True, follow_redirects=True) as r:
            return str(r.url), await r.text()

def extract_first_pin(html: str):
    """Extract first real /pin/ link from discover/search pages"""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/pin/") and "pin" in href:
            return "https://www.pinterest.com" + href
    return None

def upgrade_image_url(url: str) -> str:
    """Upgrade image URLs to highest quality (remove size params, add 736x/1080x)"""
    if not url or not url.startswith('http'):
        return url
    
    parsed = urlparse(url)
    path = parsed.path
    
    # Replace size params with highest quality
    path = re.sub(r'/\d+x\d+(v\d+)?/', '/736x/', path)
    path = re.sub(r'236x|474x|736x|564x|150x|120x', 'originals', path)
    
    # Pinterest high quality patterns
    if 'static' in path:
        path = path.replace('236x', '736x').replace('474x', '1080x')
    
    return urljoin(url, path)

async def fetch_pin(url):
    """Fetch high quality images and videos from Pinterest pin"""
    html = None
    final_url = url

    # 🔥 Handle pin.it redirects
    if "pin.it" in url or any(short in url for short in ["/t/", "/p/"]):
        try:
            final_url, html = await resolve_pin_url(url)
        except:
            pass

    # ❌ Not a direct pin → try extracting one
    if "/pin/" not in final_url:
        if not html:
            async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(final_url) as r:
                    html = await r.text()

        pin_url = extract_first_pin(html)
        if not pin_url:
            return [], None, "NO_PIN_FOUND"
        final_url = pin_url

    # 🔥 Fetch the pin page with better headers
    try:
        async with aiohttp.ClientSession(
            headers=HEADERS, 
            timeout=aiohttp.ClientTimeout(total=30),
            cookies={'_pin_session': 'placeholder'}  # Pinterest often needs cookies
        ) as session:
            async with session.get(final_url, allow_redirects=True) as r:
                if r.status != 200:
                    return [], None, f"HTTP_{r.status}"
                html = await r.text()
    except Exception as e:
        return [], None, f"FETCH_ERROR: {str(e)}"

    soup = BeautifulSoup(html, "html.parser")

    # 🖼️ HIGH QUALITY IMAGES - Multiple extraction methods
    images = set()
    
    # Method 1: Originals and high-res from img tags
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if any(high in src for high in ["originals", "736x", "1080x", "564x"]):
            images.add(upgrade_image_url(src))

    # Method 2: Data attributes with high quality images
    for div in soup.find_all(attrs={"data-test-id": "pin-wrapper"}):
        img_data = div.get("data-pin-chunk") or div.get("data-test-pin-wrapper")
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
