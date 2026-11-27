"""Instagram'ga post chiqarish (Instagram API with Instagram Login, graph.instagram.com).

Kerakli GitHub Secrets: IG_ACCESS_TOKEN, IG_USER_ID.
Rasmlar Instagram'ga ochiq havola orqali beriladi: ombor public bo'lgani uchun
raw.githubusercontent.com havolalari ishlatiladi. Instagram faqat JPEG qabul qiladi,
shuning uchun PNG fayllar JPEG'ga aylantirilib, ig_jpg/ papkasiga yoziladi va avval push qilinadi.
"""
import json
import os
import pathlib
import subprocess
import time

import requests

API = "https://graph.instagram.com/v25.0"
REPO_RAW = "https://raw.githubusercontent.com/AbdushukurGofurov/testry-content/main"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def _token():
    return os.environ["IG_ACCESS_TOKEN"].strip()


def _uid():
    return os.environ["IG_USER_ID"].strip()


def _call(method, path, **params):
    params["access_token"] = _token()
    r = requests.request(method, f"{API}/{path}", data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=120)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Instagram: {data['error'].get('message')}")
    return data


def _wait(container_id, tries=40):
    for _ in range(tries):
        st = _call("GET", container_id, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram konteyner holati: {st}")
        time.sleep(6)
    raise RuntimeError("Instagram konteyner tayyor bo'lmadi")


def _public_urls(post, folder):
    """Media fayllarni JPEG qilib omborga push qiladi va ochiq havolalarini qaytaradi."""
    from PIL import Image  # noqa: PLC0415
    out = folder / "ig_jpg"
    out.mkdir(exist_ok=True)
    rels = []
    for m in post.get("media", []):
        src = folder / m
        if src.suffix.lower() == ".mp4":
            rels.append(src.relative_to(ROOT).as_posix())
            continue
        dst = out / (src.stem + ".jpg")
        if not dst.exists():
            Image.open(src).convert("RGB").save(dst, "JPEG", quality=92)
        rels.append(dst.relative_to(ROOT).as_posix())
    subprocess.run(["git", "add", str(out)], cwd=ROOT, check=False)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
        subprocess.run(["git", "commit", "-qm", "Instagram uchun JPEG [skip ci]"], cwd=ROOT, check=True)
        subprocess.run(["git", "pull", "--rebase", "-q"], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)
        time.sleep(20)  # raw havolalar yangilanishi uchun
    return [f"{REPO_RAW}/{r}" for r in rels]


def publish(post, folder):
    urls = _public_urls(post, folder)
    caption = post.get("text", "")[:2200]
    kind = post.get("type")
    if kind == "video":
        c = _call("POST", f"{_uid()}/media", media_type="REELS", video_url=urls[0], caption=caption)
        _wait(c["id"])
        cid = c["id"]
    elif kind == "album" and len(urls) > 1:
        children = []
        for u in urls[:10]:
            params = {"is_carousel_item": "true"}
            if u.endswith(".mp4"):
                params.update(media_type="VIDEO", video_url=u)
            else:
                params["image_url"] = u
            ch = _call("POST", f"{_uid()}/media", **params)
            _wait(ch["id"])
            children.append(ch["id"])
        c = _call("POST", f"{_uid()}/media", media_type="CAROUSEL", children=",".join(children),
                  caption=caption)
        _wait(c["id"])
        cid = c["id"]
    else:
        c = _call("POST", f"{_uid()}/media", image_url=urls[0], caption=caption)
        _wait(c["id"])
        cid = c["id"]
    return _call("POST", f"{_uid()}/media_publish", creation_id=cid)


def refresh_token():
    """Uzoq muddatli token 60 kun amal qiladi; uni yangilab, yangisini qaytaradi."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": _token()}, timeout=60)
    return r.json()


if __name__ == "__main__":
    print(json.dumps(_call("GET", "me", fields="user_id,username"), ensure_ascii=False))
