import aiohttp
import asyncio
import json
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ================= REDIRECT RESOLVER =================
async def resolve_redirect(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as r:
            return str(r.url)


# ================= MAIN FETCH =================
async def fetch_pin(url):

    try:
        # Resolve short link
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

        # =====================================================
        # 1️⃣ TRY META VIDEO (Most Reliable Method)
        # =====================================================
        meta_video = soup.find("meta", property="og:video")
        if meta_video and meta_video.get("content"):
            video = meta_video["content"]

        # =====================================================
        # 2️⃣ IMAGE EXTRACTION (Original Quality)
        # =====================================================
        for img in soup.find_all("img", src=True):
            src = img["src"]

            if "pinimg.com" in src:
                src = re.sub(r"/\d+x/", "/originals/", src)
                images.add(src)

        # =====================================================
        # 3️⃣ ADVANCED JSON VIDEO SEARCH
        # =====================================================
        if not video:

            scripts = soup.find_all("script")

            for script in scripts:
                if not script.string:
                    continue

                if "video_list" in script.string:

                    matches = re.findall(r'({.*?"video_list".*?})', script.string)

                    for match in matches:
                        try:
                            data = json.loads(match)

                            if "video_list" in data:
                                best = max(
                                    data["video_list"].values(),
                                    key=lambda x: x.get("width", 0)
                                )
                                video = best.get("url")
                                break

                        except:
                            continue

                if video:
                    break

        return list(images), video, None

    except Exception as e:
        return [], None, str(e)


# ================= TEST =================
async def main():
    url = "https://pin.it/XXXXXXX"  # replace with real link
    images, video, error = await fetch_pin(url)

    print("\nIMAGES FOUND:", len(images))
    for i in images[:3]:
        print(i)

    print("\nVIDEO URL:", video)
    print("\nERROR:", error)


if __name__ == "__main__":
    asyncio.run(main())
