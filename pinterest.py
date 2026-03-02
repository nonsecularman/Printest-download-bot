import aiohttp
import asyncio
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.pinterest.com/",
}


async def resolve_redirect(url):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True) as r:
            return str(r.url)


async def fetch_pin(url):

    try:
        if "pin.it" in url:
            url = await resolve_redirect(url)

        # Extract PIN ID
        match = re.search(r"/pin/(\d+)", url)
        if not match:
            return [], None, "INVALID_PIN"

        pin_id = match.group(1)

        api_url = (
            "https://www.pinterest.com/resource/PinResource/get/"
            "?source_url=/pin/{}/"
            "&data={{\"options\":{{\"id\":\"{}\"}},\"context\":{{}}}}"
        ).format(pin_id, pin_id)

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(api_url) as r:

                if r.status != 200:
                    return [], None, f"HTTP_{r.status}"

                data = await r.json()

        pin_data = data.get("resource_response", {}).get("data", {})

        images = []
        video = None

        # IMAGE
        if "images" in pin_data:
            original = pin_data["images"].get("orig")
            if original:
                images.append(original.get("url"))

        # VIDEO
        if "videos" in pin_data:
            video_list = pin_data["videos"].get("video_list", {})

            if video_list:
                best = max(
                    video_list.values(),
                    key=lambda x: x.get("width", 0)
                )
                video = best.get("url")

        return images, video, None

    except Exception as e:
        return [], None, str(e)


# Test
async def main():
    url = "https://www.pinterest.com/pin/XXXXXXXX/"
    images, video, error = await fetch_pin(url)

    print("Images:", images)
    print("Video:", video)
    print("Error:", error)


if __name__ == "__main__":
    asyncio.run(main())
