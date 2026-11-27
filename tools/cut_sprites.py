"""Asset sheetdan Yong'oqvoy pozalarini shaffof PNG qilib qirqadi."""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

SHEET = "brand/yongoqvoy_asset_sheet.png"
# (nom, x0, y0, x1, y1) — 1536x1024 varaqdagi koordinatalar
BOXES = [
    ("like", 20, 470, 255, 700), ("ok_kozqisish", 275, 470, 510, 700),
    ("hayron", 520, 470, 750, 700), ("oylash", 760, 470, 990, 700),
    ("galaba", 990, 470, 1250, 700), ("goya", 1265, 460, 1530, 700),
    ("kitob", 25, 715, 265, 965), ("noutbuk", 300, 715, 575, 965),
    ("korsatish", 570, 715, 830, 965), ("lavha", 830, 715, 1085, 965),
]

def cut(img, box):
    crop = img.crop(box[1:]).convert("RGB")
    a = np.asarray(crop).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bright = a.max(axis=2)
    cand = ((b >= r) & (bright < 125)) | (bright < 40)   # to'q ko'k fon va soya
    lab0, _ = ndimage.label(cand)
    border = set(np.unique(np.concatenate([lab0[0], lab0[-1], lab0[:, 0], lab0[:, -1]]))) - {0}
    bg = np.isin(lab0, list(border))   # faqat chetga tegib turgan fon
    fg = ~bg
    fg = ndimage.binary_opening(fg, iterations=1)
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 400])
    else:
        keep = fg
    keep = ndimage.binary_fill_holes(keep)
    alpha = Image.fromarray((keep * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.8))
    out = crop.convert("RGBA"); out.putalpha(alpha)
    return out.crop(out.getbbox())

if __name__ == "__main__":
    img = Image.open(SHEET)
    for b in BOXES:
        cut(img, b).save(f"brand/sprites/{b[0]}.png")
        print(b[0])
