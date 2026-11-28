"""小圖示：全部自己畫（PIL），不用 emoji 或文字符號。

為什麼：emoji 是文字，有的電腦缺字會變成方框、每台電腦長得也不一樣。
用法：
- `draw_icon(name, size, color=None)`：回傳 size×size 的透明底圖。先放大 4 倍畫、再縮小，邊緣才平滑。
  單色的圖示（叉叉、勾、箭頭、音符……）用 color 上色；彩色的（食物、愛心、金幣……）自己有顏色。
- `ICON_CHARS`：文字裡的某個字元要換成哪個圖示。對話、標籤裡原本寫的 ♪ ✓ 🎧 ……會自動換成畫好的圖，
  另外有幾個私用區字元（COIN 等）是沒有對應文字的純圖示。
要新增圖示：在 `ART` 加一個畫圖函式，需要的話在 `ICON_CHARS` 加對應的字元。
"""
import math

from PIL import Image, ImageDraw

# 沒有對應文字的純圖示（私用區字元，只當「圖示的位置」）
COIN, CAPSULE, TROPHY, LOCK, NOICON = "", "", "", "", ""

# 文字裡的字元 → 圖示名稱
ICON_CHARS = {
    COIN: "coin", CAPSULE: "capsule", TROPHY: "trophy", LOCK: "lock", NOICON: "blank",
    "♪": "note", "♫": "notes", "♩": "note", "🎵": "notes", "🎶": "notes", "✦": "sparkle", "✿": "flower", "♥": "heart",
    "✓": "check", "✕": "close", "×": "close", "－": "minus", "›": "chevron", "◀": "prev", "▶": "next", "≡": "menu",
    "⤢": "expand", "⇲": "shrink", "⇄": "swap", "◢": "grip", "✎": "pencil",
    "🎧": "headphones", "📁": "folder", "📂": "folder_open", "⏰": "clock", "🍬": "candy", "⚠": "warn", "💤": "zzz",
    "🔁": "repeat", "📸": "camera", "🎉": "party", "🎲": "dice", "🍱": "bento", "🎂": "birthday",
    "✌": "hand_scissors", "✊": "hand_rock", "✋": "hand_paper",
}
# 單色圖示：畫的時候用「文字的顏色」（跟字一樣深淺、一樣的 hover 色）
MONO = {"note", "notes", "sparkle", "flower", "check", "close", "minus", "chevron", "prev", "next", "menu", "expand",
        "shrink", "swap", "grip", "pencil", "repeat", "question", "zed"}
SKIP = "️‍"          # 變體選擇字元：沒有字，直接略過

INK = (74, 52, 42)               # 沒指定顏色時單色圖示用的深褐色


def _rgba(c, a=255):
    if c is None:
        return INK + (a,)
    if isinstance(c, str):
        h = c.lstrip("#")
        try:
            c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else INK       # 不是 #rrggbb（例如系統色名稱）就用預設色
        except ValueError:
            c = INK
    return tuple(c[:3]) + ((c[3] if len(c) > 3 else a),)


class _Pen:
    """用 0～100 的座標畫圖，自動放大到畫布。"""

    def __init__(self, size, scale=4):
        self.S = size * scale
        self.u = self.S / 100
        self.im = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def pt(self, p):
        return (p[0] * self.u, p[1] * self.u)

    def box(self, b):
        return tuple(v * self.u for v in b)

    def w(self, v):
        return max(1, int(round(v * self.u)))

    def poly(self, pts, fill=None, outline=None, width=0):
        self.d.polygon([self.pt(p) for p in pts], fill=fill, outline=outline, width=self.w(width) if width else 0)

    def ell(self, b, fill=None, outline=None, width=0):
        self.d.ellipse(self.box(b), fill=fill, outline=outline, width=self.w(width) if width else 0)

    def rect(self, b, r=0, fill=None, outline=None, width=0):
        self.d.rounded_rectangle(self.box(b), radius=r * self.u, fill=fill, outline=outline, width=self.w(width) if width else 0)

    def line(self, pts, fill, width, round_caps=True):
        pts = [self.pt(p) for p in pts]
        self.d.line(pts, fill=fill, width=self.w(width), joint="curve")
        if round_caps:
            r = self.w(width) / 2
            for x, y in (pts[0], pts[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def arc(self, b, a0, a1, fill, width):
        self.d.arc(self.box(b), a0, a1, fill=fill, width=self.w(width))

    def out(self, size):
        return self.im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ 介面小圖示（單色）
def _close(p, c):
    p.line([(22, 22), (78, 78)], c, 12); p.line([(78, 22), (22, 78)], c, 12)


def _minus(p, c):
    p.line([(20, 50), (80, 50)], c, 12)


def _check(p, c):
    p.line([(18, 54), (40, 76), (82, 26)], c, 13)


def _prev(p, c):
    p.poly([(74, 14), (74, 86), (24, 50)], fill=c)


def _next(p, c):
    p.poly([(26, 14), (26, 86), (76, 50)], fill=c)


def _menu(p, c):
    for y in (26, 50, 74):
        p.line([(18, y), (82, y)], c, 10)


def _expand(p, c):
    p.line([(28, 72), (72, 28)], c, 8)
    p.poly([(46, 20), (80, 20), (80, 54)], fill=c); p.poly([(54, 80), (20, 80), (20, 46)], fill=c)


def _shrink(p, c):
    p.line([(24, 24), (64, 64)], c, 8)
    p.poly([(80, 80), (80, 44), (44, 80)], fill=c)


def _swap(p, c):
    p.line([(14, 34), (72, 34)], c, 8); p.poly([(70, 20), (92, 34), (70, 48)], fill=c)
    p.line([(86, 66), (28, 66)], c, 8); p.poly([(30, 52), (8, 66), (30, 80)], fill=c)


def _grip(p, c):
    p.poly([(90, 90), (90, 34), (34, 90)], fill=c)


def _chevron(p, c):
    p.line([(36, 18), (66, 50), (36, 82)], c, 12)


def _pencil(p, c):
    p.line([(36, 64), (74, 26)], c, 18, round_caps=False)
    p.poly([(20, 82), (26, 60), (40, 74)], fill=c)
    p.line([(70, 22), (78, 30)], (255, 255, 255, 0), 1, round_caps=False)


def _note(p, c):
    p.ell((18, 62, 50, 88), fill=c)
    p.rect((44, 16, 52, 76), fill=c)
    p.poly([(52, 16), (80, 32), (76, 54), (52, 40)], fill=c)


def _notes(p, c):
    p.ell((10, 64, 40, 88), fill=c); p.ell((54, 56, 84, 80), fill=c)
    p.rect((34, 22, 42, 76), fill=c); p.rect((78, 14, 86, 68), fill=c)
    p.poly([(34, 22), (86, 12), (86, 30), (34, 40)], fill=c)


def _sparkle(p, c):
    pts = []
    for i in range(8):
        r = 46 if i % 2 == 0 else 12
        a = math.pi / 4 * i - math.pi / 2
        pts.append((50 + r * math.cos(a), 50 + r * math.sin(a)))
    p.poly(pts, fill=c)


def _flower(p, c):
    for i in range(6):
        a = math.pi / 3 * i
        x, y = 50 + 26 * math.cos(a), 50 + 26 * math.sin(a)
        p.ell((x - 17, y - 17, x + 17, y + 17), fill=c)
    p.ell((38, 38, 62, 62), fill=(255, 255, 255, 150))


def _repeat(p, c):
    p.arc((14, 22, 86, 78), 200, 340, c, 8)
    p.poly([(70, 12), (94, 30), (66, 40)], fill=c)
    p.arc((14, 22, 86, 78), 20, 160, c, 8)
    p.poly([(30, 88), (6, 70), (34, 60)], fill=c)


# ------------------------------------------------------------------ 彩色圖示
def _heart(p, c):
    col = _rgba(c) if c else (255, 105, 135, 255)
    p.ell((8, 14, 54, 60), fill=col); p.ell((46, 14, 92, 60), fill=col)
    p.poly([(11, 46), (89, 46), (50, 90)], fill=col)
    p.ell((18, 24, 32, 36), fill=(255, 255, 255, 130))


def _coin(p, c):
    p.ell((6, 6, 94, 94), fill=(255, 205, 60, 255), outline=(207, 140, 18, 255), width=6)
    p.ell((22, 22, 78, 78), outline=(235, 168, 28, 255), width=5)
    p.arc((14, 14, 86, 86), 200, 260, (255, 240, 170, 255), 6)
    p.poly([(50, 34), (55, 46), (67, 50), (55, 54), (50, 66), (45, 54), (33, 50), (45, 46)], fill=(255, 244, 200, 255))


def _capsule(p, c):
    box = (8, 8, 92, 92)
    p.d.pieslice(p.box(box), 180, 360, fill=(240, 120, 58, 255))
    p.d.pieslice(p.box(box), 0, 180, fill=(255, 246, 232, 255))
    p.ell(box, outline=(150, 82, 46, 255), width=5)
    p.line([(8, 50), (92, 50)], (150, 82, 46, 255), 5, round_caps=False)
    p.ell((24, 20, 40, 34), fill=(255, 255, 255, 190))


def _trophy(p, c):
    gold, edge = (255, 200, 50, 255), (196, 132, 16, 255)
    p.arc((4, 14, 36, 52), 90, 270, edge, 7); p.arc((64, 14, 96, 52), 270, 90, edge, 7)
    p.poly([(24, 10), (76, 10), (72, 44), (60, 62), (40, 62), (28, 44)], fill=gold, outline=edge, width=2)
    p.rect((44, 62, 56, 76), fill=gold, outline=edge, width=2)
    p.rect((28, 76, 72, 90), r=4, fill=gold, outline=edge, width=3)
    _star(p, 50, 34, 14, (255, 244, 200, 255))


def _star(p, cx, cy, r, col):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * .45
        a = math.pi / 5 * i - math.pi / 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    p.poly(pts, fill=col)


def _lock(p, c):
    p.arc((26, 8, 74, 60), 180, 360, (150, 132, 120, 255), 9)
    p.rect((18, 42, 82, 92), r=10, fill=(190, 172, 160, 255), outline=(140, 122, 110, 255), width=4)
    p.ell((44, 56, 56, 68), fill=(120, 104, 94, 255)); p.rect((48, 64, 52, 78), fill=(120, 104, 94, 255))


def _blank(p, c):
    pass


def _headphones(p, c):
    col = _rgba(c) if c else (112, 92, 176, 255)
    p.arc((16, 12, 84, 80), 180, 360, col, 9)
    p.rect((10, 48, 32, 82), r=8, fill=col); p.rect((68, 48, 90, 82), r=8, fill=col)
    p.rect((16, 54, 26, 76), r=4, fill=(255, 255, 255, 120)); p.rect((74, 54, 84, 76), r=4, fill=(255, 255, 255, 120))


def _folder(p, c):
    p.poly([(8, 26), (38, 26), (46, 36), (92, 36), (92, 84), (8, 84)], fill=(246, 188, 70, 255), outline=(196, 132, 30, 255), width=3)
    p.rect((8, 44, 92, 84), r=6, fill=(255, 208, 100, 255), outline=(196, 132, 30, 255), width=3)


def _folder_open(p, c):
    p.poly([(8, 22), (36, 22), (44, 32), (84, 32), (84, 80), (8, 80)], fill=(238, 172, 60, 255), outline=(196, 132, 30, 255), width=3)
    p.poly([(20, 46), (96, 46), (82, 86), (6, 86)], fill=(255, 208, 100, 255), outline=(196, 132, 30, 255), width=3)


def _clock(p, c):
    red, dark = (232, 90, 70, 255), (120, 60, 40, 255)
    p.ell((8, 6, 40, 38), fill=red, outline=dark, width=3); p.ell((60, 6, 92, 38), fill=red, outline=dark, width=3)
    p.ell((14, 16, 86, 88), fill=(255, 252, 244, 255), outline=red, width=7)
    p.line([(50, 52), (50, 32)], dark, 6); p.line([(50, 52), (66, 58)], dark, 6)
    p.line([(26, 90), (16, 98)], dark, 6); p.line([(74, 90), (84, 98)], dark, 6)


def _candy(p, c):
    p.poly([(4, 30), (30, 50), (4, 70)], fill=(255, 140, 170, 255)); p.poly([(96, 30), (70, 50), (96, 70)], fill=(255, 140, 170, 255))
    p.ell((22, 26, 78, 74), fill=(255, 112, 150, 255), outline=(200, 70, 110, 255), width=3)
    p.arc((28, 32, 72, 68), 200, 290, (255, 255, 255, 230), 6); p.arc((30, 34, 70, 66), 20, 110, (255, 214, 224, 255), 6)


def _warn(p, c):
    p.poly([(50, 8), (95, 88), (5, 88)], fill=(255, 196, 40, 255), outline=(176, 112, 10, 255), width=5)
    p.rect((45, 34, 55, 64), r=3, fill=(104, 64, 20, 255)); p.ell((44, 69, 56, 81), fill=(104, 64, 20, 255))


def _zzz(p, c):
    col = (120, 140, 205, 255)
    for x, y, s in ((10, 46, 36), (44, 22, 28), (70, 4, 22)):
        p.line([(x, y), (x + s, y), (x, y + s), (x + s, y + s)], col, 7 if s > 24 else 6, round_caps=True)


def _camera(p, c):
    p.rect((8, 28, 92, 82), r=10, fill=(120, 126, 140, 255), outline=(72, 76, 90, 255), width=3)
    p.rect((30, 18, 58, 32), r=4, fill=(120, 126, 140, 255), outline=(72, 76, 90, 255), width=3)
    p.ell((30, 36, 70, 76), fill=(240, 244, 250, 255), outline=(72, 76, 90, 255), width=4); p.ell((40, 46, 60, 66), fill=(86, 130, 190, 255))
    p.ell((76, 36, 86, 46), fill=(255, 220, 110, 255))


def _party(p, c):
    p.poly([(10, 90), (34, 30), (70, 66)], fill=(255, 176, 60, 255), outline=(200, 120, 20, 255), width=3)
    p.line([(26, 66), (44, 82)], (232, 90, 70, 255), 5, round_caps=False); p.line([(20, 80), (30, 88)], (232, 90, 70, 255), 5, round_caps=False)
    for (x, y), col in (((58, 22), (255, 100, 130, 255)), ((82, 40), (90, 170, 240, 255)), ((70, 12), (120, 200, 120, 255)), ((90, 66), (255, 210, 60, 255))):
        p.ell((x - 5, y - 5, x + 5, y + 5), fill=col)
    p.line([(46, 22), (54, 8)], (170, 110, 220, 255), 5); p.line([(80, 24), (92, 20)], (255, 120, 150, 255), 5)


def _dice(p, c):
    p.rect((10, 10, 90, 90), r=16, fill=(255, 252, 246, 255), outline=(150, 120, 100, 255), width=5)
    for x, y in ((30, 30), (70, 30), (50, 50), (30, 70), (70, 70)):
        p.ell((x - 8, y - 8, x + 8, y + 8), fill=(214, 70, 70, 255) if (x, y) == (50, 50) else (74, 52, 42, 255))


def _bento(p, c):
    p.rect((6, 22, 94, 84), r=10, fill=(150, 90, 56, 255), outline=(100, 56, 32, 255), width=3)
    p.rect((12, 28, 50, 78), r=6, fill=(255, 252, 244, 255)); p.ell((22, 38, 40, 56), fill=(214, 70, 70, 255))
    p.rect((54, 28, 88, 50), r=5, fill=(255, 196, 80, 255)); p.rect((54, 54, 88, 78), r=5, fill=(120, 190, 100, 255))


def _birthday(p, c):
    p.rect((8, 78, 92, 90), r=4, fill=(220, 200, 180, 255))
    p.rect((16, 52, 84, 80), r=6, fill=(255, 190, 200, 255), outline=(220, 130, 150, 255), width=3)
    p.rect((24, 34, 76, 54), r=6, fill=(255, 246, 232, 255), outline=(220, 130, 150, 255), width=3)
    p.rect((47, 14, 53, 34), fill=(120, 190, 240, 255)); p.poly([(50, 3), (57, 14), (43, 14)], fill=(255, 180, 50, 255))
    for x in (28, 44, 60, 74):
        p.ell((x - 5, 50, x + 5, 64), fill=(255, 246, 232, 255))


def _hand(p, kind):
    skin, edge = (255, 218, 170, 255), (196, 140, 90, 255)
    if kind == "paper":
        p.rect((26, 44, 74, 92), r=14, fill=skin, outline=edge, width=3)
        for i, x in enumerate((26, 40, 54, 66)):
            p.rect((x, 8 + (0 if i in (1, 2) else 8), x + 12, 56), r=6, fill=skin, outline=edge, width=3)
        p.rect((8, 48, 32, 62), r=7, fill=skin, outline=edge, width=3)
    elif kind == "rock":
        p.rect((18, 34, 82, 90), r=18, fill=skin, outline=edge, width=3)
        for x in (22, 38, 54, 68):
            p.rect((x, 26, x + 13, 52), r=6, fill=skin, outline=edge, width=3)
        p.rect((8, 54, 40, 70), r=8, fill=skin, outline=edge, width=3)
    else:  # scissors
        p.rect((26, 52, 82, 92), r=16, fill=skin, outline=edge, width=3)
        p.poly([(34, 56), (22, 8), (36, 6), (48, 52)], fill=skin, outline=edge, width=3)
        p.poly([(52, 52), (64, 6), (78, 10), (66, 56)], fill=skin, outline=edge, width=3)
        p.rect((8, 56, 36, 70), r=7, fill=skin, outline=edge, width=3)


# ------------------------------------------------------------------ 丟給她們的東西（食物、玩具）
def _onigiri(p, c):
    p.poly([(50, 8), (90, 80), (10, 80)], fill=(255, 252, 244, 255), outline=(180, 170, 150, 255), width=3)
    p.rect((26, 62, 74, 92), r=4, fill=(40, 52, 44, 255))
    p.ell((40, 40, 46, 46), fill=(215, 210, 196, 255)); p.ell((54, 52, 60, 58), fill=(215, 210, 196, 255))


def _rice(p, c):
    p.d.pieslice(p.box((12, 14, 88, 66)), 180, 360, fill=(255, 252, 244, 255), outline=(190, 180, 160, 255), width=p.w(3))
    p.d.pieslice(p.box((6, 38, 94, 96)), 0, 180, fill=(210, 120, 80, 255), outline=(150, 76, 50, 255), width=p.w(3))
    p.rect((6, 52, 94, 62), r=4, fill=(236, 150, 100, 255))
    for x, y in ((34, 30), (50, 24), (62, 34), (44, 38)):
        p.ell((x - 3, y - 2, x + 3, y + 2), fill=(222, 214, 196, 255))


def _cake_slice(p, c):
    p.poly([(8, 84), (8, 44), (92, 30), (92, 84)], fill=(255, 226, 200, 255), outline=(200, 140, 110, 255), width=3)
    p.poly([(8, 44), (92, 30), (92, 48), (8, 62)], fill=(255, 150, 180, 255))
    p.rect((8, 80, 92, 90), r=3, fill=(230, 200, 170, 255))
    p.ell((36, 16, 62, 40), fill=(226, 50, 70, 255)); p.line([(49, 18), (52, 8)], (90, 160, 70, 255), 4)


def _dango(p, c):
    p.line([(50, 4), (50, 96)], (196, 150, 90, 255), 5)
    for y, col in ((22, (255, 170, 200, 255)), (50, (255, 252, 244, 255)), (78, (150, 210, 130, 255))):
        p.ell((26, y - 15, 74, y + 15), fill=col, outline=(180, 150, 130, 255), width=3)
    p.ell((38, 12, 50, 22), fill=(255, 255, 255, 140))


def _donut(p, c):
    p.ell((6, 8, 94, 92), fill=(232, 176, 100, 255), outline=(180, 120, 60, 255), width=3)
    p.ell((10, 10, 90, 80), fill=(255, 150, 190, 255), outline=(210, 100, 140, 255), width=3)
    p.ell((34, 32, 66, 60), fill=(0, 0, 0, 0), outline=(210, 100, 140, 255), width=3)
    p.d.ellipse(p.box((36, 34, 64, 58)), fill=(0, 0, 0, 0))
    for x, y, col in ((24, 30, (120, 190, 250, 255)), (68, 26, (255, 230, 100, 255)), (76, 52, (140, 220, 140, 255)), (22, 56, (255, 255, 255, 255)), (50, 18, (255, 255, 255, 255))):
        p.line([(x, y), (x + 6, y + 3)], col, 4)


def _strawberry(p, c):
    p.poly([(14, 28), (86, 28), (62, 90), (38, 90)], fill=(228, 52, 72, 255), outline=(170, 30, 50, 255), width=3)
    p.ell((10, 18, 90, 62), fill=(228, 52, 72, 255)); p.d.ellipse(p.box((10, 18, 90, 62)), outline=(170, 30, 50, 255), width=p.w(3))
    for x, y in ((30, 40), (50, 36), (70, 40), (38, 58), (60, 58), (50, 74)):
        p.ell((x - 3, y - 3, x + 3, y + 4), fill=(255, 226, 150, 255))
    for a in (-50, -20, 0, 20, 50):
        p.line([(50, 20), (50 + a * .6, 8 - abs(a) * .05)], (80, 170, 80, 255), 8)


def _banana(p, c):
    edge, body = (196, 150, 20, 255), (255, 224, 80, 255)
    p.arc((8, -14, 104, 82), 25, 155, edge, 30)
    p.arc((8, -14, 104, 82), 28, 152, body, 22)
    p.line([(14, 36), (8, 24)], (120, 90, 40, 255), 9)
    p.ell((84, 66, 94, 76), fill=(110, 80, 40, 255))


def _drink(p, c):
    p.line([(60, 4), (56, 30)], (240, 90, 110, 255), 6)
    p.poly([(22, 28), (78, 28), (70, 94), (30, 94)], fill=(150, 210, 250, 255), outline=(80, 140, 190, 255), width=3)
    p.rect((16, 20, 84, 32), r=4, fill=(255, 255, 255, 255), outline=(80, 140, 190, 255), width=3)
    p.poly([(26, 52), (74, 52), (70, 90), (30, 90)], fill=(255, 150, 110, 255))
    p.ell((36, 62, 46, 72), fill=(255, 255, 255, 140))


def _tea(p, c):
    p.rect((10, 38, 76, 88), r=10, fill=(255, 252, 244, 255), outline=(150, 140, 120, 255), width=3)
    p.rect((14, 40, 72, 52), r=4, fill=(140, 190, 90, 255))
    p.arc((60, 44, 96, 76), 270, 90, (150, 140, 120, 255), 6)
    for x in (30, 46, 60):
        p.arc((x - 8, 6, x + 8, 30), 90, 270, (190, 200, 210, 255), 4)


def _soccer(p, c):
    p.ell((6, 6, 94, 94), fill=(255, 255, 255, 255), outline=(60, 60, 60, 255), width=4)
    dark = (50, 50, 56, 255)
    p.poly([(50, 30), (68, 44), (61, 66), (39, 66), (32, 44)], fill=dark)
    for a in range(5):
        ang = math.pi * 2 / 5 * a - math.pi / 2
        x, y = 50 + 34 * math.cos(ang), 50 + 34 * math.sin(ang)
        p.line([(50 + 20 * math.cos(ang), 50 + 20 * math.sin(ang)), (x, y)], dark, 4)
        p.ell((x - 7, y - 7, x + 7, y + 7), fill=dark)


def _basketball(p, c):
    p.ell((6, 6, 94, 94), fill=(240, 130, 50, 255), outline=(70, 40, 20, 255), width=4)
    dark = (70, 40, 20, 255)
    p.line([(50, 6), (50, 94)], dark, 4, round_caps=False); p.line([(6, 50), (94, 50)], dark, 4, round_caps=False)
    p.arc((-30, 8, 38, 92), -60, 60, dark, 4); p.arc((62, 8, 130, 92), 120, 240, dark, 4)


def _yarn(p, c):
    p.ell((8, 8, 88, 88), fill=(196, 130, 220, 255), outline=(120, 70, 160, 255), width=4)
    dark = (128, 78, 170, 255)
    for box, a0, a1 in (((6, 20, 96, 74), 190, 340), ((14, 36, 100, 98), 200, 330), ((-4, 8, 70, 84), 330, 70), ((20, -4, 100, 80), 100, 200)):
        p.arc(box, a0, a1, dark, 4)
    p.ell((22, 18, 40, 32), fill=(230, 190, 250, 200))
    p.line([(78, 76), (92, 82), (88, 94)], (196, 130, 220, 255), 5)


def _question(p, c):
    p.arc((26, 8, 74, 52), 180, 450, c, 11)
    p.line([(50, 50), (50, 64)], c, 11); p.ell((43, 76, 57, 90), fill=c)


def _zed(p, c):
    p.line([(22, 24), (78, 24), (22, 76), (78, 76)], c, 13)


def _sunflower(p, c):
    for i in range(12):
        a = math.pi / 6 * i
        x, y = 50 + 31 * math.cos(a), 50 + 31 * math.sin(a)
        p.ell((x - 11, y - 11, x + 11, y + 11), fill=(255, 205, 50, 255), outline=(224, 160, 20, 255), width=2)
    p.ell((28, 28, 72, 72), fill=(130, 84, 40, 255), outline=(96, 60, 28, 255), width=3)
    for x, y in ((42, 42), (58, 42), (50, 50), (42, 58), (58, 58)):
        p.ell((x - 3, y - 3, x + 3, y + 3), fill=(180, 126, 70, 255))


def _pin(p, c):
    p.line([(36, 62), (18, 90)], (150, 150, 160, 255), 6)
    p.poly([(36, 26), (64, 54), (54, 64), (26, 36)], fill=(230, 70, 70, 255), outline=(170, 40, 40, 255), width=3)
    p.ell((50, 10, 88, 48), fill=(240, 90, 90, 255), outline=(170, 40, 40, 255), width=3)
    p.ell((60, 18, 70, 28), fill=(255, 255, 255, 150))


ART = {
    "question": _question, "zed": _zed, "sunflower": _sunflower, "pin": _pin,
    "close": _close, "minus": _minus, "check": _check, "prev": _prev, "next": _next, "menu": _menu, "expand": _expand,
    "shrink": _shrink, "swap": _swap, "grip": _grip, "chevron": _chevron, "pencil": _pencil, "note": _note, "notes": _notes,
    "sparkle": _sparkle, "flower": _flower, "repeat": _repeat,
    "heart": _heart, "coin": _coin, "capsule": _capsule, "trophy": _trophy, "lock": _lock, "blank": _blank,
    "headphones": _headphones, "folder": _folder, "folder_open": _folder_open, "clock": _clock, "candy": _candy, "warn": _warn,
    "zzz": _zzz, "camera": _camera, "party": _party, "dice": _dice, "bento": _bento, "birthday": _birthday,
    "hand_paper": lambda p, c: _hand(p, "paper"), "hand_rock": lambda p, c: _hand(p, "rock"), "hand_scissors": lambda p, c: _hand(p, "scissors"),
    # 食物、玩具
    "飯糰": _onigiri, "白飯": _rice, "蛋糕": _cake_slice, "糰子": _dango, "甜甜圈": _donut, "草莓": _strawberry, "香蕉": _banana,
    "飲料": _drink, "熱茶": _tea, "足球": _soccer, "籃球": _basketball, "毛線球": _yarn,
}


def draw_icon(name, size, color=None):
    """畫一個 size×size 的小圖。單色圖示用 color（顏色字串 "#rrggbb" 或 (r, g, b)），沒給就是深褐色。"""
    p = _Pen(size)
    col = _rgba(color) if (name in MONO or color is not None) else None
    ART[name](p, _rgba(color) if name in MONO else (_rgba(color) if color is not None else None))
    return p.out(size)


_CACHE = {}


def icon_pil(name, size, color=None):
    key = (name, size, _rgba(color) if color is not None else None)
    if key not in _CACHE:
        _CACHE[key] = draw_icon(name, size, color)
    return _CACHE[key]
