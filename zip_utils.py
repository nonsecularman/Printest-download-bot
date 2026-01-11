import zipfile
import aiohttp
import os

async def make_zip(images, zip_name):
    os.makedirs("tmp", exist_ok=True)
    zip_path = f"tmp/{zip_name}.zip"

    async with aiohttp.ClientSession() as session:
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for i, url in enumerate(images):
                async with session.get(url) as r:
                    data = await r.read()
                    fname = f"img_{i}.jpg"
                    path = f"tmp/{fname}"
                    with open(path, "wb") as f:
                        f.write(data)
                    zipf.write(path, fname)
                    os.remove(path)

    return zip_path
