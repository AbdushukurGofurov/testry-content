"""Post rasmlarini brend shablonida chizadi (HTML -> PNG, Chrome orqali).

Foydalanish:  python tools/render.py spec.json chiqish_papkasi/
spec.json:
{
  "size": "ig" | "tg",            # ig = 1080x1350 (karusel), tg = 1080x1080
  "slides": [
    {"title": "Kasbni *tasodifan* tanlamang", "body": "...", "pose": "hayron",
     "kicker": "Testry", "cta": "Havola bio'da"}
  ]
}
*so'z* — moviy urg'u, _so'z_ — to'q sariq urg'u.
"""
import html
import json
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIZES = {"ig": (1080, 1350), "tg": (1080, 1080)}


def rich(text):
    t = html.escape(text or "")
    t = re.sub(r"\*(.+?)\*", r'<span class="c">\1</span>', t)
    t = re.sub(r"_(.+?)_", r'<span class="o">\1</span>', t)
    return t.replace("\n", "<br>")


CSS = """
@font-face{font-family:M;src:url('%(f)s/Montserrat_800ExtraBold.ttf');font-weight:800}
@font-face{font-family:M;src:url('%(f)s/Montserrat_700Bold.ttf');font-weight:700}
@font-face{font-family:M;src:url('%(f)s/Montserrat_500Medium.ttf');font-weight:500}
*{margin:0;padding:0;box-sizing:border-box}
body{width:%(w)dpx;height:%(h)dpx;font-family:M;color:#fff;overflow:hidden;
 background:radial-gradient(120%% 90%% at 80%% 10%%,#154D7C 0%%,#062652 45%%,#011434 100%%)}
.frame{position:absolute;inset:44px;border-radius:64px;border:3px solid rgba(56,209,233,.85);
 box-shadow:0 0 28px rgba(56,209,233,.55),inset 0 0 40px rgba(122,41,177,.25)}
.wrap{position:absolute;inset:44px;padding:84px 80px;display:flex;flex-direction:column}
.kicker{font-weight:700;font-size:30px;letter-spacing:4px;text-transform:uppercase;color:#38D1E9;margin-bottom:34px}
.title{font-weight:800;font-size:%(tsize)dpx;line-height:1.08;max-width:%(tw)dpx}
.body{font-weight:500;font-size:40px;line-height:1.35;margin-top:38px;color:#DCEBFA;max-width:%(bw)dpx}
.c{color:#38D1E9}.o{color:#ED7227}
.pose{position:absolute;right:70px;bottom:62px;height:%(ph)dpx;filter:drop-shadow(0 18px 30px rgba(0,0,0,.45))}
.foot{position:absolute;left:124px;bottom:104px;font-weight:800;font-size:38px;color:#38D1E9}
.foot small{font-weight:700;font-size:22px;color:#9FB8D6;letter-spacing:3px;display:block;margin-top:6px}
.cta{display:inline-block;margin-top:44px;padding:22px 38px;border-radius:999px;font-weight:800;font-size:34px;
 background:linear-gradient(90deg,#ED7227,#7A29B1);align-self:flex-start}
.page{position:absolute;right:124px;top:118px;font-weight:700;font-size:26px;color:#9FB8D6}
"""


def slide_html(s, w, h, idx, total):
    long_title = len(s.get("title", "")) > 38
    css = CSS % {"f": (ROOT / "brand" / "fonts").as_uri(), "w": w, "h": h,
                 "tsize": 72 if long_title else 88, "tw": w - 330 if s.get("pose") else w - 250,
                 "bw": w - 420 if s.get("pose") else w - 250, "ph": int(h * 0.40)}
    pose = s.get("pose")
    pose_img = f'<img class="pose" src="{(ROOT / "brand" / "sprites" / (pose + ".png")).as_uri()}">' if pose else ""
    page = f'<div class="page">{idx}/{total}</div>' if total > 1 else ""
    cta = f'<div class="cta">{rich(s["cta"])}</div>' if s.get("cta") else ""
    body = f'<div class="body">{rich(s["body"])}</div>' if s.get("body") else ""
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="frame"></div>{page}
<div class="wrap"><div class="kicker">{rich(s.get('kicker', 'Testry'))}</div>
<div class="title">{rich(s.get('title', ''))}</div>{body}{cta}</div>
{pose_img}<div class="foot">Testry.uz<small>TEST. TRY. SUCCEED.</small></div></body></html>"""


def render(spec, out_dir):
    w, h = SIZES[spec.get("size", "ig")]
    out = pathlib.Path(out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome" if pathlib.Path("/usr/bin/google-chrome").exists() else None)
        pg = b.new_page(viewport={"width": w, "height": h})
        slides = spec["slides"]
        for i, s in enumerate(slides, 1):
            tmp = out / f"_s{i}.html"
            tmp.write_text(slide_html(s, w, h, i, len(slides)), encoding="utf-8")
            pg.goto(tmp.as_uri()); pg.wait_for_timeout(150)
            f = out / f"{i}.png"; pg.screenshot(path=str(f)); tmp.unlink(); files.append(f.name)
        b.close()
    return files


if __name__ == "__main__":
    print(render(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2]))
