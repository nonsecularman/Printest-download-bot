import zipfile
import aiohttp
import os
import uuid
import time
from pathlib import Path
from typing import List
import asyncio


# ✅ FIXED HEADERS (Brotli Disabled)
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.pinterest.com/",
    "Accept": "*/*",

    # ✅ Prevent Brotli Encoding
    "Accept-Encoding": "gzip, deflate"
}


# ✅ Download single image safely
async def download_image(url: str) -> tuple[str, bytes] | None:
    try:
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            async with session.get(url, allow_redirects=True) as response:

                if response.status != 200:
                    return None

                content = await response.read()

                # Skip blocked/empty files
                if len(content) < 3000:
                    return None

                # Detect extension
                ctype = response.headers.get("content-type", "").lower()

                ext = "jpg"
                if "png" in ctype:
                    ext = "png"
                elif "webp" in ctype:
                    ext = "webp"

                filename = f"img_{uuid.uuid4().hex[:8]}.{ext}"
                return filename, content

    except Exception as e:
        print("Image Download Error:", e)
        return None


# ✅ FINAL ZIP MAKER (Heroku Safe)
async def make_zip(images: List[str], zip_name: str = "album") -> str | None:

    # ✅ Use Heroku safe tmp folder
    tmp_dir = Path("/tmp")
    zip_path = tmp_dir / f"{zip_name}_{uuid.uuid4().hex[:6]}.zip"

    semaphore = asyncio.Semaphore(5)

    async def download_with_limit(url: str):
        async with semaphore:
            return await download_image(url)

    # Download max 30 images
    tasks = [download_with_limit(url) for url in images[:30]]
    results = await asyncio.gather(*tasks)

    # ✅ Filter valid images
    valid_images = [r for r in results if r is not None]

    if not valid_images:
        return None

    # ✅ Create ZIP
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for fname, data in valid_images:
                zipf.writestr(fname, data)

        # Verify ZIP size
        if zip_path.exists() and zip_path.stat().st_size > 5000:
            return str(zip_path)

        zip_path.unlink(missing_ok=True)
        return None

    except Exception as e:
        print("ZIP ERROR:", e)
        zip_path.unlink(missing_ok=True)
        return None


# 🧹 Cleanup old ZIP files
def cleanup_tmp():
    tmp_dir = Path("/tmp")

    for file in tmp_dir.glob("*.zip"):
        if time.time() - file.stat().st_mtime > 3600:
            file.unlink()
