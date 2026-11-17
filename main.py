from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import subprocess
import json

app = FastAPI(title="SnapSave API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LinkRequest(BaseModel):
    url: str

def detect_platform(url: str):
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    elif "instagram.com" in url_lower:
        return "Instagram"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "Facebook"
    elif "pinterest.com" in url_lower or "pin.it" in url_lower:
        return "Pinterest"
    return "Other"

@app.get("/")
def home():
    return {"status": "SnapSave Engine is Running!"}

@app.post("/api/video")
def get_video(req: LinkRequest):
    url = req.url.strip()
    platform = detect_platform(url)
    ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats_list = []
            seen_resolutions = set()
            for f in info.get('formats', []):
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                ext = f.get('ext')
                download_url = f.get('url')
                if vcodec != 'none' and acodec != 'none' and ext == 'mp4' and download_url:
                    height = f.get('height')
                    res_label = f"{height}p (HD)" if height and height >= 720 else (f"{height}p" if height else "Standard")
                    if res_label not in seen_resolutions:
                        seen_resolutions.add(res_label)
                        formats_list.append({"quality": res_label, "ext": "MP4", "url": download_url})
            if not formats_list and info.get('url'):
                formats_list.append({"quality": "Best Quality", "ext": info.get('ext', 'MP4').upper(), "url": info.get('url')})
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url'):
                    formats_list.append({"quality": "Audio Only", "ext": f.get('ext', 'M4A').upper(), "url": f.get('url')})
                    break
            return {"success": True, "platform": platform, "title": info.get('title', 'SnapSave Video'), "thumbnail": info.get('thumbnail', ''), "formats": formats_list}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Video error: {str(e)}")

@app.post("/api/thumbnail")
def get_thumbnail(req: LinkRequest):
    url = req.url.strip()
    platform = detect_platform(url)
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumbnails = info.get('thumbnails', [])
            best_thumb = info.get('thumbnail', '')
            max_width = 0
            for t in thumbnails:
                w = t.get('width') or 0
                if w > max_width and t.get('url'):
                    max_width = w
                    best_thumb = t.get('url')
            if not best_thumb:
                raise Exception("Thumbnail nahi mila")
            return {"success": True, "platform": platform, "title": info.get('title', 'SnapSave Thumbnail'), "thumbnail_url": best_thumb}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Thumbnail error: {str(e)}")

@app.post("/api/post")
def get_post(req: LinkRequest):
    url = req.url.strip()
    platform = detect_platform(url)
    try:
        result = subprocess.run(["gallery-dl", "--get-urls", url], capture_output=True, text=True, timeout=25)
        urls = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("http")]
        if not urls:
            raise Exception("Is link par koi post nahi mili.")
        return {"success": True, "platform": platform, "count": len(urls), "images": urls}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Post error: {str(e)}")
