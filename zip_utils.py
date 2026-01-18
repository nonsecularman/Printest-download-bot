import zipfile
import aiohttp
import os
from pathlib import Path
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.pinterest.com/",
    "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
}

async def download_image(url: str, tmp_dir: Path) -> tuple[str, bytes] | None:
    """Download single image with proper error handling"""
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    return None
                
                content = await response.read()
                if len(content) < 512:  # Skip tiny files
                    return None
                
                # Determine extension from content-type or URL
                content_type = response.headers.get('content-type', '').lower()
                ext = 'jpg'
                if 'png' in content_type:
                    ext = 'png'
                elif 'webp' in content_type:
                    ext = 'webp'
                
                return f"img_{uuid.uuid4().hex[:8]}.{ext}", content
    except Exception:
        return None

async def make_zip(images: List[str], zip_name: str = "album") -> str | None:
    """
    Create ZIP from multiple image URLs
    Optimized: concurrent downloads + no temp files
    """
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    
    zip_path = tmp_dir / f"{zip_name}.zip"
    
    # Limit concurrency to avoid rate limits
    semaphore = asyncio.Semaphore(5)
    
    async def download_with_semaphore(url: str) -> tuple[str, bytes] | None:
        async with semaphore:
            return await download_image(url, tmp_dir)
    
    # 🔥 CONCURRENT DOWNLOADS
    tasks = [download_with_semaphore(url) for url in images[:50]]  # Max 50 images
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter successful downloads
    valid_images = [(fname, data) for result in results 
                   if isinstance(result, tuple) and result 
                   for fname, data in [result]]
    
    if not valid_images:
        return None
    
    # 📦 CREATE ZIP (NO TEMP FILES!)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for fname, data in valid_images:
                zipf.writestr(fname, data)
        
        # Verify ZIP
        if zip_path.exists() and zip_path.stat().st_size > 1024:
            return str(zip_path)
        else:
            zip_path.unlink(missing_ok=True)
            return None
            
    except Exception:
        if zip_path.exists():
            zip_path.unlink(missing_ok=True)
        return None

# 🧹 CLEANUP UTILITY
def cleanup_tmp():
    """Remove old temp files"""
    tmp_dir = Path("tmp")
    if tmp_dir.exists():
        for file in tmp_dir.glob("*.zip"):
            if time.time() - file.stat().st_time > 3600:  # 1 hour
                file.unlink()

# 🔄 BATCH ZIP (for >50 images)
async def make_zip_batch(images: List[str], zip_name: str = "album") -> List[str]:
    """Split large albums into multiple ZIPs"""
    cleanup_tmp()
    
    batches = [images[i:i+30] for i in range(0, len(images), 30)]
    zip_paths = []
    
    for i, batch in enumerate(batches):
        zip_path = await make_zip(batch, f"{zip_name}_part_{i+1}")
        if zip_path:
            zip_paths.append(zip_path)
    
    return zip_paths

# 📊 STATS HELPER
def get_image_stats(images: List[str]) -> dict:
    """Quick image analysis"""
    return {
        "total": len(images),
        "unique": len(set(images)),
        "max_recommended": min(50, len(images))
    }
