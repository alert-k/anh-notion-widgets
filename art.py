"""Generate Elaina-themed covers (private frame crops) + original icons, upload to Notion, apply to pages.
Frame crops come from your local video and are only uploaded into your private Notion (never committed)."""
import os, math, random, mimetypes, json, urllib.request, uuid
from PIL import Image, ImageDraw, ImageFilter
from lib import api, ids, ROOT, _token, VER

A = os.path.join(ROOT, "art_private"); os.makedirs(A, exist_ok=True)
CREAM, BLUSH, MAUVE, MIST, SKY, VIO, INK = "#f8f4ea", "#e9c8bd", "#856165", "#caddd7", "#8fd3d8", "#8a7cc4", "#2b2328"
S = 4  # supersample


def canvas(n=256):
    return Image.new("RGBA", (n * S, n * S), (0, 0, 0, 0))


def finish(im, n=256):
    return im.resize((n, n), Image.LANCZOS)


def disc(bg):
    im = canvas(); d = ImageDraw.Draw(im); m = 8 * S
    d.ellipse([m, m, 256 * S - m, 256 * S - m], fill=bg, outline=INK, width=3 * S)
    return im, d


def P(*pts): return [(x * S, y * S) for x, y in pts]


def star(d, cx, cy, R, r, fill):
    pts = [(cx + (R if i % 2 == 0 else r) * math.sin(i * math.pi / 5), cy - (R if i % 2 == 0 else r) * math.cos(i * math.pi / 5)) for i in range(10)]
    d.polygon(P(*pts), fill=fill, outline=INK)


def icon_hat():
    im, d = disc(MIST)
    d.polygon(P((128, 40), (88, 150), (168, 150)), fill=INK)
    d.polygon(P((128, 40), (150, 62), (140, 72)), fill=INK)
    d.ellipse(P((52, 138), (204, 172)), fill=INK)
    d.rectangle(P((90, 126), (166, 144)), fill=VIO)
    star(d, 128, 100, 12, 5, BLUSH)
    return finish(im)


def icon_star():
    im, d = disc(BLUSH); star(d, 128, 132, 78, 34, CREAM); return finish(im)


def icon_moon():
    im, d = disc(VIO)
    d.ellipse(P((70, 62), (190, 182)), fill=CREAM)
    d.ellipse(P((98, 50), (212, 164)), fill=VIO)
    star(d, 170, 178, 16, 7, CREAM); star(d, 82, 190, 9, 4, CREAM)
    return finish(im)


def icon_book():
    im, d = disc(CREAM)
    d.rounded_rectangle(P((66, 66), (190, 190)), 10 * S, fill=MAUVE, outline=INK, width=3 * S)
    d.rectangle(P((82, 66), (92, 190)), fill=INK)
    d.rounded_rectangle(P((108, 90), (176, 112)), 4 * S, fill=CREAM)
    star(d, 142, 150, 16, 7, BLUSH)
    return finish(im)


def icon_broom():
    im, d = disc(SKY)
    r = 2 ** .5
    E = (112, 144)
    def pt(t, w): return (E[0] - t / r + w / r, E[1] + t / r + w / r)
    d.line(P((196, 60), E), fill=MAUVE, width=9 * S)
    d.polygon(P(pt(0, -14), pt(0, 14), pt(62, 38), pt(62, -38)), fill=BLUSH, outline=INK)
    for w in (-20, -7, 7, 20): d.line(P(pt(10, w * .4), pt(60, w * 1.6)), fill=MAUVE, width=2 * S)
    d.rectangle(P((0, 0), (0, 0)))
    return finish(im)


def icon_cat():
    im, d = disc(CREAM)
    d.polygon(P((70, 120), (78, 62), (116, 96)), fill=INK); d.polygon(P((186, 120), (178, 62), (140, 96)), fill=INK)
    d.ellipse(P((62, 84), (194, 196)), fill=INK)
    d.ellipse(P((92, 126), (112, 150)), fill=CREAM); d.ellipse(P((144, 126), (164, 150)), fill=CREAM)
    d.ellipse(P((98, 134), (108, 146)), fill=SKY); d.ellipse(P((150, 134), (160, 146)), fill=SKY)
    d.polygon(P((122, 156), (134, 156), (128, 164)), fill=BLUSH)
    return finish(im)


def icon_key():
    im, d = disc(BLUSH)
    d.ellipse(P((60, 78), (126, 144)), outline=INK, width=10 * S, fill=CREAM)
    d.rectangle(P((120, 106), (200, 118)), fill=INK); d.rectangle(P((172, 118), (184, 140)), fill=INK); d.rectangle(P((192, 118), (204, 134)), fill=INK)
    return finish(im)


ICONS = {"home": icon_hat, "act": icon_star, "log": icon_moon, "sec": icon_hat, "study": icon_book, "job": icon_broom, "pkm": icon_cat, "guide": icon_key, "sites": icon_star}


def banner(seed, a, b, w=1920, h=384):
    random.seed(seed)
    im = Image.new("RGB", (w, h)); px = im.load()
    A_, B_ = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    for x in range(w):
        t = x / w
        for y in range(h):
            u = (t * .7 + y / h * .3)
            px[x, y] = tuple(int(A_[k] * (1 - u) + B_[k] * u) for k in range(3))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(60):
        x, y, r = random.randrange(w), random.randrange(h), random.choice([2, 3, 4, 6])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, random.randrange(90, 220)))
    return im.filter(ImageFilter.GaussianBlur(.6))


def covers():
    full = Image.open(os.path.join(A, "full.jpg")).convert("RGB"); W, H = full.size

    def crop(x0, y0, x1, y1): return full.crop((x0, y0, x1, y1)).resize((1920, int(1920 * (y1 - y0) / (x1 - x0))), Image.LANCZOS)
    return {
        "home": crop(0, 250, W, 1018), "act": crop(0, 1350, W, 2118), "log": crop(0, 300, 1900, 684),
        "sec": crop(1400, 800, W, 1288),
        "study": banner(1, MIST, CREAM), "job": banner(2, BLUSH, CREAM), "pkm": banner(3, "#d9d3ee", MIST), "guide": banner(4, CREAM, BLUSH),
        "sites": banner(5, SKY, "#d9d3ee")}


def upload(path, ctype):
    fu = api("POST", "/file_uploads", {"filename": os.path.basename(path), "content_type": ctype})
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() \
        + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(fu["upload_url"], data=body, method="POST", headers={
        "Authorization": "Bearer " + _token(), "Notion-Version": VER, "Content-Type": f"multipart/form-data; boundary={b}"})
    urllib.request.urlopen(req, timeout=120).read()
    return fu["id"]


if __name__ == "__main__":
    I = ids(); os.makedirs(os.path.join(A, "out"), exist_ok=True)
    cv = covers()
    for k, im in cv.items():
        p = os.path.join(A, "out", f"cover_{k}.jpg"); im.save(p, quality=88)
    for k, fn in ICONS.items():
        fn().save(os.path.join(A, "out", f"icon_{k}.png"))
    targets = {"home": "3ee175d9-b3e1-80fa-be67-cb06ab4d1a74", "act": I["hub:act"], "log": I["hub:log"], "sec": I["hub:sec"],
               "study": I["hub:study"], "job": I["hub:job"], "pkm": I["hub:pkm"], "guide": I["hub:guide"], "sites": I["sites"]}
    for k, pid in targets.items():
        body = {}
        c = os.path.join(A, "out", f"cover_{k}.jpg"); i = os.path.join(A, "out", f"icon_{k}.png")
        body["cover"] = {"type": "file_upload", "file_upload": {"id": upload(c, "image/jpeg")}}
        body["icon"] = {"type": "file_upload", "file_upload": {"id": upload(i, "image/png")}}
        api("PATCH", f"/pages/{pid}", body); print("themed", k)
