"""DesktopPet：AI 娘桌寵（小克、GPT、大肥魚、Gemini、GLM、千問……可以同時叫出好幾隻）

資料夾結構（相對於 DesktopPet.exe 所在位置）
    characters/<角色>/*.webp          立繪，檔名 = 姿態名，-2、-3 是同一姿態的第二、三張
    characters/<角色>/character.json  名字、顏色、台詞
    characters/dialogs.json           角色碰在一起時的對話
    settings.json                     自動存的設定（誰在桌面上、大小、衣服、好感度……）

操作
    左鍵點一下      摸摸頭（她生氣時就是在哄她；睡著時會被叫醒）
    左鍵點兩下      跳一下（貼在螢幕邊時：出來）
    左鍵拖曳        拎起來；抓著畫圈她會跟著甩；快速左右甩會暈、越甩越氣；放手會被丟出去
    丟到螢幕左右邊  貼邊，只露半個身子，滑鼠靠近會探頭
    丟到別隻身上    慢慢放＝抱抱，用力丟＝撞飛
    中鍵 / Ctrl+左鍵 戳一下
    右鍵            選單
"""
import ctypes
import datetime
import json
import math
import random
import re
import subprocess
import sys
import time
import traceback
import tkinter as tk
from tkinter import ttk
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).resolve().parent
else:
    BASE = Path(__file__).resolve().parent.parent
CHAR_DIR = BASE / "characters"
SETTINGS = BASE / "settings.json"
LOG = BASE / "error.log"

TICK_MS = 33                     # 邏輯一格
FRAME_MS = 16                    # 畫面一格：兩個畫面格算一個邏輯格，中間那格只挪視窗位置
FPS = 1000 / TICK_MS
SIZES = {"特小": 170, "小": 210, "中": 260, "大": 330, "特大": 420}
BUBBLE_SCALE = {"特小": .9, "小": 1.0, "中": 1.12, "大": 1.25, "特大": 1.4}    # 泡泡跟著大小縮放
SLEEP_AFTER = 8 * 60             # 秒：沒人理她多久會睡著
AWAY_AFTER = 10 * 60             # 秒：鍵盤滑鼠都沒動多久算「你離開了」
GRAVITY = 0.8
# 拎起來的物理：(左右門檻, 左右力道, 上下門檻, 上下力道, 重力)；依照實際錄下來的甩動調過
DRAG = [12.0, .65, 16.0, .29, 2.6, .38]
SETTLE = [.17, .95, .004]      # 停手後回正：(回正力, 每格保留的速度, 摩擦)
THROW_SCALE = 0.5
SHOW_ORDER = ["claude", "deepseek", "gpt", "gemini", "qwen", "glm"]
LOVE_LEVELS = [0, 10, 30, 60, 100, 160, 240, 340, 480, 666]

FALLBACK = {
    "pat": ["happy"], "pout": ["surprised"], "oops": ["surprised"], "dizzy": ["oops", "surprised"],
    "annoyed": ["pout", "surprised"], "puffed": ["annoyed", "pout", "surprised"],
    "redhot": ["puffed", "annoyed", "surprised"], "sulk": ["annoyed"], "coaxed": ["pat", "happy"],
    "forgiven": ["happy"], "feast": ["eat", "happy"], "eat": ["happy"], "writing": ["reading", "thinking"],
    "reading": ["thinking"], "proud": ["happy"], "tired": ["yawn"], "bye": ["happy"],
    "deepthink": ["thinking"], "drawing": ["writing", "reading"],
}
MOTION = {
    "happy": "jump", "proud": "hop", "forgiven": "hop", "gift": "hop", "reset": "hop", "feast": "bob",
    "pat": "sway", "coaxed": "sway", "hum": "sway", "clawd": "sway", "masked": "sway",
    "surprised": "jolt", "pout": "jolt", "puffed": "jolt", "pricetag": "jolt",
    "oops": "shake", "annoyed": "rock", "redhot": "angry", "sulk": "slow", "dizzy": "dizzy",
    "float": "float", "swim": "float", "eat": "bob", "soldout": "bob",
    "sleeping": "breathe", "slack": "breathe",
}
FAST_MOTION = {"jump", "hop", "jolt", "shake", "angry"}
EMIT = {
    "hum": ("note", 18), "sleeping": ("z", 32), "redhot": ("steam", 5), "dizzy": ("sweat", 22),
    "swim": ("bubble", 12), "eat": ("steam", 20), "feast": ("sparkle", 8), "float": ("sparkle", 14),
    "happy": ("sparkle", 16), "proud": ("sparkle", 10), "forgiven": ("heart", 14), "coaxed": ("heart", 30),
    "pat": ("heart", 22), "deepthink": ("bubble", 14),
}
ACTION_NAMES = {
    "hum": "哼歌", "stretch": "伸懶腰", "yawn": "打哈欠", "reading": "看書", "writing": "寫字",
    "thinking": "思考", "drawing": "畫畫", "happy": "開心", "proud": "得意", "surprised": "驚訝",
    "oops": "出錯了", "tired": "累了", "pout": "嘟嘴", "clawd": "抱 Clawd", "eat": "吃飯",
    "feast": "大吃一頓", "slack": "摸魚", "swim": "游泳", "deepthink": "深度思考", "float": "飄起來",
    "masked": "戴眼罩", "soldout": "售罄", "pricetag": "改價籤", "gift": "送禮物", "reset": "重置了！",
    "sorry": "你說得對", "dizzy": "暈", "annoyed": "不耐煩", "puffed": "鼓臉", "redhot": "氣炸",
    "sulk": "賭氣", "sleeping": "睡覺",
}
POSE_NAMES = dict(ACTION_NAMES, **{
    "idle": "待機", "pat": "被摸頭", "coaxed": "被哄", "forgiven": "原諒你", "bye": "揮手掰掰",
    "greet_morning": "早安", "greet_noon": "午安", "greet_afternoon": "下午好", "greet_evening": "晚上好",
    "greet_night": "深夜", "greet_dawn": "凌晨", "fest_newyear": "元旦裝", "fest_spring": "春節裝",
    "fest_lantern": "元宵裝", "fest_dragonboat": "端午裝", "fest_midautumn": "中秋裝",
    "fest_halloween": "萬聖節裝", "fest_christmas": "聖誕裝", "fest_national": "旅行裝",
    "listening": "聽你說", "running": "敲鍵盤", "searching": "查資料", "delegating": "派任務",
    "compact": "塞箱子", "asking": "等你回答", "busy": "忙碌", "swamped": "忙不過來", "update": "送禮物",
    "busy_left": "往左看", "busy_right": "往右看", "swamped_left": "忙翻了（左）", "swamped_right": "忙翻了（右）",
    "reset_bell": "敲鐘宣布", "reset_check": "查手機", "reset_hope": "期待", "reset_maybe": "也許吧", "reset_nope": "沒消息",
})
ITEMS = {   # 名稱: (emoji, 種類)；只用 Windows 10 內建 emoji 字型有的字
    "飯糰": ("🍙", "food"), "白飯": ("🍚", "food"), "蛋糕": ("🍰", "food"), "糰子": ("🍡", "food"),
    "甜甜圈": ("🍩", "food"), "草莓": ("🍓", "food"), "香蕉": ("🍌", "food"), "飲料": ("🥤", "food"),
    "熱茶": ("🍵", "food"), "足球": ("⚽", "toy"), "籃球": ("🏀", "toy"), "毛線球": ("🧶", "toy"),
}
RPS = {"剪刀": "✌️", "石頭": "✊", "布": "✋"}
BEATS = {"剪刀": "布", "石頭": "剪刀", "布": "石頭"}
FORTUNES = [("大吉", 12), ("中吉", 20), ("小吉", 24), ("吉", 22), ("末吉", 14), ("凶", 8)]
LUCKY = ["鯛魚燒", "白飯", "珍珠奶茶", "書籤", "橘色的東西", "藍色的筆", "熱可可", "耳機", "便利貼",
         "早點睡覺", "雨傘", "一顆蘋果", "Clawd 娃娃", "新的筆記本", "散步十分鐘"]
ADVICE = ["今天適合把拖延的小事做完", "記得多喝水", "會有意想不到的好消息", "適合整理桌面",
          "跟朋友聊聊天會很開心", "別熬夜，明天會更順", "專心一件事就會很順利", "適合學新東西",
          "小心不要粗心", "吃點甜的會有好運", "出門走走會有收穫", "今天的努力會被看見"]
FOODS = ["滷肉飯", "牛肉麵", "雞排", "鹹酥雞", "便當", "水餃", "拉麵", "火鍋", "炒飯", "咖哩飯", "鍋燒意麵",
         "義大利麵", "壽司", "蛋餅加豆漿", "臭豆腐", "麥當勞", "雞肉飯", "蚵仔煎", "肉圓", "麻辣燙", "韓式炸雞",
         "牛排", "滷味", "涼麵", "陽春麵", "飯糰", "蔥油餅", "披薩"]
JOKES = [
    "什麼東西越洗越髒？\n……水。",
    "哪一個月有二十八天？\n每個月都有喔～",
    "飛機飛那麼高，為什麼不會撞到星星？\n因為星星會「閃」。",
    "什麼門永遠關不上？\n球門。",
    "什麼東西有頭沒有腳？\n磚頭。",
    "打什麼東西不用力氣？\n打哈欠～",
    "什麼蛋不能吃？\n笨蛋。",
    "什麼東西明明是你的，別人卻用得比你多？\n你的名字。",
    "冰塊最想做什麼？\n退伍，因為它當冰（兵）很久了。",
    "番茄、馬鈴薯、小黃瓜過馬路，番茄被壓扁了。\n馬鈴薯回頭喊：番茄醬，快跟上！",
    "為什麼魚不會說話？\n因為牠們一開口就會吐泡泡。",
    "什麼路最窄？\n冤家路窄。",
]
TOPIC_REACT = ["原來如此！", "好專業～", "筆記筆記……", "這個考試會考嗎？", "我也正想說！", "聽起來好難……",
               "妳懂好多喔！", "再說一次，我沒聽懂", "（認真點頭）", "記下來了！"]
TALK_FREQ = {"常常": (25, 50), "偶爾": (60, 140), "很少": (150, 300)}
RARITY = [("N", 55), ("R", 30), ("SR", 12), ("SSR", 3)]
R_POSES = {"happy", "pat", "sleeping", "proud", "forgiven", "coaxed", "hum", "yawn", "stretch", "drawing",
           "reading", "writing", "eat", "feast", "swim", "float", "clawd", "bye"}
RARITY_COLOR = {"N": "#9a8a80", "R": "#4a8fd6", "SR": "#b05bd6", "SSR": "#e0a020"}


def card_poses(ch):
    return [q for q in ch.poses if not q.startswith(("edge_", "idle-blink")) and q != "idle"]


def rarity_of(ch, base, pose):
    if pose.startswith("fest_"):
        return "SSR"
    special = set(ch.cfg.get("idleActions") or base.cfg.get("idleActions") or [])
    if pose.startswith("greet_") or pose in special:
        return "SR"
    return "R" if pose in R_POSES else "N"
# 惹她生氣：(名稱, 台詞 key, 怒氣, 姿勢)
TEASES = [("捏臉頰", "tease_cheek", 21, "puffed"), ("彈額頭", "tease_flick", 25, "surprised"),
          ("說她胖", "tease_fat", 39, "puffed"), ("摸亂她的頭髮", "tease_hair", 31, "annoyed"),
          ("搶她的點心", "tease_snack", 45, "pout")]
ANGER_DECAY = 1.6        # 每秒自然消氣（100 → 0 大約一分鐘）
SULK_DECAY = .25         # 賭氣時每秒自然消氣（很慢，要餵東西才快）
SULK_END = 40            # 賭氣時怒氣降到這以下就原諒你
ANGER_FULL = 95          # 怒氣到這裡算氣滿 → 賭氣
LOVE_TITLES = ["", "初次見面", "認識的人", "朋友", "好朋友", "好夥伴", "摯友", "心靈相通", "最重要的人",
               "命運的羈絆", "永遠在一起"]
LOVE_UNLOCKS = {3: "摸頭時偶爾說真心話", 5: "每天送你一個小禮物", 7: "巨大化時說更多真心話",
                10: "一起度過的每一天都會被記住"}
STAT_NAMES = [("pat", "摸頭"), ("feed", "餵食"), ("poke", "戳／惹她"), ("game", "小遊戲"), ("fly", "飛高高"),
              ("hug", "抱抱"), ("study", "陪讀"), ("found", "捉迷藏找到")]
GENERIC = {
    "kick": ["嘿！"], "chase": ["等等！"], "bump": ["好痛！"], "spin": ["轉暈了……"],
    "levelup": ["好感度上升了！"], "love": ["最喜歡你了"], "comfort": ["不氣了不氣了～"],
    "rps_win": ["我贏了！"], "rps_lose": ["輸了……"], "rps_draw": ["平手！"], "remind": ["時間到囉！"],
    "welcome": ["歡迎回來！"], "meal": ["吃飯時間到了～"], "party": ["派對開始！"],
    "race_start": ["我會贏的！"], "race_win": ["第一名！"], "race_lose": ["差一點……"],
    "share": ["分我一口！"], "eat_lose": ["被搶走了……"], "fortune": ["幫你看看今天的運勢～"],
    "stack_top": ["好高～", "風景不錯！", "嘿嘿，我在上面"], "stack_bottom": ["好重……", "下、下去啦！", "頭、頭要被壓扁了"],
    "jealous": ["我也要摸！", "都只摸她……", "（嘟嘴）我也在這裡耶"], "jealous_ok": ["嘿嘿……這還差不多", "早說嘛～"],
    "tag_start": ["我當鬼！", "來抓人囉～"], "tag_caught": ["抓到了！換你當鬼！", "抓到你了！"],
    "tag_got": ["被抓到了～", "可惡！"], "tag_end": ["好累……", "跑不動了～", "好好玩！"],
    "tease": ["抓到你了！", "嘿！", "別跑！"], "climb": ["嘿咻！", "上去看看～"], "ride": ["哇——！", "晃、晃得好厲害！"],
    "fall": ["哇啊——掉下去了！", "地板不見了！"], "found": ["被找到了！", "嗚，好快！", "你怎麼知道我在這裡？"],
    "hs_count": ["我數到五喔～\n1、2、3、4、5！好了沒？"], "trip": ["哎呀！", "痛痛……", "跌倒了……"],
    "pat_friend": ["乖～摸摸", "今天也辛苦了", "摸摸頭～"],
    "visit": ["找到你了！", "在做什麼呀？", "嗨～", "（抬頭看你）"],
    "cling": ["陪我玩嘛～", "理我一下嘛～", "（拉拉你的袖子）"], "cling_got": ["抓到你了～摸摸我嘛", "嘿嘿～"],
    "cling_abort": ["哼～", "小氣……"], "candy_win": ["答對了！這顆給你 🍬", "猜中了～好厲害"],
    "candy_lose": ["猜錯囉～是這隻手！", "嘿嘿，在這裡～"], "joke_after": ["……好笑嗎？", "（等你笑）"],
    "food_pick": ["今天就吃這個吧！", "我覺得這個不錯～"],
    "tease_cheek": ["不、不要捏臉！", "（鼓臉）", "臉會被捏扁的啦！"],
    "tease_flick": ["好痛！", "彈什麼額頭啦！", "嗚……額頭紅了"],
    "tease_hair": ["我的頭髮！剛整理好的耶！", "不要把我的頭髮摸亂啦～", "髮型亂掉了啦！"],
    "tease_fat": ["誰、誰胖了！", "我才不胖！", "你再說一次看看？"],
    "tease_snack": ["那是我的點心！還給我！", "嗚……我的點心……", "小偷！"],
    "checkin": ["今天也來了呢～", "簽到成功！", "等你好久了～"], "gift": ["這個給你！", "送你的～", "收下吧！"],
    "birthday": ["生日快樂！🎂", "祝你生日快樂～今天是你的日子！"],
    "todo_remind": ["「{t}」時間到了喔！", "提醒你：「{t}」時間到了！"],
    "todo_soon": ["「{t}」還剩 {m} 分鐘喔！", "提醒一下，「{t}」再 {m} 分鐘就到了～"], "todo_done": ["好棒！完成了！", "辛苦了～", "又完成一件！"],
    "want_food": ["給我的嗎？", "好香～", "（盯——）"], "want_toy": ["要玩嗎？", "丟給我！"],
    "snatch": ["搶到了！", "嘿嘿，是我的了"], "food_forgive": ["……看在食物的份上，原諒你", "好吧，不氣了"],
    "food_wake": ["好香……！", "（聞聞）有吃的？"],
    "mis_pat": ["摸我嘛～", "（把你的手拉到頭上）"], "mis_poke": ["嘿嘿，戳戳～", "（自己戳自己的臉）"],
    "mis_eat": ["啊嗚——！"], "mis_chew": ["（嚼嚼）", "（嚼嚼嚼）"], "mis_spit": ["呸！不好吃！", "呸呸！是塑膠的味道！"],
    "mis_carry": ["我搶到了～", "抓不到我～"], "mis_return": ["還你～", "好啦，還給你"],
    "full": ["吃不下了……", "好飽……肚子要撐破了", "等一下再吃好不好"],
    "sulk_ignore": ["哼。", "……（不理你）", "（背對你）"], "sulk_food": ["……好吃。（但還在生氣）", "哼……（一邊吃一邊瞪你）"],
    "no_play": ["……不想玩。", "哼，不要。"], "yarn": ["喵！毛線球！", "喵喵喵！"],
    "fly": ["飛高高～！", "哇——好高！", "咻——！"], "fly_top": ["好高！看得好遠～", "哇，雲在旁邊！"],
    "fly_land": ["再一次！再一次！", "好好玩～"], "catch": ["接住了！", "嘿嘿，被你接住了"],
}
# 看你在做什麼：(類別, 程式檔名, 視窗標題關鍵字)，由上往下比對
APPS = [
    ("video", (), ("YouTube", "bilibili", "嗶哩", "Netflix", "Twitch", "動畫瘋", "Disney+", "愛奇藝")),
    ("video", ("vlc.exe", "potplayer64.exe", "potplayermini64.exe", "mpc-hc64.exe"), ()),
    ("music", ("spotify.exe", "kkbox.exe"), ("YouTube Music", "Spotify")),
    ("hardware", ("quartus.exe", "quartus_pgmw.exe", "vivado.exe", "modelsim.exe", "vsim.exe"), ()),
    ("code", ("code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "notepad++.exe", "sublime_text.exe",
              "cursor.exe", "windowsterminal.exe"), ()),
    ("office", ("winword.exe", "powerpnt.exe", "excel.exe"), ("Google 文件", "Google Docs", "Overleaf")),
    ("reading", ("acrord32.exe", "acrobat.exe", "sumatrapdf.exe"), (".pdf",)),
    ("chat", ("line.exe", "discord.exe", "telegram.exe"), ("Messenger", "Discord", "LINE")),
]
APP_REACT = {
    "video": ("happy", ["在看什麼？我也要看！", "這部好看嗎？", "（湊過來看）"]),
    "music": ("hum", ["♪ 這首歌好好聽", "一起聽～", "♪～"]),
    "hardware": ("thinking", ["在做電路嗎？好厲害", "編譯會過的，加油！", "波形看起來很順利呢"]),
    "code": ("writing", ["在寫程式嗎？加油！", "記得存檔喔～", "我也來幫忙想想"]),
    "office": ("reading", ["在寫報告嗎？加油！", "打字打好快～", "寫累了要休息喔"]),
    "reading": ("reading", ["在看論文嗎？好認真", "看書時間～我也來看", "眼睛要休息喔"]),
    "chat": ("hum", ["在跟誰聊天呀？", "幫我也打聲招呼～", "聊得好開心的樣子"]),
}
PERIODS = [(5, 11, "morning"), (11, 14, "noon"), (14, 18, "afternoon"), (18, 23, "evening"),
           (23, 26, "night"), (2, 5, "dawn")]
LUNAR = {
    2026: {"spring": (2, 17), "lantern": (3, 3), "dragonboat": (6, 19), "midautumn": (9, 25)},
    2027: {"spring": (2, 6), "lantern": (2, 20), "dragonboat": (6, 9), "midautumn": (9, 15)},
    2028: {"spring": (1, 26), "lantern": (2, 9), "dragonboat": (5, 28), "midautumn": (10, 3)},
}


def festival_today():
    d = datetime.date.today()
    md = (d.month, d.day)
    if md == (1, 1):
        return "fest_newyear"
    if md == (10, 31):
        return "fest_halloween"
    if md in ((12, 24), (12, 25)):
        return "fest_christmas"
    lun = LUNAR.get(d.year, {})
    if "spring" in lun and 0 <= (d - datetime.date(d.year, *lun["spring"])).days < 7:
        return "fest_spring"
    for k in ("lantern", "dragonboat", "midautumn"):
        if lun.get(k) == md:
            return "fest_" + k
    return None


def period_now():
    h = datetime.datetime.now().hour
    hh = h + 24 if h < 2 else h
    for a, b, name in PERIODS:
        if a <= hh < b:
            return name
    return "dawn"


WEEKDAYS = "一二三四五六日"


def time_text(now=None):
    """「凌晨 3 點」「中午 12 點半」這種口語時間。"""
    now = now or datetime.datetime.now()
    h, m = now.hour, now.minute
    part = ("半夜" if h == 0 else "凌晨" if h < 5 else "早上" if h < 11 else "中午" if h < 13 else "下午" if h < 18 else "晚上")
    h12 = h if h <= 12 else h - 12
    if h == 0:
        h12 = 12
    tail = "點半" if 25 <= m < 45 else "點"
    if m >= 45:
        tail = "點多" if h12 else "點"
    return f"{part} {h12} {tail}"


# 依時段的時間台詞：(開始, 結束, [台詞])，{t} 會換成「凌晨 3 點」這樣的時間
TIME_LINES = [
    (0, 5, ["現在{t}了，你還不睡覺！", "都{t}了，明天會起不來喔", "{t}了……我好睏，你也快去睡", "這麼晚了還醒著？{t}了耶"]),
    (5, 9, ["早安！現在{t}，吃早餐了嗎？", "{t}了，今天也要加油喔", "好早喔，{t}就起來了"]),
    (9, 11.5, ["{t}了，今天的進度還順利嗎？", "{t}，喝杯水吧～"]),
    (11.5, 13.5, ["{t}了，該吃午餐囉！", "{t}，午餐想吃什麼？", "肚子餓了～{t}了耶"]),
    (13.5, 15, ["{t}了，吃飽飯會不會想睡？", "{t}，打起精神來～"]),
    (15, 16.5, ["{t}了，要不要來點下午茶？", "{t}，休息一下眼睛吧"]),
    (16.5, 18, ["{t}了，今天快結束囉，加油！", "{t}，再撐一下～"]),
    (18, 20, ["{t}了，晚餐想吃什麼？", "{t}，吃晚餐了嗎？"]),
    (20, 22.5, ["{t}了，今天辛苦了", "{t}，要不要放鬆一下？"]),
    (22.5, 24, ["{t}了，差不多該準備睡覺囉", "都{t}了，別熬夜喔"]),
]
WEEK_LINES = {0: ["星期一，新的一週，加油！"], 4: ["星期五了！明天就放假了～"], 5: ["今天是星期六，好好休息～"],
              6: ["星期天，今天想做什麼？", "星期天要好好放鬆喔"]}


def time_line(p=None):
    now = datetime.datetime.now()
    hf = now.hour + now.minute / 60
    if random.random() < .2 and now.weekday() in WEEK_LINES and 7 <= now.hour <= 21:
        return random.choice(WEEK_LINES[now.weekday()])
    for a, b, lines in TIME_LINES:
        if a <= hf < b:
            own = p.lines(f"time_{a}") if p else []
            return random.choice(own or lines).format(t=time_text(now))
    return None


def time_tags():
    h = datetime.datetime.now().hour
    tags = set()
    if 5 <= h < 11:
        tags.add("morning")
    if h >= 21 or h < 2:
        tags.add("night")
    if h < 5:
        tags.add("late")
    return tags


def dbg(msg):
    """撒嬌等功能的除錯紀錄（debug.log，不會上傳）。"""
    try:
        f = BASE / "debug.log"
        if f.exists() and f.stat().st_size > 300_000:
            f.write_text("", encoding="utf-8")
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.now():%m-%d %H:%M:%S} {msg}\n")
    except Exception:
        pass


def log_error(*exc):
    try:
        ctypes.windll.user32.ClipCursor(None)
    except Exception:
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(datetime.datetime.now().isoformat() + "\n")
            traceback.print_exception(*(exc or sys.exc_info()), file=f)
    except Exception:
        pass


# ---------------------------------------------------------------- Win32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


user32.GetParent.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE),
    wintypes.HDC, ctypes.POINTER(wintypes.POINT), wintypes.DWORD, ctypes.POINTER(BLENDFUNCTION),
    wintypes.DWORD]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                   ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.GetTickCount.restype = wintypes.DWORD


user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.UINT]


class LayeredWindow:
    """把 PIL RGBA 圖直接貼成視窗外觀：邊緣半透明、透明的地方點得穿。"""

    def __init__(self, tkwin):
        tkwin.update_idletasks()
        self.hwnd = user32.GetParent(tkwin.winfo_id()) or tkwin.winfo_id()
        ex = user32.GetWindowLongW(self.hwnd, -20)
        user32.SetWindowLongW(self.hwnd, -20, ex | 0x00080000 | 0x00000080)   # LAYERED | TOOLWINDOW
        self.pos = (0, 0)
        self.dib = None                  # (寬, 高, mem DC, bitmap, bits)：同樣大小就重複用

    def _dib(self, w, h):
        if self.dib and self.dib[:2] == (w, h):
            return self.dib
        if self.dib:
            gdi32.DeleteObject(self.dib[3])
            gdi32.DeleteDC(self.dib[2])
        screen = user32.GetDC(None)
        mem = gdi32.CreateCompatibleDC(screen)
        bmi = BITMAPINFOHEADER(40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(screen, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        gdi32.SelectObject(mem, hbmp)
        user32.ReleaseDC(None, screen)
        self.dib = (w, h, mem, hbmp, bits)
        return self.dib

    def show(self, img, x, y):
        w, h = img.size
        data = img.convert("RGBa").tobytes("raw", "BGRa")      # 預乘 alpha、轉 BGRA（C 實作，快）
        _, _, mem, hbmp, bits = self._dib(w, h)
        ctypes.memmove(bits, data, len(data))
        screen = user32.GetDC(None)
        user32.UpdateLayeredWindow(self.hwnd, screen, ctypes.byref(wintypes.POINT(int(x), int(y))),
                                   ctypes.byref(wintypes.SIZE(w, h)), mem,
                                   ctypes.byref(wintypes.POINT(0, 0)), 0,
                                   ctypes.byref(BLENDFUNCTION(0, 0, 255, 1)), 2)
        user32.ReleaseDC(None, screen)
        self.pos = (int(x), int(y))

    def move(self, x, y):
        """只挪位置，不重畫（中間格用，很便宜）。"""
        x, y = int(x), int(y)
        if (x, y) != self.pos:
            user32.SetWindowPos(self.hwnd, None, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010)   # NOSIZE|NOZORDER|NOACTIVATE
            self.pos = (x, y)

    def raise_(self):
        user32.SetWindowPos(self.hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


user32.MonitorFromPoint.restype = wintypes.HANDLE
user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.ClipCursor.argtypes = [ctypes.c_void_p]


def lock_cursor(x, y):
    """把滑鼠鎖在 (x, y) 這一點：你怎麼動都動不了。"""
    r = wintypes.RECT(int(x), int(y), int(x) + 1, int(y) + 1)
    user32.ClipCursor(ctypes.byref(r))


def unlock_cursor():
    user32.ClipCursor(None)


user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]


def pointer_vanish(on=None):
    """Windows「打字時隱藏指標」：不給參數＝讀目前設定；給 True/False＝暫時改（不寫進系統設定）。"""
    if on is None:
        v = wintypes.BOOL()
        user32.SystemParametersInfoW(0x1020, 0, ctypes.byref(v), 0)
        return bool(v.value)
    user32.SystemParametersInfoW(0x1021, 0, ctypes.c_void_p(1 if on else 0), 0)


def wake_cursor():
    """送一個真的滑鼠移動（往右 1 再往左 1），讓被藏起來的游標現身。"""
    user32.mouse_event(0x0001, 1, 0, 0, None)
    user32.mouse_event(0x0001, ctypes.c_uint32(-1).value, 0, 0, None)


def move_cursor(x, y):
    """用「模擬滑鼠移動」搬游標：跟真的移動一樣，打字時被隱藏的游標也會顯示出來。"""
    vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    vw, vh = max(1, user32.GetSystemMetrics(78)), max(1, user32.GetSystemMetrics(79))
    nx = int((x - vx) * 65535 / max(1, vw - 1))
    ny = int((y - vy) * 65535 / max(1, vh - 1))
    user32.mouse_event(0x0001 | 0x8000 | 0x4000, nx, ny, 0, None)     # MOVE | ABSOLUTE | VIRTUALDESK
    user32.SetCursorPos(int(x), int(y))                                  # 再確保位置精準


def _rect(r):
    return r.left, r.top, r.right, r.bottom


def monitor_of(hmon):
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    return _rect(mi.rcWork), _rect(mi.rcMonitor)


def work_area(x=None, y=None):
    """(左, 上, 右, 下)：不給座標是主螢幕，給座標是那一點所在螢幕的工作區（扣掉工作列）。"""
    if x is None:
        r = wintypes.RECT()
        user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
        return _rect(r)
    return monitor_of(user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2))[0]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsZoomed.argtypes = [wintypes.HWND]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
try:
    dwmapi = ctypes.windll.dwmapi
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
except OSError:
    dwmapi = None
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                               ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
MY_PID = kernel32.GetCurrentProcessId()


def window_rect(hwnd):
    """視窗看得到的範圍（扣掉 Win10 視窗外圍看不見的陰影邊）。"""
    r = wintypes.RECT()
    if not (dwmapi and dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) == 0):
        user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def window_ok(hwnd):
    return (user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd)
            and not user32.IsZoomed(hwnd))


def list_windows():
    """畫面上看得到的一般視窗，從最上層排到最下層：[(hwnd, 左, 上, 右, 下, 可以站)]"""
    out = []

    def cb(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd) or user32.GetWindowTextLengthW(hwnd) == 0:
                return True
            if user32.GetWindowLongW(hwnd, -20) & 0x80:          # 工具視窗
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == MY_PID:
                return True
            if dwmapi:
                cloaked = wintypes.DWORD()
                dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
                if cloaked.value:
                    return True
            l, t, r, b = window_rect(hwnd)
            if r - l < 120 or b - t < 80:
                return True
            stand = not user32.IsZoomed(hwnd) and r - l >= 220 and t > work_area(l + (r - l) // 2, t + 5)[1] + 140
            out.append((hwnd, l, t, r, b, stand))
        except Exception:
            pass
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def foreground_app():
    """(程式檔名小寫, 視窗標題)；是自己的視窗就回傳 None。"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == MY_PID:
        return None
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    exe = ""
    h = kernel32.OpenProcess(0x1000, False, pid.value)
    if h:
        size = wintypes.DWORD(520)
        name = ctypes.create_unicode_buffer(520)
        if kernel32.QueryFullProcessImageNameW(h, 0, name, ctypes.byref(size)):
            exe = name.value.replace("/", "\\").split("\\")[-1].lower()
        kernel32.CloseHandle(h)
    return exe, buf.value


def fullscreen_app():
    """前景視窗是不是全螢幕（看影片、玩遊戲、簡報）。桌面、工作列和自己的視窗不算。"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == kernel32.GetCurrentProcessId():
        return False
    buf = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, buf, 64)
    if buf.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        return False
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    ml, mt, mr, mb = monitor_of(user32.MonitorFromWindow(hwnd, 2))[1]
    return r.left <= ml and r.top <= mt and r.right >= mr and r.bottom >= mb


def cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def idle_seconds():
    li = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    if not user32.GetLastInputInfo(ctypes.byref(li)):
        return 0
    return ((kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000


# ---------------------------------------------------------------- 文字（缺字自動換字型）
class Text:
    CHAINS = (("msjh.ttc", "mingliu.ttc", "arial.ttf"), ("seguisym.ttf",), ("seguiemj.ttf",))

    def __init__(self):
        self.fonts = {}
        self.has = {}

    def font(self, idx, size):
        key = (idx, size)
        if key not in self.fonts:
            f = None
            for name in self.CHAINS[idx]:
                try:
                    f = ImageFont.truetype(name, size)
                    break
                except OSError:
                    continue
            self.fonts[key] = f or ImageFont.load_default()
        return self.fonts[key]

    @staticmethod
    def _sig(font, ch, emoji=False):
        im = Image.new("RGBA", (48, 48))
        ImageDraw.Draw(im).text((4, 4), ch, font=font, fill=(255, 255, 255, 255), embedded_color=emoji)
        return im.tobytes()

    def pick(self, ch, size):
        """回傳 (font, 是否 emoji)。"""
        if ch in "️‍":
            return self.font(0, size), False
        if ch not in self.has:
            choice = 0
            if ord(ch) > 0x2000 and not ch.isspace():
                for idx in (0, 1, 2):
                    f = self.font(idx, 20)
                    if self._sig(f, ch, idx == 2) != self._sig(f, "\U0010FFFD", idx == 2):
                        choice = idx
                        break
            self.has[ch] = choice
        idx = self.has[ch]
        return self.font(idx, size), idx == 2

    def width(self, d, s, size):
        return sum(d.textlength(c, font=self.pick(c, size)[0]) for c in s if c not in "️‍")

    def draw(self, d, xy, s, size, fill, anchor="la"):
        x, y = xy
        for c in s:
            if c in "️‍":
                continue
            f, emoji = self.pick(c, size)
            d.text((x, y), c, font=f, fill=fill, embedded_color=emoji, anchor=anchor)
            x += d.textlength(c, font=f)

    def emoji_image(self, ch, size):
        f = self.font(2, size)
        im = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((size // 2, size // 2), ch, font=f, embedded_color=True)
        return im.crop(im.getbbox())


TEXT = Text()


# ---------------------------------------------------------------- 角色資料
class Character:
    def __init__(self, folder):
        self.id = folder.name
        self.folder = folder
        f = folder / "character.json"
        self.cfg = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        self.base = self.cfg.get("skinOf", self.id)
        self.poses = {}
        for img in sorted(folder.glob("*.webp")) + sorted(folder.glob("*.png")):
            name = re.sub(r"-\d+$", "", img.stem)
            self.poses.setdefault(name, []).append(img)
        self.cache = {}

    def has(self, pose):
        return pose in self.poses

    def resolve(self, pose):
        if pose in self.poses:
            return pose
        for alt in FALLBACK.get(pose, []):
            if alt in self.poses:
                return alt
        return "idle" if "idle" in self.poses else next(iter(self.poses))

    def image(self, path, h):
        key = (path, h)
        im = self.cache.get(key)
        if im is None:
            src = Image.open(path).convert("RGBA")
            k = h / src.height
            im = src.resize((max(1, round(src.width * k)), h), Image.LANCZOS)
            self.cache[key] = im
        return im


# ---------------------------------------------------------------- 丟給她們的東西
class Item:
    def __init__(self, world, name, x, y):
        self.world = world
        self.name = name
        self.emoji, self.kind = ITEMS[name]
        self.img = TEXT.emoji_image(self.emoji, 44)
        self.S = 90
        self.win = tk.Toplevel(world.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{self.S}x{self.S}+0+0")
        self.lw = LayeredWindow(self.win)
        L, T, R, B = work_area(x, y)
        self.L, self.R, self.floor = L, R, B
        self.x, self.y = float(x), float(min(y, B))
        self.vx, self.vy = random.uniform(-1, 1), 0.0
        self.angle = 0.0
        self.held = None
        self.trail = []
        self.alive = True
        self.claimed = None
        self.win.bind("<ButtonPress-1>", self.on_press)
        self.win.bind("<B1-Motion>", self.on_motion)
        self.win.bind("<ButtonRelease-1>", self.on_release)
        # 右鍵「放開」時才收掉：按下和放開都留在這個視窗，桌面才不會跟著跳出右鍵選單
        self.win.bind("<ButtonPress-3>", lambda e: "break")
        self.win.bind("<ButtonRelease-3>", lambda e: self.world.root.after(1, self.remove))
        self.render()

    def on_ground(self):
        return self.held is None and self.y >= self.floor - 0.5 and abs(self.vy) < 0.5

    def on_press(self, e):
        self.held = (e.x_root, e.y_root)
        self.trail = [(e.x_root, e.y_root, e.time)]

    def on_motion(self, e):
        if self.held:
            self.x, self.y = e.x_root, e.y_root + self.img.size[1] / 2
            self.trail = (self.trail + [(e.x_root, e.y_root, e.time)])[-6:]
            self.render()
            self.world.item_hover(self, e.x_root, e.y_root)

    def on_release(self, e):
        self.held = None
        if self.world.item_drop(self, e.x_root, e.y_root):
            return
        self.L, _, self.R, self.floor = work_area(e.x_root, e.y_root)
        if len(self.trail) >= 2:
            x0, y0, t0 = self.trail[0]
            x1, y1, t1 = self.trail[-1]
            dt = max(1, t1 - t0) / TICK_MS
            self.vx = max(-22, min(22, (x1 - x0) / dt * THROW_SCALE))
            self.vy = max(-22, min(22, (y1 - y0) / dt * THROW_SCALE))

    def half_step(self):
        if self.alive and not self.held and (not self.on_ground() or abs(self.vx) > .05) and not self.angle:
            self.lw.move(self.lw.pos[0] + self.vx / 2, self.lw.pos[1] + (self.vy + GRAVITY / 2) / 2)

    def update(self):
        if self.held or not self.alive:
            return
        moving = not self.on_ground() or abs(self.vx) > 0.05
        if not moving:
            return
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
        if self.x < self.L + 20 or self.x > self.R - 20:
            self.x = max(self.L + 20, min(self.x, self.R - 20))
            self.vx = -self.vx * 0.7
        if self.y >= self.floor:
            self.y = self.floor
            bounce = 0.55 if self.kind == "toy" else 0.2
            self.vy = -self.vy * bounce if self.vy > 3 else 0
            self.vx *= 0.97 if self.kind == "toy" else 0.8
            if abs(self.vx) < 0.05:
                self.vx = 0
        if self.kind == "toy":
            self.angle -= self.vx * 3
        self.render()

    def render(self):
        S = self.S
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        spr = self.img.rotate(self.angle, resample=Image.BICUBIC, expand=True) if self.angle else self.img
        img.alpha_composite(spr, (S // 2 - spr.width // 2, S - 4 - spr.height))
        self.lw.show(img, self.x - S // 2, self.y - S + 4)

    def remove(self):
        if self.alive:
            self.alive = False
            self.win.destroy()
            if self in self.world.items:
                self.world.items.remove(self)


# ---------------------------------------------------------------- 寵物
class Pet:
    def __init__(self, world, base_id, outfit, x=None):
        self.world = world
        self.base_id = base_id
        self.win = tk.Toplevel(world.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{world.win_w}x{world.win_h}+0+0")
        self.lw = LayeredWindow(self.win)

        self.base = world.chars[base_id]
        self.char = world.chars.get(outfit, self.base)
        L, T, R, B = work_area(*(world.home or (None, None)))
        if x is not None:
            L, T, R, B = work_area(x, B - 10)
        self.L, self.R, self.floor = L, R, B
        self.x = float(x if x is not None else random.randint(L + 150, R - 150))
        self.x = max(L + 60, min(self.x, R - 60))
        self.y = float(B)
        self.vx = self.vy = 0.0
        self.impact = 0.0
        self.speed = 1.8

        self.state = "idle"
        self.pose = "idle"
        self.variant = 0
        self.t = 0
        self.act_left = 0
        self.then = None
        self.blink = 0
        self.next_action = world.tick + random.randint(int(8 * FPS), int(25 * FPS))
        self.next_variant = world.tick + random.randint(int(30 * FPS), int(60 * FPS))
        self.walk_to = None
        self.target = None             # 追的東西（Item）
        self.follow = False
        self.edge = None
        self.peeking = False
        self.last_touch = time.time()
        self.last_love = 0

        self.anger = 0.0
        self.sulking = False
        self.sulk_until = 0
        self.coax = 0
        self.shakes = []
        self.last_dir = 0
        self.dizzy_until = 0
        self.last_complain = 0
        self.spin = 0.0

        self.drag = None
        self.theta = self.omega = 0.0
        self.prev_g = None
        self.prev_v = (0.0, 0.0)
        self.vs = (0.0, 0.0)
        self.grab_frac = (.5, .1)
        self.trail = []
        self.press = None
        self.dragging = False
        self.click_job = None
        self.skip_release = False

        self.bubble = None
        self.bubble_left = 0
        self.parts = []
        self.dirty = True
        self.study_next = 0
        self.giant = False
        self.belly = 0.0                 # 飽足度：0～胃的大小
        self.card_lock = None            # 巨大化時鎖定成某張卡：不做動作，只說話
        self.cling_until = 0
        self.busy_until = 0
        self.queue = []
        self.eager_cd = 0
        self.snatch = None
        self.ate_pending = False
        self.plat = None                 # 站在哪個視窗上（hwnd）
        self.on = None                   # 疊在哪一隻頭上
        self.stack_until = 0
        self.tease_n = 0
        self.last_cur = (0, 0)
        self.hide_kind = None
        self.jealous_until = 0
        self.tag_pause = 0
        self.flying = False
        self.air_spin = 0.0
        self.last_hover = None
        self.strokes = []
        self.click_xy = (0, 0)

        w = self.win
        w.bind("<ButtonPress-1>", self.on_press)
        w.bind("<B1-Motion>", self.on_motion)
        w.bind("<ButtonRelease-1>", self.on_release)
        w.bind("<Double-Button-1>", self.on_double)
        w.bind("<Button-2>", lambda e: self.poke())
        w.bind("<Button-3>", lambda e: self.world.show_menu(self, e))
        w.bind("<Motion>", self.on_hover)
        w.bind("<Escape>", lambda e: self.world.exit_giant())

    # ---------- 基本 ----------
    @property
    def name(self):
        return self.world.disp_name(self.base_id)

    @property
    def accent(self):
        c = (self.char.cfg.get("accent") or self.base.cfg.get("accent", "#e8763a")).lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

    def lines(self, key):
        return (self.char.cfg.get("lines", {}).get(key) or self.base.cfg.get("lines", {}).get(key)
                or GENERIC.get(key) or [])

    def say(self, key=None, text=None, secs=2.8, force=False, **fmt):
        if self.world.settings.get("quiet") and not force:
            return
        if text is None:
            opts = self.lines(key)
            if not opts:
                return
            text = random.choice(opts)
        try:
            text = text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            pass
        self.bubble = text
        self.bubble_left = int(secs * FPS)
        self.dirty = True

    def touch(self):
        self.last_touch = time.time()

    def free(self):
        return self.state in ("idle", "walk") and not self.sulking and not self.follow

    def set_pose(self, pose, variant=None):
        if self.card_lock:
            pose, variant = self.card_lock, 0
        if pose != self.pose:
            self.pose = pose
            self.t = 0
            ch = self.base if (not self.char.has(pose) and self.base.has(pose)) else self.char
            self.variant = random.randrange(len(ch.poses.get(ch.resolve(pose), [0])))
        if variant is not None:
            self.variant = variant
        self.dirty = True

    def act(self, pose, secs, line=None, then=None, force=False):
        if self.card_lock:                        # 卡片模式：只說話
            if line:
                self.say(line, force=force)
            return
        if self.state in ("drag", "air", "leaving"):
            return
        self.state = "act"
        self.target = None
        self.set_pose(pose)
        self.t = 0
        self.act_left = int(secs * FPS)
        self.then = then
        if line:
            self.say(line, force=force)

    def idle(self):
        if self.world.study and not self.giant and self.state not in ("drag", "air", "leaving"):
            self.walk_to = None
            self.target = None
            return self.enter_study()          # 陪讀還在計時 → 回去讀書
        self.state = "idle"
        self.walk_to = None
        self.target = None
        self.set_pose("idle", 0)

    def go_to(self, x, speed=1.8, state="walk"):
        if self.plat and state != "walk":
            self.to_ground()
        self.walk_to = max(self.L + 60, min(self.R - 60, x))
        self.speed = speed
        self.state = state
        self.set_pose("idle", 0)

    def burst(self, kind, n):
        for _ in range(n):
            self.emit(kind)

    # ---------- 生氣 ----------
    def anger_level(self):
        a = self.anger
        return "redhot" if a >= 80 else "puffed" if a >= 50 else "annoyed" if a >= 25 else None

    def show_anger(self):
        lv = self.anger_level()
        if self.sulking:
            self.state = "sulk"
            self.set_pose("sulk")
        elif self.anger >= ANGER_FULL:           # 氣滿了 → 賭氣，不理你
            self.sulking = True
            self.act("redhot", 3, "redhot", then="sulk")
        elif lv:
            self.act(lv, 3.2, lv)
        elif self.world.study:
            self.enter_study()
        else:
            self.idle()

    def forgive(self):
        self.sulking = False
        self.anger = min(self.anger, 20)
        self.burst("heart", 6)
        if self.state in ("sulk", "idle", "walk", "act", "study"):
            self.state = "idle"
            self.act("forgiven", 3, "forgiven", force=True)

    def stomach(self):
        return 220 if self.base_id == "deepseek" else 100

    def is_full(self):
        return self.belly + 25 > self.stomach()

    def calm(self, n):
        """對她好 → 消氣。"""
        if not self.sulking:
            self.anger = max(0.0, self.anger - n)

    def pat(self, by=None):
        self.touch()
        if self.state in ("drag", "air", "leaving"):
            return
        if self.world.study and self.state == "study":
            self.burst("heart", 2)
            self.say("study_poke")
            return
        if self.state == "sleep":
            self.act("surprised", 2, "wake")
            return
        if self.sulking:                         # 賭氣中：不理你
            self.say("sulk_ignore", force=True)
            return
        if self.anger >= 25:
            self.anger = max(0, self.anger - 18)
            if self.anger < 25:
                self.burst("heart", 4)
                self.act("forgiven", 3, "forgiven")
            else:
                self.act("coaxed", 2.5, "coaxed", then=self.show_anger)
            return
        self.burst("heart", 4)
        lv = self.world.love_level(self.base_id)
        line = "love" if lv >= 4 and random.random() < 0.3 else "pat"
        if time.time() < self.jealous_until:
            line, self.jealous_until = "jealous_ok", 0
        self.act("pat", 2.6, line)
        if line == "pat" and random.random() < .12:
            tl = time_line(self)
            if tl:
                self.say(text=tl)
        if by is None:
            self.world.on_pat(self)
            self.world.stat("pat")
        if by is None and time.time() - self.last_love > 4:
            self.last_love = time.time()
            self.world.add_love(self, 1)

    def tease(self, key, amount, pose):
        """惹她生氣。"""
        self.touch()
        if self.state in ("drag", "air", "leaving", "edge", "hide"):
            return
        self.world.stat("poke")
        if self.state == "sleep":
            self.anger = min(100, self.anger + amount / 2)
            return self.act("surprised", 2, "wake")
        self.anger = min(100, self.anger + amount)
        if self.sulking:
            self.say("sulk_ignore", force=True)
            return
        self.act(pose if self.char.has(pose) else "surprised", 2, key, force=True,
                 then=self.show_anger if self.anger_level() else None)

    def poke(self):
        self.touch()
        if self.state in ("drag", "air", "leaving", "edge"):
            return
        self.world.stat("poke")
        if self.state == "sleep":
            self.act("surprised", 2, "wake")
            return
        if self.sulking:
            return self.say("sulk_ignore", force=True)
        self.anger = min(100, self.anger + 20)
        pp = self.char.cfg.get("pokePose") or self.base.cfg.get("pokePose") or "surprised"
        self.act(pp, 1.6, pp if self.lines(pp) else "surprised",
                 then=self.show_anger if self.anger_level() else None)

    # ---------- 每個 tick ----------
    def update(self):
        w = self.world
        self.t += 1
        s = self.state
        if s != "drag":
            self.anger = max(0.0, self.anger - (SULK_DECAY if self.sulking else ANGER_DECAY) / FPS)
        if self.belly:
            self.belly = max(0.0, self.belly - 10 / 60 / FPS)    # 每分鐘消化 10
        if self.sulking and self.anger < SULK_END:      # 不管在做什麼，消到夠低就原諒你
            self.forgive()

        if s == "idle":
            self.update_idle()
        elif s in ("walk", "chase", "race"):
            self.update_walk()
        elif s == "act":
            self.act_left -= 1
            if self.act_left <= 0:
                then, self.then = self.then, None
                if callable(then):
                    then()
                elif then == "sulk":
                    self.state = "sulk"
                    self.set_pose("sulk")
                elif w.study:
                    self.enter_study()
                else:
                    self.idle()
        elif s == "sulk":
            if not self.sulking:
                self.idle()
        elif s == "sleep":
            if self.t % int(25 * FPS) == 0:
                self.say("sleeping")
        elif s == "study":
            if w.tick >= self.study_next:
                self.study_pose()
        elif s == "edge":
            self.update_edge()
        elif s == "drag":
            self.update_drag()
        elif s == "air":
            self.update_air()
        elif s == "stack":
            self.update_stack()
        elif s == "tag":
            self.update_tag()
        if self.plat and self.state not in ("drag", "air", "leaving", "edge", "hide", "stack") and self.t % 2 == 0:
            self.ride_platform()

        kind, every = EMIT.get(self.pose, (None, 0))
        if kind and s != "drag" and self.t % every == 0:
            self.emit(kind)
        if self.parts:
            kk = self.k()
            for p in self.parts:
                p[1] += p[3] * kk
                p[2] += p[4] * kk
                p[5] -= 1
            self.parts = [p for p in self.parts if p[5] > 0]
            if self.t % (4 if self.giant else 2) == 0 or not self.parts:   # 特效每秒 7～15 次就夠了
                self.dirty = True
        if self.bubble_left > 0:
            self.bubble_left -= 1
            if not self.bubble_left:
                self.bubble = None
                self.dirty = True
        m = MOTION.get(self.pose)
        if s in ("walk", "chase", "race", "air", "drag", "tag") or m in FAST_MOTION:
            if not self.giant or self.t % 3 == 0:
                self.dirty = True
        elif m and not self.giant and self.t % 2 == 0:       # 輕微的動作每秒畫 15 次；巨大化時不畫
            self.dirty = True
        if self.blink:
            self.blink -= 1
            if not self.blink:
                self.dirty = True
        if self.dirty:
            self.render()
            self.dirty = False

    def half_step(self):
        """60 fps 的中間格：沿著速度方向挪一半，不重畫。"""
        if self.giant:
            return
        if self.state == "air":
            self.lw.move(self.lw.pos[0] + self.vx / 2, self.lw.pos[1] + (self.vy + GRAVITY / 2) / 2)
        elif self.state == "drag" and self.drag:
            gx, gy = cursor_pos()
            self.lw.move(self.lw.pos[0] + gx - self.drag[0], self.lw.pos[1] + gy - self.drag[1])
            self.drag = (gx, gy)

    def update_idle(self):
        w = self.world
        if self.giant:
            if self.pose == "idle" and self.variant == 0 and self.char.has("idle-blink") and not self.blink \
                    and random.random() < 1 / 110:
                self.blink = 4
                self.dirty = True
            if w.tick >= self.next_action:
                self.next_action = w.tick + random.randint(int(12 * FPS), int(25 * FPS))
                lv = w.love_level(self.base_id)
                acts = [a for a in ("hum", "stretch", "yawn", "pat", "happy", "thinking") if self.char.has(a)]
                acts += [a for a in (self.char.cfg.get("idleActions") or self.base.cfg.get("idleActions") or [])
                         if self.char.has(a)]
                a = random.choice(acts or ["idle"])
                key = "love" if lv >= 3 and random.random() < .35 else ("idle" if random.random() < .5 else a)
                self.act(a, random.uniform(4, 6), key)
                mode = w.settings.get("talk_mode", "daily")
                if mode != "daily" and random.random() < (.8 if mode == "pro" else .4):
                    line = w.topic_line()
                    if line:
                        self.say(text=line, secs=max(4, len(line) / 7))
            return
        if self.follow:
            if abs(cursor_pos()[0] - self.x) > 90:
                self.state = "walk"
                self.set_pose("idle", 0)
            return
        if self.pose == "idle" and self.variant == 0 and self.char.has("idle-blink") and not self.blink \
                and random.random() < 1 / 110:
            self.blink = 4
            self.dirty = True
        if w.tick >= self.next_variant:
            self.next_variant = w.tick + random.randint(int(30 * FPS), int(70 * FPS))
            n = len(self.char.poses.get("idle", [0]))
            self.set_pose("idle", random.randrange(n) if random.random() < 0.4 else 0)
        if time.time() - self.last_touch > SLEEP_AFTER and self.char.has("sleeping") and random.random() < 0.01:
            self.state = "sleep"
            self.set_pose("sleeping")
            self.say("sleeping")
            return
        # 逗貓棒：滑鼠在頭上晃
        if self.t % 3 == 0 and self.tease_check():
            return
        # 跟別隻疊在一起 → 走開一點
        if self.t % 45 == 0:
            for q in w.pets.values():
                if q is not self and q.state in ("idle", "act", "sleep", "study") and abs(q.x - self.x) < 70 \
                        and abs(q.y - self.y) < 20 and q.plat == self.plat:
                    d = 1 if self.x >= q.x else -1
                    if not (self.L + 100 < self.x + d * 130 < self.R - 100):
                        d = -d
                    self.go_to(self.x + d * random.randint(110, 160))
                    return
        # 看到地上有東西
        if w.items and self.t % 30 == 0 and not self.plat:
            it = w.want_item(self)
            if it:
                self.target = it
                fast = it.kind == "food" and self.base_id == "deepseek"
                self.go_to(it.x, 3.2 if fast else 2.4, "chase")
                if random.random() < 0.5:
                    self.say("chase")
                return
        if w.tick < self.next_action:
            return
        self.next_action = w.tick + random.randint(int(20 * FPS), int(55 * FPS))
        late = datetime.datetime.now().hour < 5
        opts = [("walk", 35), ("hum", 14), ("stretch", 9), ("yawn", 18 if late else 6)]
        for a in self.char.cfg.get("idleActions") or self.base.cfg.get("idleActions") or []:
            opts.append((a, 12))
        if self.base_id == "claude":
            opts += [("reading", 6), ("thinking", 4)]
        if w.settings.get("climb", True):
            opts += [("hop_down", 14)] if self.plat else [("climb", 12)]
        if w.settings.get("visit", True) and not self.plat:
            opts += [("visit", 10)]
        opts = [(a, wgt) for a, wgt in opts if a in ("walk", "climb", "hop_down", "visit") or self.char.has(a)]
        a = random.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        if a == "visit":
            mx, my = cursor_pos()
            L, T, R, B = work_area(self.x, self.y - 10)
            if L <= mx <= R and my > T:
                self.go_to(mx + random.choice((-1, 1)) * 40, 2.2)
                self.then = lambda: self.act("bye" if self.char.has("bye") else "happy", 2.2, "visit")
            return
        if a == "climb":
            if not self.climb():
                self.go_to(self.x + random.choice((-1, 1)) * random.randint(80, 320))
        elif a == "hop_down":
            self.jump_to(self.L - 80 if random.random() < .5 else self.R + 80, self.y - 40)
        elif a == "walk" and self.plat and random.random() < .25:
            self.walk_to = self.L - 30 if random.random() < .5 else self.R + 30      # 從視窗邊邊走下去
            self.speed = 1.8
            self.state = "walk"
            self.set_pose("idle", 0)
        elif a == "walk":
            self.go_to(self.x + random.choice((-1, 1)) * random.randint(80, 320))
        else:
            self.act(a, random.uniform(4, 6.5), a if random.random() < 0.6 else None)

    def update_walk(self):
        w = self.world
        if self.state == "chase":
            it = self.target
            if not it or not it.alive:
                self.idle()
                return
            self.walk_to = it.x
            if abs(it.x - self.x) < 40 and it.on_ground():
                w.reach_item(self, it)
                return
        if self.state == "race":
            self.x += self.speed * random.uniform(0.6, 1.4)
            self.dirty = True
            if self.x >= w.race_goal:
                w.race_finish(self)
            return
        tx = cursor_pos()[0] if self.follow else self.walk_to
        if tx is None:
            self.idle()
            return
        d = tx - self.x
        if abs(d) < (60 if self.follow else 3):
            if not self.follow:
                arrived = self.then if callable(self.then) else None
                self.then = None
                self.idle()
                if arrived:
                    arrived()
            return
        self.x += max(-self.speed, min(self.speed, d))
        if self.plat:
            if self.x < self.L - 5 or self.x > self.R + 5:
                self.fall()
                return
        else:
            self.x = max(self.L + 60, min(self.x, self.R - 60))
        self.dirty = True
        if self.state == "walk" and not self.follow and random.random() < 1 / 2500:
            self.act("dizzy" if self.char.has("dizzy") else "oops", 1.8, "trip")

    # 吊著的幾何：支點＝抓的地方，重心＝身體中間偏下
    def hang_geom(self, spr):
        sw, sh = spr.size
        px, py = self.grab_frac[0] * sw, self.grab_frac[1] * sh
        cx, cy = sw / 2, sh * .55
        return px, py, cx, cy

    def rest_angle(self):
        return 0.0

    def update_drag(self):
        """拎後領的鐘擺：抓的點會順順滑到後領；滑鼠的加速度讓她甩起來，用力畫圈會整圈轉。"""
        gx, gy = cursor_pos()
        self.drag = (gx, gy)
        fx, fy = self.grab_frac
        self.grab_frac = (fx + (.5 - fx) * .2, fy + (.15 - fy) * .2)
        if self.prev_g is None:
            self.prev_g = (gx, gy)
        vx, vy = gx - self.prev_g[0], gy - self.prev_g[1]
        svx = self.vs[0] * .5 + vx * .5               # 速度做平滑，免得一抖一抖
        svy = self.vs[1] * .5 + vy * .5
        ax = max(-200, min(200, svx - self.vs[0]))
        ay = max(-200, min(200, svy - self.vs[1]))
        # 小的加速度當作沒有（慢慢拖只是被拎著）；超過門檻的部分才拿來甩
        ax = math.copysign(max(0.0, abs(ax) - DRAG[0]) * DRAG[1], ax)
        ay = math.copysign(max(0.0, abs(ay) - DRAG[2]) * DRAG[3], ay)
        self.prev_g, self.vs = (gx, gy), (svx, svy)
        Lp = max(30.0, self.current_image().size[1] * .4)
        th = self.theta
        alpha = -(ax * math.cos(th) + (DRAG[4] - ay) * math.sin(th)) / Lp     # 重力大一點，甩完很快穩定
        still = ax == 0 and ay == 0
        if still:
            # 手停下來：像彈簧一樣快速來回、越擺越小，很快停在垂直（18° → -13° → 10° → -8° → -3° → 0°）
            th = (self.theta + math.pi) % math.tau - math.pi
            self.theta = th
            self.omega = (self.omega - SETTLE[0] * th) * SETTLE[1]
            self.omega -= math.copysign(min(abs(self.omega), SETTLE[2]), self.omega)     # 一點點摩擦，尾巴收得快
            if abs(th) < .012 and abs(self.omega) < .01:
                self.theta = self.omega = 0.0
        else:
            self.omega = (self.omega + alpha) * .92
        self.omega = max(-DRAG[5], min(DRAG[5], self.omega))
        self.theta += self.omega
        self.spin += self.omega
        if abs(self.spin) > math.tau * 1.5:
            self.spin = 0
            self.anger = min(100, self.anger + 12)
            self.dizzy_until = self.world.tick + int(2 * FPS)
            self.say("spin")
        want = "dizzy" if self.world.tick < self.dizzy_until else "surprised"
        if self.pose != want:
            self.set_pose(want)

    def update_air(self):
        w = self.world
        was_up = self.vy < 0
        prev_y = self.y
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
        it = self.snatch
        if it is not None:
            if not it.alive or not it.held:
                self.snatch = None
            else:
                h = self.current_image().size[1]
                if math.hypot(it.x - self.x, (it.y - 20) - (self.y - h * .8)) < 75:
                    self.snatch = None
                    it.remove()
                    self.ate_pending = True
                    self.burst("heart", 3)
                    self.say("snatch", force=True)
        if self.vy > 0 and self.try_stack(prev_y):
            return
        if self.vy > 0 and not self.plat and w.settings.get("climb", True):
            self.try_platform(prev_y)
        if self.flying and self.vy < 0:
            self.theta += self.air_spin            # 往上飛的時候轉圈圈
            if self.t % 3 == 0:
                self.emit("sparkle")
        else:
            th = (self.theta + math.pi) % math.tau - math.pi
            self.theta = th * 0.85
        if self.flying and was_up and self.vy >= 0:
            self.say("fly_top", force=True, secs=1.6)
        if self.x <= self.L + 40 or self.x >= self.R - 40:
            self.x = max(self.L + 40, min(self.x, self.R - 40))
            self.vx = -self.vx * 0.6
        # 撞到地上的其他隻
        if abs(self.vx) > 5 and self.y > self.floor - w.sprite_h * 0.7:
            for o in w.pets.values():
                if o is not self and o.state not in ("drag", "air", "leaving", "edge", "hide", "stack") \
                        and abs(o.x - self.x) < 55 and abs(o.y - self.y) < w.sprite_h * .7:
                    o.knocked(self.vx)
                    self.vx *= 0.3
                    w.add_love(self, 0)
        if self.y >= self.floor:
            self.y = self.floor
            if self.vy > 7:
                self.impact = max(self.impact, self.vy)
                self.vy = -self.vy * 0.35
                self.vx *= 0.7
            else:
                hard = self.impact > 16 and not self.plat
                flew, self.flying = self.flying, False
                self.impact = 0
                self.vx = self.vy = 0
                self.theta = 0
                self.state = "idle"
                self.snatch = None
                if self.ate_pending:
                    self.ate_pending = False
                    w.feed(self)
                elif not w.landed(self):
                    if flew and not self.anger_level():
                        self.burst("sparkle", 5)
                        self.act("happy", 2.2, "fly_land", force=True)
                    elif hard:
                        self.act("dizzy", 2.6, "land", then=self.show_anger)
                    elif self.anger_level() or self.sulking:
                        self.show_anger()
                    elif w.study:
                        self.enter_study()
                    else:
                        self.idle()

    def update_bounds(self, x, y):
        self.L, _, self.R, self.floor = work_area(x, y)

    def to_ground(self):
        """離開視窗、離開別隻的頭，直接回到工作列上。"""
        self.plat = None
        self.on = None
        self.update_bounds(self.x, self.y - 10)
        self.y = self.floor

    def fall(self, line=True):
        self.plat = None
        self.on = None
        self.update_bounds(self.x, self.y - 10)
        self.state = "air"
        self.vx, self.vy = self.vx * .3, 0.0
        self.flying = False
        self.set_pose("surprised")
        if line and random.random() < .6:
            self.say("fall")

    def jump_to(self, tx, ty):
        """跳到 (tx, ty)：算好初速，讓她剛好在下降時經過那個高度。"""
        rise = max(30.0, self.y - ty + 50)
        vy = -math.sqrt(2 * GRAVITY * rise)
        t_total = -vy / GRAVITY + math.sqrt(2 * 50 / GRAVITY)
        self.vx = max(-12, min(12, (tx - self.x) / t_total))
        self.vy = vy
        self.plat = None
        self.on = None
        self.update_bounds(self.x, self.y - 10)
        self.state = "air"
        self.flying = False
        self.set_pose("happy")

    # ---------- 站在視窗上 ----------
    def climb(self):
        w = self.world
        h = self.current_image().size[1]
        cands = []
        for i, (hwnd, l, t, r, b, stand) in enumerate(w.wins):
            if not stand or not (80 < self.y - t < 650):
                continue
            tx = min(max(self.x, l + 80), r - 80)
            if abs(tx - self.x) < 450 and not w.covered(tx, t, i) and t - h > 0:
                cands.append((tx, t))
        if not cands:
            return False
        tx, t = random.choice(cands)
        self.jump_to(tx, t)
        if random.random() < .5:
            self.say("climb")
        return True

    def try_platform(self, prev_y):
        w = self.world
        for i, (hwnd, l, t, r, b, stand) in enumerate(w.wins):
            if stand and l + 25 < self.x < r - 25 and prev_y <= t <= self.y and not w.covered(self.x, t, i):
                self.plat = hwnd
                self.plat_rect = (l, t, r, b)
                self.L, self.R, self.floor = l, r, t
                self.y = t
                return True
        return False

    def ride_platform(self):
        """站在視窗上：視窗動了跟著動；視窗不見、縮小、放大或她走出邊緣就掉下來。"""
        hwnd = self.plat
        if not window_ok(hwnd):
            return self.fall()
        l, t, r, b = window_rect(hwnd)
        ol, ot = self.plat_rect[:2]
        if (l, t) != (ol, ot):
            dx, dy = l - ol, t - ot
            self.x += dx
            if abs(dx) + abs(dy) > 30 and random.random() < .15:
                self.say("ride")
            self.dirty = True
        self.plat_rect = (l, t, r, b)
        self.L, self.R, self.floor = l, r, t
        self.y = t
        if not (l - 10 < self.x < r + 10) or t < work_area(self.x, t + 5)[1] + 40:
            self.fall()

    # ---------- 疊羅漢 ----------
    def try_stack(self, prev_y):
        w = self.world
        for o in w.pets.values():
            if o is self or o.giant or o.state not in ("idle", "walk", "act", "sleep", "sulk", "study", "stack"):
                continue
            head = o.y - o.current_image().size[1] * .82
            if abs(o.x - self.x) < 55 and prev_y <= head <= self.y:
                self.on = o
                self.plat = None
                self.state = "stack"
                self.vx = self.vy = 0
                self.theta = 0
                self.flying = False
                self.set_pose("happy")
                self.say("stack_top", force=True)
                self.stack_until = w.tick + int(random.uniform(8, 16) * FPS)
                self.lw.raise_()
                if o.state in ("idle", "walk", "act"):
                    o.act("tired" if o.char.has("tired") else "annoyed", 3, "stack_bottom", force=True)
                w.add_love(self, 1)
                return True
        return False

    def update_stack(self):
        o = self.on
        if o is None or o.base_id not in self.world.pets or o.giant \
                or o.state in ("drag", "air", "leaving", "hide", "edge"):
            return self.fall()
        nx, ny = o.x, o.y - o.current_image().size[1] * .82
        if (nx, ny) != (self.x, self.y):
            self.x, self.y = nx, ny
            self.dirty = True
        if self.t % int(6 * FPS) == 0 and random.random() < .3:
            o.say("stack_bottom")
        if self.world.tick >= self.stack_until:
            self.on = None
            self.jump_to(self.x + random.choice((-1, 1)) * 140, o.floor - 20)
            self.set_pose("happy")

    # ---------- 鬼抓人 ----------
    def update_tag(self):
        w = self.world
        g = w.tag
        if not g or self not in g["players"]:
            return self.idle()
        if self.tag_pause > 0:
            self.tag_pause -= 1
            return
        it = g["it"]
        others = [q for q in g["players"] if q is not self and q.base_id in w.pets]
        if not others:
            return
        if self is it:
            tgt = min(others, key=lambda q: abs(q.x - self.x))
            d = 1 if tgt.x > self.x else -1
            self.x += d * 3.4
            if abs(tgt.x - self.x) < 45 and tgt.tag_pause <= 0:
                g["it"] = tgt
                self.say("tag_caught", force=True)
                tgt.say("tag_got", force=True)
                tgt.tag_pause = int(1.2 * FPS)
                tgt.set_pose("surprised")
                self.set_pose("happy")
        else:
            d = -1 if it.x > self.x else 1
            if abs(it.x - self.x) > 420:
                d = getattr(self, "tag_dir", d)
            self.tag_dir = d
            self.x += d * 2.9
            if self.pose != "happy":
                self.set_pose("happy")
        if self.x < self.L + 70 or self.x > self.R - 70:
            self.x = max(self.L + 70, min(self.x, self.R - 70))
            self.tag_dir = -getattr(self, "tag_dir", 1)
        self.dirty = True

    # ---------- 逗貓棒 ----------
    def tease_check(self):
        mx, my = cursor_pos()
        lx, ly = self.last_cur
        self.last_cur = (mx, my)
        h = self.current_image().size[1]
        head = self.y - h
        near = abs(mx - self.x) < 80 and head - 180 < my < head + 20
        if near and abs(mx - lx) + abs(my - ly) > 12:
            self.tease_n += 2 if self.base_id == "gemini" else 1
        else:
            self.tease_n = max(0, self.tease_n - .2)
        if self.tease_n < 5:
            return False
        self.tease_n = 0
        self.touch()
        rise = max(30, min(220, head - my + 40))
        plat = self.plat
        self.jump_to(mx, self.y - rise + 50)
        self.vx = max(-4, min(4, self.vx))
        if plat:
            self.update_bounds(self.x, self.y - 10)
        if random.random() < .45:
            self.say("tease")
        return True

    # ---------- 捉迷藏 ----------
    def hide(self, kind):
        self.to_ground()
        self.follow = False
        self.target = None
        self.bubble = None
        self.state = "hide"
        self.hide_kind = kind
        if kind in ("left", "right"):
            self.edge = kind
            self.set_pose(f"edge_{kind}")
        else:
            self.edge = None
            self.x = random.randint(int(self.L + 120), int(self.R - 120))
            self.set_pose("idle", 0)
        self.dirty = True

    def knocked(self, vx):
        self.touch()
        self.edge = None
        self.target = None
        self.vx = vx * 0.7
        self.vy = -7
        self.theta = 0
        self.anger = min(100, self.anger + 16)
        self.state = "air"
        self.set_pose("surprised")
        self.say("bump", force=True)

    def enter_study(self):
        self.state = "study"
        self.study_pose()

    def study_pose(self):
        opts = [p for p in ("reading", "writing", "thinking") if self.char.has(p)] or ["idle"]
        self.set_pose(random.choice(opts))
        self.study_next = self.world.tick + random.randint(int(60 * FPS), int(100 * FPS))

    # ---------- 貼邊 ----------
    def edge_pose(self, peek):
        p = f"edge_{self.edge}" + ("_peek" if peek else "")
        return p if self.char.has(p) else f"edge_{self.edge}"

    def enter_edge(self, side):
        self.to_ground()
        self.edge = side
        self.state = "edge"
        self.peeking = False
        self.y = self.floor
        self.theta = 0
        self.set_pose(self.edge_pose(False))
        self.world.repack_edges(side)

    def update_edge(self):
        mx, my = cursor_pos()
        edge_x = self.L if self.edge == "left" else self.R
        near = abs(mx - edge_x) < 220 and self.floor - self.world.sprite_h - 120 < my < self.floor + 10
        if near != self.peeking:
            self.peeking = near
            self.set_pose(self.edge_pose(near))
            if near and random.random() < 0.3:
                self.say("edge_peek")

    def leave_edge(self):
        side = self.edge
        self.world.root.after(1, lambda: self.world.repack_edges(side))
        sw = self.current_image().size[0]
        self.x = (self.L + sw / 2 + 20) if self.edge == "left" else (self.R - sw / 2 - 20)
        self.edge = None
        self.state = "idle"
        self.act("happy", 1.5)

    # ---------- 粒子：[種類, x, y, vx, vy, 剩餘, 總長, 大小] ----------
    def emit(self, kind):
        W, H, h = self.dims()
        cx, top = W / 2, H - h
        r = random.uniform
        if kind == "heart":
            p = [kind, cx + r(-h * .25, h * .25), top + h * .15 + r(-10, 20), r(-.5, .5), -1.5, 50, 50, r(8, 12)]
        elif kind == "note":
            p = [kind, cx + random.choice((-1, 1)) * h * r(.25, .4), top + h * .25, r(-.3, .3), -1.0, 60, 60, r(14, 19)]
        elif kind == "z":
            p = [kind, cx + h * .25, top + h * .2, .6, -.8, 70, 70, r(13, 20)]
        elif kind == "steam":
            p = [kind, cx + r(-h * .2, h * .2), top + h * .1, r(-.4, .4), -1.8, 30, 30, r(5, 10)]
        elif kind == "sweat":
            p = [kind, cx + random.choice((-1, 1)) * h * .22, top + h * .15, r(-.6, .6), 1.2, 30, 30, 6]
        elif kind == "bubble":
            p = [kind, cx + r(-h * .3, h * .3), top + h * .4, r(-.3, .3), -1.2, 60, 60, r(4, 8)]
        else:
            p = [kind, cx + r(-h * .35, h * .35), top + r(0, h * .6), 0, -.3, 28, 28, r(6, 11)]
        self.parts.append(p)

    def draw_parts(self, d, ox=0, oy=0):
        kk = self.k()
        for kind, x, y, vx, vy, left, total, s in self.parts:
            x, y, s = x + ox, y + oy, s * kk
            a = int(255 * min(1, left / total * 1.6))
            if kind == "heart":
                col = (255, 105, 135, a)
                r = s / 2
                d.ellipse((x - s, y - r, x, y + r), fill=col)
                d.ellipse((x, y - r, x + s, y + r), fill=col)
                d.polygon([(x - s + 1, y + 2), (x + s - 1, y + 2), (x, y + s * 1.25)], fill=col)
            elif kind == "note":
                d.text((x, y), "♪", font=TEXT.font(1, int(s)), fill=self.accent + (a,), anchor="mm")
            elif kind == "z":
                d.text((x, y), "Z", font=TEXT.font(0, int(s)), fill=(120, 140, 200, a), anchor="mm")
            elif kind == "steam":
                d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, int(a * .7)))
            elif kind == "sweat":
                d.polygon([(x, y - s), (x - s * .6, y + s * .3), (x + s * .6, y + s * .3)], fill=(120, 190, 255, a))
                d.ellipse((x - s * .6, y - s * .1, x + s * .6, y + s * .9), fill=(120, 190, 255, a))
            elif kind == "bubble":
                d.ellipse((x - s, y - s, x + s, y + s), outline=(150, 200, 255, a), width=2)
            else:
                k = s * (.5 + .5 * math.sin(left / 3))
                d.polygon([(x, y - k), (x + k * .3, y - k * .3), (x + k, y), (x + k * .3, y + k * .3),
                           (x, y + k), (x - k * .3, y + k * .3), (x - k, y), (x - k * .3, y - k * .3)],
                          fill=(255, 220, 120, a))

    # ---------- 畫 ----------
    def dims(self):
        """(畫布寬, 畫布高, 角色高)"""
        w = self.world
        if self.giant:
            return w.giant_cw, w.giant_hh, w.giant_h
        return w.win_w, w.win_h, w.sprite_h

    def k(self):
        return self.dims()[2] / 210

    def current_image(self):
        h = self.dims()[2]
        ch = self.char
        if self.card_lock and self.base.has(self.card_lock):
            return self.base.image(self.base.poses[self.card_lock][0], h)
        pose = ch.resolve(self.pose)
        if pose != self.pose and ch is not self.base and self.base.has(self.pose):
            ch, pose = self.base, self.pose          # 換裝沒有這個動作（例如節日裝）→ 暫時用原裝演
        if self.blink and pose == "idle" and self.variant == 0 and ch.has("idle-blink"):
            return ch.image(ch.poses["idle-blink"][0], h)
        files = ch.poses[pose]
        return ch.image(files[self.variant % len(files)], h)

    def motion(self):
        if self.card_lock:
            return 0, 0, 0
        moving = self.state in ("walk", "chase", "race", "tag") and not (self.follow and abs(cursor_pos()[0] - self.x) < 60)
        m = "waddle" if moving else MOTION.get(self.pose)
        t = self.t
        if m == "jump":
            return 0, (-abs(math.sin(t * .2)) * 16 if t < 32 else 0), 0
        if m == "hop":
            return 0, (-abs(math.sin(t * .25)) * 9 if t < 50 else 0), 0
        if m == "sway":
            return 0, 0, 3 * math.sin(t * .13)
        if m == "rock":
            return 0, 0, 5 * math.sin(t * .3)
        if m == "jolt":
            return (5 * math.sin(t * 2.4) * (1 - t / 10) if t < 10 else 0), 0, 0
        if m == "shake":
            return 3 * math.sin(t * 1.7), 0, 0
        if m == "angry":
            return 2.5 * math.sin(t * 3.1), -abs(math.sin(t * 3.1)) * 1.5, 0
        if m == "dizzy":
            return 0, 0, 6 * math.sin(t * .18)
        if m == "slow":
            return 0, 0, 1.5 * math.sin(t * .05)
        if m == "float":
            return 0, -10 - 7 * math.sin(t * .07), 0
        if m == "bob":
            return 0, -2.5 * abs(math.sin(t * .22)), 0
        if m == "breathe":
            return 0, -1.2 * (1 + math.sin(t * .06)), 0
        if m == "waddle":
            k = .45 if self.state in ("race", "tag") else .3
            return 0, -3 * abs(math.sin(t * k)), 4 * math.sin(t * k)
        return 0, 0, 0

    def render(self):
        if self.giant:
            return self.render_giant()
        w = self.world
        spr = self.current_image()
        sw, sh = spr.size
        if self.state == "drag":
            px, py, cx, cy = self.hang_geom(spr)
            reach = max(math.hypot(px - x, py - y) for x in (0, sw) for y in (0, sh))
            S = int(reach * 2 + 40)
            pv = S // 2
            layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            layer.alpha_composite(spr, (int(pv - px), int(pv - py)))
            rot = math.degrees(self.theta)
            img = layer.rotate(rot, resample=Image.BICUBIC, center=(pv, pv)) if abs(rot) > .3 else layer
            gx, gy = self.drag
            d = ImageDraw.Draw(img)
            if self.bubble:
                self.draw_bubble(img, S, max(60, int(pv - reach * .6)))
            self.lw.show(img, gx - pv, gy - pv)
            return
        W, H = w.win_w, w.win_h
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        foot = H - 4
        if self.state == "hide":
            if self.hide_kind == "bottom":           # 從工作列探出頭頂
                spr = spr.crop((0, 0, sw, int(sh * .27)))
                img.alpha_composite(spr, (W // 2 - sw // 2, foot - spr.height))
                wx = self.x - W // 2
            else:
                img.alpha_composite(spr, (W // 2 - sw // 2, foot - sh))
                hide = int(sw * .55)
                wx = (self.L - (W // 2 - sw // 2) - hide) if self.hide_kind == "left" \
                    else (self.R - (W // 2 + sw - sw // 2) + hide)
            self.lw.show(img, wx, self.y - foot)
            return
        dx, dy, ang = self.motion()
        if self.state == "air" and abs(self.theta) > .02:
            ang = math.degrees(self.theta)
        top = int(foot - sh + dy)
        if ang:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            layer.alpha_composite(spr, (int(W // 2 - sw // 2 + dx), top))
            pivot = (W // 2, foot - sh // 2) if self.state == "air" else (W // 2, foot)
            img.alpha_composite(layer.rotate(ang, resample=Image.BICUBIC, center=pivot))
        else:
            img.alpha_composite(spr, (int(W // 2 - sw // 2 + dx), top))
        if self.state == "edge":
            wx = self.L - (W // 2 - sw // 2) if self.edge == "left" else self.R - (W // 2 + sw - sw // 2)
        else:
            wx = self.x - W // 2
        wy = self.y - foot
        d = ImageDraw.Draw(img)
        if self.parts:
            self.draw_parts(d)
        if self.bubble:
            self.draw_bubble(img, W, max(0, top))
        self.lw.show(img, wx, wy)

    def render_giant(self):
        w = self.world
        W, H, h = self.dims()
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        spr = self.current_image()
        sw, sh = spr.size
        dx, dy, ang = self.motion()
        kk = self.k()
        top = int(H - sh + dy * kk)
        img.alpha_composite(spr, (int(W // 2 - sw // 2 + dx * kk), top))
        self.sprite_box = (W // 2 - sw // 2, top, sw, sh)
        d = ImageDraw.Draw(img)
        if self.parts:
            self.draw_parts(d)
        if self.bubble:
            self.draw_bubble(img, W, max(0, top + int(sh * .05)))
        self.lw.show(img, w.giant_cx, w.giant_y)

    def close_btn(self):
        return -999, -999, 0

    def zone(self, x, y):
        """巨大化時，滑鼠在角色的哪個部位：head / cheek / body / None"""
        bx, by, bw, bh = getattr(self, "sprite_box", (0, 0, 1, 1))
        if not (bx <= x <= bx + bw and by <= y <= by + bh):
            return None
        r = (y - by) / bh
        return "head" if r < .2 else "cheek" if r < .33 else "body"

    def giant_touch(self, zone):
        self.touch()
        w = self.world
        if self.state == "sleep":
            self.act("surprised", 2, "wake")
        elif zone == "head":
            self.pat()
        elif zone == "cheek":
            self.act("puffed" if self.char.has("puffed") else "pout", 2)
            self.say(text=random.choice(["不、不要戳臉啦……", "（鼓臉）", "臉會被戳扁的！", "唔……"]))
        elif zone == "body":
            self.burst("heart", 6)
            self.act("pat" if self.char.has("pat") else "happy", 2.6, "hug")
            if time.time() - self.last_love > 4:
                self.last_love = time.time()
                w.add_love(self, 1)

    def on_hover(self, e):
        """巨大化時、或撒嬌把滑鼠拉過來之後，滑鼠在頭上來回晃＝一直摸。"""
        if self.press or not (self.giant or time.time() < self.cling_until):
            return
        if self.giant:
            on_head = self.zone(e.x, e.y) == "head"
        else:
            sw, sh = self.current_image().size
            W, H = self.world.win_w, self.world.win_h
            on_head = abs(e.x - W / 2) < sw * .4 and H - 4 - sh <= e.y <= H - 4 - sh * .65
        if not on_head:
            self.last_hover = None
            return
        now = self.world.tick
        if self.last_hover is not None:
            lx, ldir = self.last_hover
            dr = 1 if e.x > lx + 3 else -1 if e.x < lx - 3 else ldir
            if dr != ldir and ldir:
                self.strokes = [t for t in self.strokes if now - t < 40] + [now]
                self.burst("heart", 1)
            self.last_hover = (e.x, dr)
        else:
            self.last_hover = (e.x, 0)
        if len(self.strokes) >= 6:
            self.strokes = []
            if self.state == "act" and self.pose == "pat":
                self.act_left = int(2.6 * FPS)
            else:
                self.pat()

    def draw_bubble(self, img, W, top):
        kk = min(2.2, max(1.0, self.k() * .45)) if self.giant else self.world.text_scale
        edge = self.edge if self.state == "edge" else None
        key = (self.bubble, W, kk, self.accent, edge)
        cache = getattr(self, "_bub", None)
        if not cache or cache[0] != key:
            cache = self._bub = (key,) + self.make_bubble(W, kk, edge)
        _, bub, bx, bh = cache
        img.alpha_composite(bub, (int(bx), int(max(2, top - bh - 12))))

    def make_bubble(self, W, kk, edge):
        """排好一個泡泡的圖：回傳 (圖, 左邊 x, 泡泡本體高度)。"""
        size = int(15 * kk)
        maxw = min(W - 20, int(240 * kk))
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        lines = []
        for para in self.bubble.split("\n"):
            cur = ""
            for ch in para:
                if TEXT.width(d, cur + ch, size) > maxw - 22:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
        lh = int(21 * kk)
        tw = max(TEXT.width(d, l, size) for l in lines)
        bw, bh = tw + 22 * kk, lh * len(lines) + 12 * kk
        bx = (W - bw) / 2
        if edge:                                   # 貼左邊 → 泡泡在右邊；貼右邊 → 在左邊（朝螢幕中間）
            bx = W - bw - 4 if edge == "left" else 4
        bx = max(2, min(bx, W - bw - 2))
        bub = Image.new("RGBA", (int(bw) + 3, int(bh) + 12), (0, 0, 0, 0))
        d = ImageDraw.Draw(bub)
        col = self.accent
        d.rounded_rectangle((1, 1, bw, bh), radius=10, fill=(255, 253, 248, 245), outline=col + (255,), width=2)
        tx = min(max(W / 2, bx + 14), bx + bw - 14) - bx
        d.polygon([(tx - 7, bh - 1), (tx + 7, bh - 1), (tx, bh + 9)], fill=(255, 253, 248, 245))
        d.line([(tx - 7, bh), (tx, bh + 9), (tx + 7, bh)], fill=col + (255,), width=2)
        for i, l in enumerate(lines):
            TEXT.draw(d, (11 * kk, 6 * kk + i * lh + lh / 2), l, size, (58, 42, 37, 255), anchor="lm")
        return bub, bx, bh

    # ---------- 滑鼠 ----------
    def on_press(self, e):
        self.press = (e.x_root, e.y_root)
        self.dragging = False

    def on_motion(self, e):
        if self.giant:
            self.on_hover(e)
            return
        if not self.press:
            self.on_hover(e)
            return
        if not self.press or self.state in ("leaving", "race"):
            return
        if not self.dragging:
            if abs(e.x_root - self.press[0]) + abs(e.y_root - self.press[1]) < 7:
                return
            self.dragging = True
            self.touch()
            if self.state == "air" and self.flying:    # 在空中被接住
                self.flying = False
                self.burst("heart", 4)
                self.say("catch", force=True)
                self.world.add_love(self, 1)
                self.world.root.after(10, lambda: self.say("catch", force=True))
            if self.click_job:
                self.world.root.after_cancel(self.click_job)
                self.click_job = None
            # 抓的位置（佔角色寬高的比例），之後就以這一點當支點吊著她
            spr = self.current_image()
            sw, sh = spr.size
            left = (self.L if self.edge == "left" else self.R - sw) if self.state == "edge" else self.x - sw / 2
            top = self.y - sh
            self.grab_frac = (min(.95, max(.05, (self.press[0] - left) / sw)),
                              min(.95, max(.03, (self.press[1] - top) / sh)))
            if self.state == "hide":
                self.world.found(self, quiet=True)
            if self.on is None:
                for q in self.world.pets.values():
                    if q.on is self:                 # 下面那隻被拎走 → 上面的掉下來
                        q.world.root.after(1, q.fall)
            self.edge = None
            self.plat = None
            self.on = None
            self.target = None
            self.then = None
            self.state = "drag"
            self.set_pose("surprised")
            self.theta = self.rest_angle()
            self.omega = self.spin = 0.0
            self.prev_g = None
            self.prev_v = (0.0, 0.0)
            self.vs = (0.0, 0.0)
            self.trail = []
            self.shakes = []
            self.last_dir = 0
            self.set_pose("surprised")
            self.say("drag")
        if self.trail:
            dx = e.x_root - self.trail[-1][0]
            if abs(dx) > 12:
                dr = 1 if dx > 0 else -1
                if self.last_dir and dr != self.last_dir:
                    now = self.world.tick
                    self.shakes = [s for s in self.shakes if now - s < 1.2 * FPS] + [now]
                    if len(self.shakes) >= 2:
                        self.anger = min(100, self.anger + 9)
                        self.dizzy_until = now + int(1.2 * FPS)
                        if now - self.last_complain > 1.6 * FPS:
                            self.last_complain = now
                            self.say(self.anger_level() or "dizzy")
                self.last_dir = dr
        self.drag = (e.x_root, e.y_root)
        self.trail.append((e.x_root, e.y_root, e.time))
        self.trail = self.trail[-6:]

    def on_release(self, e):
        self.press = None
        if self.giant:
            cx, cy, r = self.close_btn()
            if (e.x - cx) ** 2 + (e.y - cy) ** 2 <= (r + 6) ** 2:
                self.world.exit_giant()
                return
        if self.dragging:
            self.dragging = False
            self.release_drag(e)
            return
        if self.skip_release:
            self.skip_release = False
            return
        if e.state & 0x0004:
            self.poke()
            return
        if self.click_job:
            self.world.root.after_cancel(self.click_job)
        self.click_xy = (e.x, e.y)
        self.click_job = self.world.root.after(230, self.single_click)

    def single_click(self):
        self.click_job = None
        if self.state == "hide":
            self.world.found(self)
            return
        if self.giant:
            z = self.zone(*self.click_xy)
            if z:
                self.giant_touch(z)
            return
        if self.state == "edge":
            self.say("edge_peek")
            return
        self.pat()

    def on_double(self, e):
        if self.click_job:
            self.world.root.after_cancel(self.click_job)
            self.click_job = None
        self.skip_release = True
        self.touch()
        if self.giant:
            self.act("happy", 1.4)
            return
        if self.state == "edge":
            self.leave_edge()
        elif self.state in ("idle", "walk", "act", "study"):
            self.act("happy", 1.4)

    def release_drag(self, e):
        sh = self.current_image().size[1]
        if e.x_root <= self.L + 30 and self.char.has("edge_left"):
            self.enter_edge("left")
            return
        if e.x_root >= self.R - 30 and self.char.has("edge_right"):
            self.enter_edge("right")
            return
        # 放手時腳底在哪：把「腳底相對支點」的向量照目前的旋轉角度轉過去
        spr = self.current_image()
        sw = spr.size[0]
        px, py, cx, cy = self.hang_geom(spr)
        phi = self.theta
        bx, by = sw / 2 - px, sh - py
        gx, gy = self.drag or (e.x_root, e.y_root)
        self.x = float(gx + bx * math.cos(phi) + by * math.sin(phi))
        self.y = float(min(self.floor, gy - bx * math.sin(phi) + by * math.cos(phi)))
        self.theta = phi                      # 空中再慢慢轉正
        self.update_bounds(gx, gy)
        self.vx = max(-20, min(20, self.vs[0] * 1.2))
        self.vy = max(-36, min(20, self.vs[1] * 1.4 if self.vs[1] < 0 else self.vs[1] * 1.2))
        self.state = "air"
        self.flying = self.vy < -15 and not self.sulking and self.anger < 45
        if self.flying:                        # 往上甩 → 飛高高
            self.world.stat("fly")
            self.air_spin = random.choice((-1, 1)) * random.uniform(.12, .22)
            self.set_pose("happy")
            self.say("fly", force=True, secs=2)
            self.world.add_love(self, 1)
            self.dirty = True
            return
        self.set_pose("dizzy" if self.world.tick < self.dizzy_until else "surprised")
        self.dirty = True


# ---------------------------------------------------------------- 世界
class World:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        try:
            import tkinter.font as tkfont
            for name in ("TkDefaultFont", "TkMenuFont", "TkTextFont", "TkHeadingFont", "TkCaptionFont",
                         "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
                tkfont.nametofont(name).configure(family="Microsoft JhengHei")
            self.root.option_add("*Font", ("Microsoft JhengHei", 10))
        except Exception:
            pass
        self.root.report_callback_exception = lambda *a: log_error(*a)
        self.settings = self.load_settings()
        self.sprite_h = SIZES.get(self.settings.get("size"), 210)
        self.set_size_dims()
        self.chars = {}
        for d in sorted(CHAR_DIR.iterdir()) if CHAR_DIR.exists() else []:
            if d.is_dir() and (any(d.glob("idle*.webp")) or any(d.glob("idle*.png"))):
                self.chars[d.name] = Character(d)
        self.dialogs = []
        dj = CHAR_DIR / "dialogs.json"
        if dj.exists():
            try:
                self.dialogs = json.loads(dj.read_text(encoding="utf-8"))
            except Exception:
                log_error()
        self.pets = {}
        self.items = []
        self.tick = 0
        self.study = None
        self.break_until = None
        self.dialog_busy = False
        self.next_dialog = int(40 * FPS)
        self.last_hour = datetime.datetime.now().hour
        self.last_late = None
        self.feeds = []
        self.reminders = []
        self.away = False
        self.race_goal = None
        self.race_rank = []
        self.comforting = False
        self.frame = 0
        self.cling_job = None
        self.cling_next = time.time() + 60
        self.next_topic = int(20 * FPS)
        self.next_time_chat = int(random.uniform(3, 8) * 60 * FPS)
        self.cling_cur = (0, 0)
        self.cling_still = time.time()
        self.wins = []
        self.pat_log = []
        self.jealous_cool = 0
        self.tag = None
        self.hs = None
        self.app_seen = (None, 0)
        self.app_said = {}
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)      # 讓計時器準到 1ms，60 fps 才穩
        except Exception:
            pass
        self.hide_reasons = set()
        self.key_down = False
        self.home = None
        self.events = __import__("queue").Queue()
        self.tray = None
        self.giant = None
        self.giant_dim = False
        self.giant_rest_end = None
        self.giant_x = self.giant_y = 0
        self.giant_w = self.giant_hh = self.giant_h = 1
        self.panel = None

        out = [c for c in self.settings.get("out", ["claude", "deepseek"]) if c in self.chars]
        if not out:
            out = [c for c in ("claude", "deepseek") if c in self.chars][:1] or list(self.chars)[:1]
        for i, c in enumerate(out):
            self.root.after(400 * i, lambda c=c: self.spawn(c))

    # ---------- 設定 ----------
    def load_settings(self):
        try:
            s = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            s = {}
        base = {"size": "中", "quiet": False, "hourly": True, "late": True, "meal": True, "climb": True,
                "watch_app": True, "visit": True, "cling": False, "cards": {}, "foods": list(FOODS),
                "stats": {}, "todos": [], "birthday": "", "first_day": datetime.date.today().isoformat(),
                "checkin": {"last": "", "streak": 0, "total": 0}, "gifts": {}, "celebrated": [],
                "talk_mode": "daily", "talk_freq": "偶爾", "topic_on": ["數位 IC"], "topics": None,
                "giant_bg": 0, "giant_rest_bg": 60,
                "out": ["claude", "deepseek"], "outfits": {}, "pos": {}, "love": {}, "meals_done": ""}
        base.update(s)
        return base

    def save(self):
        s = self.settings
        s["out"] = list(self.pets)
        s["pos"].update({k: int(p.x) for k, p in self.pets.items()})
        s["outfits"].update({k: p.char.id for k, p in self.pets.items()})
        try:
            SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            log_error()

    def set_size_dims(self):
        h = self.sprite_h
        self.text_scale = BUBBLE_SCALE.get(self.settings.get("size", "中"), 1.0)
        self.win_w = max(280, int(h * 1.35), int(270 * self.text_scale))
        self.win_h = h + int(130 * max(1.0, self.text_scale))

    # ---------- 好感度 ----------
    def love_level(self, cid):
        v = self.settings["love"].get(cid, 0)
        return sum(1 for t in LOVE_LEVELS if v >= t)

    def add_love(self, p, n):
        if n <= 0:
            return
        before = self.love_level(p.base_id)
        self.settings["love"][p.base_id] = self.settings["love"].get(p.base_id, 0) + n
        after = self.love_level(p.base_id)
        if after > before:
            self.root.after(2700, lambda: self.level_up(p, after))

    def level_up(self, p, lv):
        if p.base_id not in self.pets or p.state in ("drag", "air"):
            return
        p.burst("heart", 10)
        p.burst("sparkle", 6)
        p.act("happy", 3)
        p.say(text=f"好感度 Lv{lv}！\n" + random.choice(p.lines("levelup")), force=True, secs=4)
        self.save()

    def repack_edges(self, side):
        """貼在同一邊的往上排，不會疊在一起。"""
        ps = [q for q in self.pets.values() if q.state == "edge" and q.edge == side]
        ps.sort(key=lambda q: -q.y)
        for i, q in enumerate(ps):
            q.y = q.floor - i * int(self.sprite_h * .62)
            q.dirty = True

    def disp_name(self, cid):
        return self.settings.get("names", {}).get(cid) or self.chars[cid].cfg.get("name", cid)

    def love_title(self, cid):
        return LOVE_TITLES[min(self.love_level(cid), len(LOVE_TITLES) - 1)]

    def love_progress(self, cid):
        """(目前分數, 這一級起點, 下一級門檻或 None)"""
        v = self.settings["love"].get(cid, 0)
        lv = self.love_level(cid)
        lo = LOVE_LEVELS[lv - 1] if lv >= 1 else 0
        hi = LOVE_LEVELS[lv] if lv < len(LOVE_LEVELS) else None
        return v, lo, hi

    def next_unlock(self, cid):
        lv = self.love_level(cid)
        for k in sorted(LOVE_UNLOCKS):
            if k > lv:
                return f"Lv{k} 解鎖：{LOVE_UNLOCKS[k]}"
        return "全部解鎖了！"

    # ---------- 統計 ----------
    def stat(self, key, n=1):
        today = datetime.date.today().isoformat()
        st = self.settings.setdefault("stats", {})
        st.setdefault(today, {})
        st[today][key] = st[today].get(key, 0) + n
        if len(st) > 400:
            for k in sorted(st)[:-400]:
                del st[k]

    def stat_sum(self, days=None):
        st = self.settings.get("stats", {})
        keys = sorted(st)
        if days is not None:
            since = (datetime.date.today() - datetime.timedelta(days=days - 1)).isoformat()
            keys = [k for k in keys if k >= since]
        out = {}
        for k in keys:
            for a, b in st[k].items():
                out[a] = out.get(a, 0) + b
        return out

    # ---------- 簽到、禮物、生日、紀念日 ----------
    def daily(self):
        """每天第一次：簽到、生日、紀念日。程式開著跨日也會觸發。"""
        today = datetime.date.today()
        ci = self.settings.setdefault("checkin", {"last": "", "streak": 0, "total": 0})
        if ci.get("last") == today.isoformat() or not self.pets:
            return
        yesterday = (today - datetime.timedelta(days=1)).isoformat()
        ci["streak"] = ci.get("streak", 0) + 1 if ci.get("last") == yesterday else 1
        ci["total"] = ci.get("total", 0) + 1
        ci["last"] = today.isoformat()
        p = self.pick_pet()
        for q in self.pets.values():
            self.add_love(q, 3)
        msg = f"簽到第 {ci['total']} 天！（連續 {ci['streak']} 天）"
        special = ci["streak"] in (7, 30, 100, 365)
        if special:
            msg += f"\n連續 {ci['streak']} 天！謝謝你一直來看我們～"
        self.root.after(4500, lambda: (p.burst("sparkle", 10 if special else 5), p.act("happy", 3.5, None),
                                       p.say(text=random.choice(p.lines("checkin")) + "\n" + msg, force=True, secs=5)))
        self.save()
        self.root.after(10000, self.celebrations)

    def celebrations(self):
        today = datetime.date.today()
        done = self.settings.setdefault("celebrated", [])
        bd = self.settings.get("birthday", "")
        tag = f"bd-{today.year}"
        if bd and today.strftime("%m-%d") == bd and tag not in done:
            done.append(tag)
            self.party()
            for p in self.pets.values():
                p.say("birthday", force=True, secs=5)
            self.drop_item_at("蛋糕", *cursor_pos())
            self.save()
            return
        try:
            first = datetime.date.fromisoformat(self.settings.get("first_day"))
        except (TypeError, ValueError):
            return
        days = (today - first).days
        years = today.year - first.year
        tag = f"day-{days}"
        msg = None
        if days > 0 and days % 100 == 0:
            msg = f"今天是我們認識的第 {days} 天！"
        elif years >= 1 and (today.month, today.day) == (first.month, first.day):
            msg = f"認識滿 {years} 年了！謝謝你～"
        if msg and tag not in done:
            done.append(tag)
            for p in self.pets.values():
                p.burst("heart", 8)
                p.burst("sparkle", 6)
                p.act("happy", 4)
            self.pick_pet().say(text=msg, force=True, secs=6)
            self.save()

    def daily_gift(self):
        today = datetime.date.today().isoformat()
        gifts = self.settings.setdefault("gifts", {})
        for p in self.pets.values():
            if self.love_level(p.base_id) >= 5 and gifts.get(p.base_id) != today and p.free() and not p.plat \
                    and random.random() < .02:
                gifts[p.base_id] = today
                name = random.choice([n for n, (e, k) in ITEMS.items() if k == "food"])
                sw, sh = p.current_image().size
                self.drop_item_at(name, p.x + random.choice((-1, 1)) * 70, p.y - sh)
                p.act("happy", 3, "gift", force=True)
                self.save()
                return

    def drop_item_at(self, name, x, y):
        it = Item(self, name, x, y)
        self.items.append(it)
        return it

    # ---------- 待辦 ----------
    def check_todos(self):
        now = datetime.datetime.now()
        hm = now.strftime("%H:%M")
        today = now.date().isoformat()
        for td in self.settings.get("todos", []):
            if td.get("done") or not td.get("time") or td.get("notified") == today:
                continue
            due = now.replace(hour=int(td["time"][:2]), minute=int(td["time"][3:]), second=0, microsecond=0)
            left = (due - now).total_seconds() / 60
            if 0 < left <= 10 and td.get("warned") != today:        # 剩 10 分鐘先提醒一次
                td["warned"] = today
                p = self.pick_pet()
                if p:
                    p.touch()
                    p.act("surprised", 3)
                    p.say("todo_soon", force=True, secs=6, t=td["text"], m=max(1, round(left)))
                self.save()
                continue
            if hm >= td["time"]:
                td["notified"] = now.date().isoformat()
                p = self.pick_pet()
                if p:
                    p.touch()
                    p.burst("sparkle", 5)
                    p.act("happy", 4)
                    p.say("todo_remind", force=True, secs=7, t=td["text"])
                self.save()

    def todo_done(self, td):
        td["done"] = True
        p = self.pick_pet()
        if p:
            p.burst("heart", 6)
            p.act("happy", 3, "todo_done", force=True)
            self.add_love(p, 1)
        self.save()

    def love_text(self, cid):
        v = self.settings["love"].get(cid, 0)
        lv = self.love_level(cid)
        nxt = LOVE_LEVELS[lv] if lv < len(LOVE_LEVELS) else None
        return f"好感度 Lv{lv}" + (f"（{v}/{nxt}）" if nxt else "（MAX）")

    # ---------- 叫出來 / 回家 ----------
    def base_ids(self):
        ids = [c for c in self.chars if "skinOf" not in self.chars[c].cfg]
        return sorted(ids, key=lambda c: SHOW_ORDER.index(c) if c in SHOW_ORDER else 99)

    def skins_of(self, base):
        return [c for c, ch in self.chars.items() if ch.base == base]

    def spawn(self, cid, greet=True):
        if cid in self.pets or cid not in self.chars:
            return
        outfit = self.settings["outfits"].get(cid, cid)
        x = self.settings["pos"].get(cid)
        if x is None and self.pets:
            ref = random.choice(list(self.pets.values())).x
            x = ref + random.choice((-1, 1)) * random.randint(150, 260)
        p = Pet(self, cid, outfit, x)
        self.pets[cid] = p
        if greet:
            self.greet(p)
        self.save()

    def greet(self, p):
        fest = festival_today()
        key = fest if fest and (p.char.has(fest) or p.lines(fest)) else "greet_" + period_now()
        if not (p.char.has(key) or p.lines(key)):
            key = "greeting"
        p.act(key if p.char.has(key) else "happy", 3.5, key if p.lines(key) else "greeting")

    def dismiss(self, p):
        if p.state == "leaving":
            return
        if p is self.giant:
            self.exit_giant()
        p.set_pose("bye")
        p.say("bye", force=True)
        p.state = "leaving"
        p.render()
        self.pets.pop(p.base_id, None)
        self.save()
        self.root.after(1800, p.win.destroy)
        if not self.pets:
            self.root.after(1900, self.quit)

    def quit(self):
        self.mis_end()
        self.save()
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()

    def change_outfit(self, p, outfit):
        p.char = self.chars[outfit]
        p.set_pose("idle", 0)
        self.settings["outfits"][p.base_id] = outfit
        self.save()
        p.act("happy", 2.5)
        g = p.char.cfg.get("greeting")
        if g:
            p.say(text=g)

    # ---------- 互動 ----------
    def landed(self, p):
        """被慢慢放到別隻身上 → 抱抱。回傳 True 表示已經處理。"""
        for o in self.pets.values():
            if o is not p and o.state not in ("drag", "air", "leaving", "edge", "hide", "stack") \
                    and abs(o.x - p.x) < 110 and abs(o.y - p.y) < 20:
                self.stat("hug")
                for a in (p, o):
                    a.touch()
                    a.burst("heart", 6)
                    a.act("pat", 3, "hug")
                self.add_love(p, 2)
                self.add_love(o, 2)
                return True
        return False

    def feed(self, p, food="飯糰"):
        p.touch()
        if p.is_full():                              # 吃太飽了
            p.state = "idle" if p.state not in ("drag", "air", "leaving") else p.state
            p.act("tired" if p.char.has("tired") else "oops", 2.2, "full", force=True)
            return False
        p.belly += 25
        self.stat("feed")
        if p.sulking:                                # 賭氣中：吃東西是唯一能明顯消氣的方法
            p.anger = max(0.0, p.anger - 35)
            if p.anger < SULK_END:
                p.forgive()
                p.say("food_forgive", force=True)
                self.add_love(p, 2)
            else:
                p.state = "idle"
                p.act("coaxed" if p.char.has("coaxed") else "eat", 2.4, "sulk_food", then="sulk", force=True)
            return
        if p.anger >= 25:
            p.anger = max(0.0, p.anger - 40)
            if p.anger < 25:
                p.burst("heart", 5)
                p.act("forgiven", 3, "food_forgive", force=True)
                self.add_love(p, 2)
                return
        now = self.tick
        self.feeds = [(t, c) for t, c in self.feeds if now - t < 20 * FPS] + [(now, p.base_id)]
        many = sum(1 for _, c in self.feeds if c == p.base_id) >= 3
        if many and p.char.has("feast"):
            p.burst("sparkle", 6)
            p.act("feast", 4.5, "feast")
        else:
            p.act("eat" if p.char.has("eat") else "happy", 4, "feed")
        self.add_love(p, 2)
        fish = self.pets.get("deepseek")
        if fish and fish is not p and fish.free() and random.random() < 0.6:
            fish.go_to(p.x + (110 if fish.x > p.x else -110), 2.6)
            fish.then = lambda: fish.act("pout" if fish.char.has("pout") else "surprised", 2.5, "share")

    # 直接把東西拿給她
    def pet_at(self, x, y, pad=0):
        for p in self.pets.values():
            if p.giant or p.state in ("drag", "leaving", "hide", "edge"):
                continue
            sw, sh = p.current_image().size
            if abs(x - p.x) < sw * .45 + pad and p.y - sh - pad <= y <= p.y + 5:
                return p
        return None

    def item_hover(self, it, x, y):
        now = time.time()
        p = self.pet_at(x, y, pad=60)
        if p and now > p.eager_cd and p.state in ("idle", "walk", "act", "sleep"):
            p.eager_cd = now + 4
            if p.state == "sleep" and it.kind == "food":
                p.touch()
                p.act("surprised", 1.5, "food_wake", force=True)
            elif p.state != "sleep":
                p.touch()
                p.act("happy" if it.kind == "food" else "surprised", 1.4,
                      "want_food" if it.kind == "food" else "want_toy")
        # 食物拿在頭上晃 → 跳起來搶
        if it.kind != "food":
            return
        for q in self.pets.values():
            if q.giant or q.state not in ("idle", "walk", "act") or q.snatch or q.sulking or q.is_full():
                continue
            sh = q.current_image().size[1]
            head = q.y - sh
            if abs(x - q.x) < 90 and head - 200 < y < head - 10 and now > q.eager_cd - 2:
                if random.random() < (.5 if q.base_id == "deepseek" else .18):
                    q.eager_cd = now + 4
                    q.snatch = it
                    q.jump_to(x, y + sh + 20)
                    q.vx = max(-4, min(4, q.vx))

    def item_drop(self, it, x, y):
        p = self.pet_at(x, y, pad=10)
        if not p:
            return False
        self.give(p, it)
        return True

    def give(self, p, it):
        p.touch()
        if it.kind == "food":
            if p.is_full() and not p.sulking:
                p.act("tired" if p.char.has("tired") else "oops", 2, "full", force=True)
                it.held = None
                return
            it.remove()
            if p.state == "air":
                p.ate_pending = True
            elif p.sulking or p.anger >= 25:
                self.feed(p)
            else:
                if p.state in ("sleep", "study", "sulk", "stack", "tag"):
                    p.state = "idle"
                self.feed(p)
            return
        # 玩具：接住、踢出去
        sw, sh = p.current_image().size
        it.held = None
        it.x, it.y = p.x, p.y - sh * .45
        it.vx = random.choice((-1, 1)) * random.uniform(7, 11)
        it.vy = -random.uniform(8, 12)
        if p.base_id == "gemini" and it.name == "毛線球":
            p.burst("heart", 5)
            p.act("happy", 2.5, "yarn", force=True)
        else:
            p.act("happy", 1.6, "kick")
        self.add_love(p, 1)

    # 地上的東西
    def drop_item(self, name):
        mx, my = cursor_pos()
        it = Item(self, name, mx, my)
        self.items.append(it)

    def want_item(self, p):
        cands = [it for it in self.items if it.alive and not it.held and it.on_ground()]
        if not cands:
            return None
        it = min(cands, key=lambda i: abs(i.x - p.x))
        if it.kind == "food":
            if p.is_full():
                return None
            chance = 1.0 if p.base_id == "deepseek" else 0.6
        else:
            chance = 0.35
        return it if random.random() < chance else None

    def reach_item(self, p, it):
        if it.kind == "food":
            if p.is_full():
                p.act("tired" if p.char.has("tired") else "oops", 2, "full")
                return
            others = [o for o in self.pets.values() if o is not p and o.target is it]
            it.remove()
            p.belly += 25
            p.burst("heart", 3)
            p.act("eat" if p.char.has("eat") else "happy", 3.5, "feed")
            self.add_love(p, 1)
            for o in others:
                o.act("pout" if o.char.has("pout") else "surprised", 2, "eat_lose")
        else:
            dr = 1 if it.x >= p.x else -1
            it.vx = dr * random.uniform(6, 11)
            it.vy = -random.uniform(5, 9)
            p.act("happy", 1.2, "kick" if random.random() < 0.5 else None)
            p.next_action = self.tick + int(2 * FPS)

    def gather(self):
        mx = cursor_pos()[0]
        ps = list(self.pets.values())
        for i, p in enumerate(ps):
            if p.state in ("drag", "air", "leaving"):
                continue
            p.edge = None
            p.to_ground()
            p.go_to(mx + (i - (len(ps) - 1) / 2) * 140, 2.4)
            p.say("gather")

    def line_up(self):
        ps = list(self.pets.values())
        L, T, R, B = work_area()
        for i, p in enumerate(ps):
            p.edge = None
            p.to_ground()
            p.go_to(R - 120 - (len(ps) - 1 - i) * 150, 2.4)

    def all_sleep(self):
        for p in self.pets.values():
            if p.state in ("idle", "walk", "act") and p.char.has("sleeping"):
                p.state = "sleep"
                p.set_pose("sleeping")

    def all_wake(self):
        for p in self.pets.values():
            if p.state == "sleep":
                p.touch()
                p.act("surprised", 2, "wake")

    def party(self):
        ps = [p for p in self.pets.values() if p.state not in ("drag", "air", "leaving")]
        for i, p in enumerate(ps):
            p.touch()
            seq = ["hum", "happy", "hum", "happy", "hum"]
            for k, pose in enumerate(seq):
                self.root.after(k * 2200 + i * 300, lambda p=p, pose=pose: (
                    p.state not in ("drag", "air", "leaving") and (p.act(pose, 2.2), p.burst("sparkle", 3))))
            p.say("party", force=True)

    def start_race(self):
        ps = [p for p in self.pets.values() if p.state not in ("drag", "air", "leaving")]
        if len(ps) < 2:
            if ps:
                ps[0].say(text="一個人要跟誰比啦……", force=True)
            return
        L, T, R, B = work_area()
        self.race_goal = R - 140
        self.race_rank = []
        for i, p in enumerate(ps):
            p.edge = None
            p.follow = False
            p.to_ground()
            p.go_to(L + 120 + i * 40, 3)
        ref = ps[0]
        self.root.after(3500, lambda: ref.say(text="預備……", force=True, secs=1))
        self.root.after(4600, lambda: ref.say(text="開始！", force=True, secs=1))
        self.root.after(4700, lambda: self.race_go(ps))

    def race_go(self, ps):
        for p in ps:
            if p.base_id in self.pets and p.state not in ("drag", "air"):
                p.state = "race"
                p.speed = random.uniform(2.6, 4.2) * (1.15 if p.base_id == "gemini" else 1)
                p.set_pose("idle", 0)
                if random.random() < 0.5:
                    p.say("race_start")

    def race_finish(self, p):
        self.race_rank.append(p)
        if len(self.race_rank) == 1:
            p.burst("sparkle", 8)
            p.act("proud" if p.char.has("proud") else "happy", 4, "race_win", force=True)
            self.add_love(p, 2)
        else:
            p.act("pout" if p.char.has("pout") else "oops", 3, "race_lose")

    # 猜拳、運勢、提醒
    def rps(self, p, mine):
        p.touch()
        self.stat("game")
        hers = random.choice(list(RPS))
        p.act("thinking", 1.2)
        p.say(text=f"剪刀、石頭……布！\n你出 {RPS[mine]}，我出 {RPS[hers]}", force=True, secs=3)

        def result():
            if hers == mine:
                p.act("surprised", 2.2, "rps_draw", force=True)
            elif BEATS[hers] == mine:
                p.burst("sparkle", 5)
                p.act("proud" if p.char.has("proud") else "happy", 2.5, "rps_win", force=True)
            else:
                p.act("pout" if p.char.has("pout") else "oops", 2.5, "rps_lose", force=True)
            self.add_love(p, 1)
        self.root.after(1900, result)

    def fortune(self, p):
        p.touch()
        self.stat("game")
        today = datetime.date.today().isoformat()
        rng = random.Random(today + p.base_id + str(self.settings.get("seed", 0)))
        luck = rng.choices([f[0] for f in FORTUNES], [f[1] for f in FORTUNES])[0]
        item, advice = rng.choice(LUCKY), rng.choice(ADVICE)
        p.act("thinking", 1.6, "fortune", force=True)

        def show():
            good = luck in ("大吉", "中吉")
            if good:
                p.burst("sparkle", 8)
            p.act("happy" if luck != "凶" else "oops", 5)
            p.say(text=f"今日運勢：{luck}！\n幸運物：{item}\n{advice}", force=True, secs=7)
        self.root.after(1800, show)

    def remind_in(self, p, minutes):
        self.reminders.append((time.time() + minutes * 60, p.base_id, minutes))
        p.act("happy", 1.5)
        p.say(text=f"好，{minutes} 分鐘後叫你！", force=True)

    # ---------- 陪讀 ----------
    def start_study(self):
        self.study = time.time() + 25 * 60
        self.break_until = None
        for p in self.pets.values():
            p.touch()
            if p.state in ("idle", "walk", "act", "sleep", "chase"):
                p.follow = False
                p.enter_study()
        ps = list(self.pets.values())
        if ps:
            random.choice(ps).say("study_start", force=True, secs=4)

    def stop_study(self, finished=False):
        self.study = None
        for p in self.pets.values():
            if p.state == "study":
                if finished:
                    p.burst("sparkle", 8)
                    p.act("happy", 4)
                else:
                    p.idle()
        if finished:
            self.stat("study")
        if finished and self.pets:
            p = random.choice(list(self.pets.values()))
            p.say("study_end", force=True, secs=5)
            self.break_until = time.time() + 5 * 60
            if self.settings.get("study_giant", True):
                self.root.after(2500, lambda: self.enter_giant(p.base_id, rest=True))

    # ---------- 主迴圈 ----------
    def loop(self):
        self.frame += 1
        if self.frame % 2:                           # 中間格
            try:
                if not self.hide_reasons:
                    for p in list(self.pets.values()):
                        if self.giant is None or p is self.giant:
                            p.half_step()
                    if self.giant is None:
                        for it in list(self.items):
                            it.half_step()
            except Exception:
                log_error()
            self.root.after(FRAME_MS, self.loop)
            return
        try:
            self.tick += 1
            if self.tick % 15 == 1:
                self.wins = list_windows() if self.settings.get("climb", True) else []
            self.poll_events()
            if self.hide_reasons:
                self.root.after(FRAME_MS, self.loop)
                if self.tick % 15 == 0:
                    self.check_fullscreen()
                return
            for p in list(self.pets.values()):
                if self.giant is None or p is self.giant:
                    p.update()
            if self.giant is None:
                for it in list(self.items):
                    it.update()
            elif self.giant_rest_end and self.tick % 30 == 0:
                self.render_giant_bg()
            if self.tick % 15 == 0:
                self.timers()
            if self.tag and time.time() > self.tag["until"]:
                self.end_tag()
            if self.hs and time.time() > self.hs["until"]:
                self.end_hide_seek()
            self.social()
        except Exception:
            log_error()
        self.root.after(FRAME_MS, self.loop)

    def covered(self, x, y, idx):
        """(x, y) 這一點有沒有被比第 idx 個視窗更上層的視窗蓋住。"""
        for hwnd, l, t, r, b, _ in self.wins[:idx]:
            if l <= x <= r and t <= y + 2 <= b:
                return True
        return False

    # ---------- 撒嬌：把滑鼠拉過來 ----------
    def check_cling(self):
        now = time.time()
        cur = cursor_pos()
        if cur != self.cling_cur:
            self.cling_cur, self.cling_still = cur, now
        if not self.settings.get("cling", False) or self.cling_job or now < self.cling_next:
            return
        if now - self.cling_still < 1.5 or any(user32.GetAsyncKeyState(k) & 0x8000 for k in (1, 2, 4)):
            return
        if self.study or self.giant or self.hs or self.tag:
            return
        free = [p for p in self.pets.values() if p.free() and not p.plat and p.state in ("idle", "walk")]
        if free:
            self.cling_next = now + random.uniform(1.5, 4) * 60
            self.mischief(random.choice(free), manual=False)
        elif self.tick % 600 == 0:
            dbg("自動撒嬌：沒有空閒的角色（" + ", ".join(f"{q.base_id}:{q.state}" for q in self.pets.values()) + "）")

    # ---------- 調皮：抓你的滑鼠去玩 ----------
    def mischief(self, p, kind=None, manual=True):
        if self.cling_job and time.time() - getattr(self, "mis_started", 0) > 20:
            self.cling_job = None                    # 上一次卡住了 → 重來
        if self.cling_job or p.state in ("drag", "air", "leaving", "hide") or p.giant:
            dbg(f"撒嬌被略過：cling_job={self.cling_job} state={p.state} giant={p.giant}")
            return
        if p.sulking:
            return p.say(text="哼，現在不想撒嬌。", force=True)
        self.mis_started = time.time()
        p.edge = None
        p.follow = False
        kind = kind or random.choice(["pat", "pat", "poke", "eat", "eat", "carry"])
        p.touch()
        p.to_ground()
        p.state = "idle"
        sw, sh = p.current_image().size
        head = lambda: (p.x, p.y - sh * .9)
        cheek = lambda: (p.x + sw * .14, p.y - sh * .7)
        mouth = lambda: (p.x, p.y - sh * .64)
        d = random.choice((-1, 1))
        say = lambda key, pose=None, secs=1.6: (lambda: (pose and p.act(pose, secs), p.say(key, force=True, secs=secs)))
        # 每一段：(幾格, 目標位置函式, 一開始要做的事, 是否一直跟著目標)
        if kind == "pat":
            hx, hy = head()
            segs = [(45, head, say("cling", "happy", 1.6), False)]
            for i in range(8):
                segs.append((7, (lambda i=i: (head()[0] + (28 if i % 2 else -28), head()[1])),
                             say("mis_pat", "pat", 3) if i == 0 else None, False))
            segs.append((10, head, lambda: (p.burst("heart", 8), p.act("pat", 2.5, "cling_got", force=True)), False))
        elif kind == "poke":
            segs = [(45, cheek, say("cling", "happy", 1.6), False)]
            for i in range(4):
                segs.append((6, (lambda: (cheek()[0] + 34, cheek()[1] - 12)), None, False))
                segs.append((5, cheek, (say("mis_poke", "puffed" if p.char.has("puffed") else "happy", 2)
                                        if i == 0 else (lambda: p.burst("heart", 1))), False))
        elif kind == "eat":
            segs = [(45, mouth, say("mis_eat", "eat" if p.char.has("eat") else "surprised", 1.8), False)]
            for i in range(6):
                segs.append((5, (lambda i=i: (mouth()[0] + (5 if i % 2 else -5), mouth()[1] + (3 if i % 3 else 0))),
                             say("mis_chew", "eat" if p.char.has("eat") else "happy", 2) if i == 0 else None, False))
            segs.append((14, (lambda: (p.x + d * 320, p.y - sh * 1.4)),
                         say("mis_spit", "surprised", 2), False))
        else:   # carry：頂在頭上跑走
            segs = [(45, head, say("cling", "happy", 1.6), False),
                    (90, head, lambda: (p.go_to(p.x + d * 320, 2.6), p.say("mis_carry", force=True)), True),
                    (8, (lambda: (head()[0], head()[1] - 40)), lambda: (p.idle(), p.act("happy", 2, "mis_return", force=True)), False)]
        self.cling_job = True
        self.mis_manual = manual
        self.mis_frames = 0
        # 撒嬌這幾秒：暫時關掉「打字時隱藏指標」，讓你看得到自己真正的游標被搶走
        try:
            self.mis_vanish = pointer_vanish()
            if self.mis_vanish:
                pointer_vanish(False)
            wake_cursor()
        except Exception:
            self.mis_vanish = False
        dbg(f"撒嬌開始：{p.base_id} {kind} 手動={manual} 強制設定={self.settings.get('cling_force')} "
            f"滑鼠={cursor_pos()} 她的位置=({int(p.x)},{int(p.y)})")
        self._mis_run(p, segs, 0, 0, cursor_pos(), None)

    def mis_end(self):
        unlock_cursor()
        if getattr(self, "mis_vanish", False):
            try:
                pointer_vanish(True)
            except Exception:
                pass
            self.mis_vanish = False

    def _mis_run(self, p, segs, si, k, start, last):
        cur = cursor_pos()
        self.mis_frames += 1
        moved = last and (abs(cur[0] - last[0]) > 12 or abs(cur[1] - last[1]) > 12)
        force = self.mis_manual or self.settings.get("cling_force", False)
        self.mis_force = force
        if force and time.time() - self.mis_started > 9:              # 保險：最多鎖 9 秒
            self.mis_end()
            self.cling_job = None
            return
        if moved and not force and self.mis_frames > 4:            # 她自己來撒嬌時，你動滑鼠她就放手
            dbg(f"  你動了滑鼠 → 放手（{cur} vs {last}）")
            self.mis_end()
            self.cling_job = None
            p.say("cling_abort", force=True)
            return
        if p.base_id not in self.pets or p.state in ("drag", "air", "leaving") or si >= len(segs):
            self.mis_end()
            self.cling_job = None
            if si >= len(segs):
                p.cling_until = time.time() + 6
                self.add_love(p, 1)
            return
        n, target, on_start, follow = segs[si]
        if k == 0 and on_start:
            on_start()
            start = cur
        tx, ty = target()
        e = min(1, (k + 1) / n)
        e = 1 if follow else e * e * (3 - 2 * e)
        x = int(start[0] + (tx - start[0]) * e) if not follow or k < 6 else int(tx)
        y = int(start[1] + (ty - start[1]) * e) if not follow or k < 6 else int(ty)
        if force:
            lock_cursor(x, y)                    # 強制：滑鼠被鎖住，你動不了，直到她放開
        move_cursor(x, y)
        if self.mis_frames <= 4 or self.mis_frames % 30 == 0:
            dbg(f"  第{self.mis_frames}格 段{si}：想搬到 ({x},{y})，實際 {cursor_pos()}")
        if k + 1 >= n:
            si, k, start = si + 1, 0, (x, y)
        else:
            k += 1
        self.root.after(16, lambda: self._mis_run(p, segs, si, k, start, (x, y)))

    def game_list(self, p):
        return [("猜拳：出剪刀", lambda: self.rps(p, "剪刀"), 4.2), ("猜拳：出石頭", lambda: self.rps(p, "石頭"), 4.2),
                ("猜拳：出布", lambda: self.rps(p, "布"), 4.2), ("比大小：猜大", lambda: self.dice(p, True), 4.3),
                ("比大小：猜小", lambda: self.dice(p, False), 4.3), ("猜糖果：左手", lambda: self.candy(p, True), 4.4),
                ("猜糖果：右手", lambda: self.candy(p, False), 4.4), ("-", None, 0),
                ("抽卡", lambda: self.gacha(p), 6.2), ("今日運勢", lambda: self.fortune(p), 7.5),
                ("今天吃什麼", lambda: self.what_to_eat(p), 5), ("講冷笑話", lambda: self.joke(p), 9)]

    def do_pose(self, p, pose):
        self.enqueue(p, lambda: (p.touch(), p.act(pose, 4, pose)), 4.2, play=False)

    # ---------- 話題（日常 / 認真 / 混合） ----------
    def default_topics(self):
        try:
            return json.loads((CHAR_DIR / "topics.json").read_text(encoding="utf-8"))
        except Exception:
            return {"自訂": []}

    def topics(self):
        return self.settings.get("topics") or self.default_topics()

    def edit_topics(self):
        """要改話題時，先把預設的複製一份到設定裡，之後都改設定裡的。"""
        if not self.settings.get("topics"):
            self.settings["topics"] = self.default_topics()
        return self.settings["topics"]

    def topic_line(self):
        tp = self.topics()
        on = [c for c in self.settings.get("topic_on", []) if tp.get(c)]
        if not on:
            return None
        lines = [l for l in tp[random.choice(on)] if not l.startswith("（這一類是給你自己填的")]
        return random.choice(lines) if lines else None

    def talk_topic(self, p=None, force=False):
        free = [q for q in self.pets.values() if q.free() and not q.plat]
        if p is None:
            if not free:
                return
            p = random.choice(free)
        line = self.topic_line()
        if not line:
            if force:
                p.say(text="（還沒有勾選話題類別喔，到控制面板的「話題」分頁勾選）", force=True, secs=4)
            return
        secs = max(3.5, len(line) / 7)
        p.act(random.choice([q for q in ("thinking", "reading", "writing") if p.char.has(q)] or ["happy"]), secs)
        p.say(text=line, force=force, secs=secs)
        others = [q for q in free if q is not p and abs(q.x - p.x) < 500]
        if others and random.random() < .45:
            q = random.choice(others)
            self.root.after(int(secs * 1000) - 300,
                            lambda: q.free() and (q.act("happy", 2.5), q.say(text=random.choice(TOPIC_REACT), secs=2.5)))

    def check_time_chat(self):
        """有時間觀念：不定時看一下時間講一句（大約 10～25 分鐘一次）。"""
        if self.tick < self.next_time_chat or self.study or self.giant or self.hs or self.tag:
            return
        self.next_time_chat = self.tick + int(random.uniform(10, 25) * 60 * FPS)
        if self.settings.get("quiet") or self.settings.get("talk_mode") == "pro":
            return
        free = [q for q in self.pets.values() if q.free()]
        if free:
            p = random.choice(free)
            line = time_line(p)
            if line:
                p.act("happy" if datetime.datetime.now().hour >= 5 else ("yawn" if p.char.has("yawn") else "happy"), 3)
                p.say(text=line, secs=4)

    def chat(self, p):
        """叫她說點話：照控制面板的說話模式（日常／認真／混合）。"""
        p.touch()
        mode = self.settings.get("talk_mode", "daily")
        if mode == "pro" or (mode == "mix" and random.random() < .5):
            line = self.topic_line()
            if line:
                return self.talk_topic(p, force=True)
        lv = self.love_level(p.base_id)
        kind = random.choice(["idle", "idle", "hum", "time", "love" if lv >= 3 else "pat", "greeting"])
        if kind == "time":
            text = time_line(p)
            if text:
                p.act("happy", 3)
                return p.say(text=text, force=True, secs=4)
            kind = "idle"
        pose = {"hum": "hum", "love": "happy", "pat": "happy"}.get(kind, random.choice(["happy", "idle"]))
        p.act(pose if p.char.has(pose) else "happy", 3, kind, force=True)

    def check_topic(self):
        mode = self.settings.get("talk_mode", "daily")
        if mode == "daily" or self.study or self.giant or self.hs or self.tag or self.settings.get("quiet"):
            return
        if self.tick < self.next_topic:
            return
        lo, hi = TALK_FREQ.get(self.settings.get("talk_freq", "偶爾"), (60, 140))
        if mode == "mix":
            lo, hi = lo * 2, hi * 2
        self.next_topic = self.tick + int(random.uniform(lo, hi) * FPS)
        self.talk_topic()

    # ---------- 排隊 ----------
    def enqueue(self, p, fn, secs, play=True):
        """連續按好幾個遊戲／動作時，做完一個再做下一個（最多排 5 個）。"""
        if play and p.sulking:
            return p.say("no_play", force=True)
        now = time.time()
        if now < p.busy_until:
            if len(p.queue) < 5:
                p.queue.append((fn, secs, play))
            return
        p.busy_until = now + secs
        fn()
        self.root.after(int(secs * 1000), lambda: self._next_in_queue(p))

    def _next_in_queue(self, p):
        if p.queue and p.base_id in self.pets:
            fn, secs, play = p.queue.pop(0)
            p.busy_until = 0
            self.enqueue(p, fn, secs, play)

    # ---------- 小遊戲 ----------
    def game_result(self, p, win, lose_pose="pout"):
        p.calm(10)
        if win is None:
            p.act("surprised", 2.2, "rps_draw", force=True)
        elif win:
            p.burst("sparkle", 5)
            p.act("proud" if p.char.has("proud") else "happy", 2.5, "rps_win", force=True)
        else:
            p.act(lose_pose if p.char.has(lose_pose) else "oops", 2.5, "rps_lose", force=True)
        self.add_love(p, 1)

    def dice(self, p, guess_big):
        p.touch()
        self.stat("game")
        n = random.randint(1, 6)
        p.act("thinking", 1.2)
        p.say(text=f"🎲 擲骰子……\n{n} 點！{'大' if n >= 4 else '小'}！", force=True, secs=3)
        you_win = (n >= 4) == guess_big
        self.root.after(1700, lambda: self.game_result(p, not you_win))

    def candy(self, p, left):
        p.touch()
        self.stat("game")
        hand_left = random.random() < .5
        p.act("thinking", 1.4)
        p.say(text="🍬 糖果在哪隻手呢～", force=True, secs=1.6)

        def reveal():
            if hand_left == left:
                p.burst("heart", 5)
                p.act("happy", 2.5, "candy_win", force=True)
            else:
                p.act("pout" if p.char.has("pout") else "happy", 2.5, "candy_lose", force=True)
            self.add_love(p, 1)
        self.root.after(1700, reveal)

    def gacha(self, p):
        p.touch()
        self.stat("game")
        ch = p.base                                   # 卡池以原裝為準
        poses = card_poses(ch)
        by = {}
        for q in poses:
            by.setdefault(rarity_of(ch, ch, q), []).append(q)
        rars = [r for r, _ in RARITY if by.get(r)]
        rar = random.choices(rars, [w for r, w in RARITY if r in rars])[0]
        pose = random.choice(by[rar])
        cards = self.settings.setdefault("cards", {}).setdefault(p.base_id, [])
        new = pose not in cards
        if new:
            cards.append(pose)
        total = len(poses)
        p.act("thinking", 1.2)
        p.say(text="🃏 抽卡中……", force=True, secs=1.3)

        def show():
            if rar in ("SR", "SSR"):
                p.burst("sparkle", 12 if rar == "SSR" else 6)
            p.act(pose, 4.5)
            p.say(text=f"【{rar}】{POSE_NAMES.get(pose, pose)}的{p.name}" + ("　NEW!" if new else "") +
                  f"\n收集 {len(cards)}/{total}", force=True, secs=4.5)
            self.add_love(p, 1)
            self.save()
        self.root.after(1500, show)

    def what_to_eat(self, p):
        p.touch()
        foods = self.settings.get("foods") or FOODS
        food = "白飯！" if p.base_id == "deepseek" and random.random() < .4 else random.choice(foods)
        p.act("thinking", 1.3)
        self.root.after(1400, lambda: (p.act("happy", 3), p.say(text=f"🍱 {food}\n" + random.choice(p.lines("food_pick")),
                                                                  force=True, secs=4)))

    def joke(self, p):
        p.touch()
        q, a = random.choice(JOKES).split("\n", 1)
        p.act("thinking", 2.5)
        p.say(text=q, force=True, secs=2.6)
        self.root.after(2700, lambda: (p.act("happy", 3), p.say(text=a, force=True, secs=3)))
        self.root.after(5900, lambda: p.say("joke_after"))

    # ---------- 吃醋 ----------
    def on_pat(self, p):
        now = time.time()
        self.pat_log = [(t, c) for t, c in self.pat_log if now - t < 20] + [(now, p.base_id)]
        if sum(1 for _, c in self.pat_log if c == p.base_id) < 3 or now < self.jealous_cool or self.giant:
            return
        others = [q for q in self.pets.values() if q is not p and q.free()]
        if not others or random.random() > .6:
            return
        self.jealous_cool = now + 60
        j = random.choice(others)
        j.go_to(p.x + (110 if j.x > p.x else -110), 2.6)

        def arrive():
            j.act("pout" if j.char.has("pout") else "puffed", 2.8, "jealous", force=True)
            j.jealous_until = time.time() + 20
        j.then = arrive

    # ---------- 鬼抓人 ----------
    def start_tag(self):
        ps = [p for p in self.pets.values() if p.state in ("idle", "walk", "act", "sleep") and not p.giant]
        if len(ps) < 2:
            if ps:
                ps[0].say(text="要兩隻以上才能玩喔～", force=True)
            return
        ps = random.sample(ps, min(3, len(ps)))
        for p in ps:
            p.to_ground()
            p.follow = False
            p.state = "tag"
            p.tag_pause = 0
            p.set_pose("happy")
        it = random.choice(ps)
        it.tag_pause = int(1.5 * FPS)
        it.set_pose("idle", 0)
        it.say("tag_start", force=True)
        self.tag = {"it": it, "players": ps, "until": time.time() + 25}

    def end_tag(self):
        g, self.tag = self.tag, None
        for p in g["players"]:
            if p.state == "tag":
                p.state = "idle"
                p.act("tired" if p.char.has("tired") else "happy", 2.5, "tag_end" if random.random() < .6 else None)
                self.add_love(p, 1)

    # ---------- 捉迷藏 ----------
    def start_hide_seek(self):
        if self.giant:
            self.exit_giant()
        ps = [p for p in self.pets.values() if p.state not in ("drag", "air", "leaving")]
        if not ps:
            return
        ps[0].say("hs_count", force=True, secs=2.5)
        self.root.after(2600, lambda: self._hide_all(ps))

    def _hide_all(self, ps):
        kinds = []
        for p in ps:
            opts = ["bottom", "bottom"] + [k for k in ("left", "right") if p.char.has(f"edge_{k}") and k not in kinds]
            k = random.choice(opts)
            kinds.append(k)
            p.hide(k)
        self.hs = {"start": time.time(), "until": time.time() + 90, "left": set(p.base_id for p in ps)}

    def found(self, p, quiet=False):
        if not self.hs or p.base_id not in self.hs["left"]:
            p.idle()
            return
        self.hs["left"].discard(p.base_id)
        kind = p.hide_kind
        p.hide_kind = None
        p.state = "idle"
        if kind in ("left", "right"):
            p.leave_edge()
        if not quiet:
            self.stat("found")
            p.burst("heart", 4)
            p.act("surprised", 2, "found", force=True)
            self.add_love(p, 1)
        if not self.hs["left"]:
            secs = int(time.time() - self.hs["start"])
            self.hs = None
            if not quiet:
                self.root.after(2100, lambda: (p.burst("sparkle", 8), p.act("happy", 3),
                                               p.say(text=f"全部找到了！花了 {secs} 秒～", force=True, secs=4)))

    def end_hide_seek(self):
        hs, self.hs = self.hs, None
        for cid in hs["left"]:
            p = self.pets.get(cid)
            if p and p.state == "hide":
                p.state = "idle"
                if p.hide_kind in ("left", "right"):
                    p.leave_edge()
                p.hide_kind = None
                p.act("happy", 3, None)
                p.say(text="嘿嘿，你找不到我們～", force=True)

    # ---------- 看你在做什麼 ----------
    def check_app(self):
        if not self.settings.get("watch_app", True) or self.study or self.giant:
            return
        try:
            info = foreground_app()
        except Exception:
            return
        cat = None
        if info:
            exe, title = info
            for c, exes, words in APPS:
                if exe in exes or any(wd.lower() in title.lower() for wd in words):
                    cat = c
                    break
        last, since = self.app_seen
        now = time.time()
        if cat != last:
            self.app_seen = (cat, now)
            return
        if not cat or now - since < 20 or now - self.app_said.get(cat, 0) < 15 * 60:
            return
        free = [p for p in self.pets.values() if p.free()]
        if not free:
            return
        self.app_said[cat] = now
        p = random.choice(free)
        pose, lines = APP_REACT[cat]
        own = p.lines("app_" + cat)
        p.act(pose if p.char.has(pose) else "happy", 4)
        p.say(text=random.choice(own or lines))

    def pick_pet(self, prefer=None):
        if self.giant:
            return self.giant
        ps = [p for p in self.pets.values() if p.state != "leaving"]
        if not ps:
            return None
        if prefer and prefer in self.pets:
            return self.pets[prefer]
        return random.choice(ps)

    # ---------- 隱藏 / 系統匣 ----------
    def set_hidden(self, reason, on):
        before = bool(self.hide_reasons)
        (self.hide_reasons.add if on else self.hide_reasons.discard)(reason)
        after = bool(self.hide_reasons)
        if before == after:
            return
        wins = [p.win for p in self.pets.values() if self.giant is None or p is self.giant]
        wins += [it.win for it in self.items] if self.giant is None else []
        for wdw in wins:
            wdw.withdraw() if after else wdw.deiconify()
        if not after:
            for p in self.pets.values():
                p.dirty = True

    def check_fullscreen(self):
        try:
            self.set_hidden("fullscreen", fullscreen_app())
        except Exception:
            log_error()

    def poll_events(self):
        # 巨大化時 Esc 在哪裡按都有效
        if self.giant and user32.GetAsyncKeyState(0x1B) & 0x8000:
            self.exit_giant()
        if self.giant and self.tick % 30 == 0:
            self.giant_order()
        # Ctrl+Alt+P：藏起來 / 叫回來
        down = all(user32.GetAsyncKeyState(k) & 0x8000 for k in (0x11, 0x12, 0x50))
        if down and not self.key_down:
            self.set_hidden("hotkey", "hotkey" not in self.hide_reasons)
        self.key_down = down
        while not self.events.empty():
            ev = self.events.get()
            if ev == "panel":
                self.open_panel()
            elif ev == "toggle":
                self.set_hidden("hotkey", "hotkey" not in self.hide_reasons)
            elif ev == "home":
                self.call_home()
            elif ev == "quit":
                self.quit()

    def call_home(self):
        """把大家叫回主螢幕的右下角（拖到看不見的地方時用）。"""
        self.set_hidden("hotkey", False)
        if self.giant:
            self.exit_giant()
        L, T, R, B = work_area()
        for i, p in enumerate(self.pets.values()):
            p.plat = p.on = None
            p.L, p.R, p.floor = L, R, B
            p.edge = None
            p.follow = False
            p.state = "idle"
            p.x, p.y = R - 150 - i * 150, B
            p.idle()
            p.act("happy", 1.5)

    def start_tray(self):
        try:
            import pystray
        except ImportError:
            return
        try:
            im = Image.open(CHAR_DIR / "claude" / "idle.webp").convert("RGBA")
            bb = im.getbbox()
            side = int((bb[2] - bb[0]) * .62)
            cx = (bb[0] + bb[2]) // 2
            icon = im.crop((cx - side // 2, bb[1], cx + side // 2, bb[1] + side)).resize((64, 64), Image.LANCZOS)
        except Exception:
            icon = Image.new("RGBA", (64, 64), (232, 118, 58, 255))
        q = self.events
        M = pystray.MenuItem
        self.tray = pystray.Icon("DesktopPet", icon, "DesktopPet", pystray.Menu(
            M("開啟控制面板", lambda: q.put("panel"), default=True),
            M("藏起來 / 叫回來（Ctrl+Alt+P）", lambda: q.put("toggle")),
            M("叫大家回到畫面上", lambda: q.put("home")),
            M("全部掰掰（關閉）", lambda: q.put("quit"))))
        self.tray.run_detached()

    def timers(self):
        now = datetime.datetime.now()
        flag = BASE / ".quit"
        if flag.exists():
            try:
                flag.unlink()
            except OSError:
                pass
            return self.quit()
        if self.tick % 30 == 0:
            self.check_fullscreen()
        self.check_topic()
        self.check_time_chat()
        if self.tick % 60 == 0:
            self.check_app()
            self.check_todos()
            self.daily_gift()
        if self.tick % 300 == 0:
            self.daily()
        self.check_cling()
        if not self.pets:
            return
        # 你離開電腦 / 回來
        idle = idle_seconds()
        if not self.away and idle > AWAY_AFTER and not self.study:
            self.away = True
            self.all_sleep()
        elif self.away and idle < 3:
            self.away = False
            for p in self.pets.values():
                if p.state == "sleep":
                    p.touch()
                    p.idle()
            p = self.pick_pet()
            p.burst("heart", 5)
            p.act("happy", 3, "welcome", force=True)
        if self.study and time.time() >= self.study:
            self.stop_study(finished=True)
        if self.giant_rest_end and not self.giant:
            self.giant_rest_end = None
        if self.giant_rest_end and time.time() >= self.giant_rest_end:
            self.giant_rest_end = None
            g = self.giant
            g.burst("sparkle", 10)
            g.act("happy", 3)
            g.say(text="休息結束！繼續加油～", force=True, secs=3)
            self.root.after(2600, self.exit_giant)
        if self.break_until and time.time() >= self.break_until:
            self.break_until = None
            self.pick_pet().say(text="休息夠了嗎？要再來一輪陪讀嗎？", force=True, secs=5)
        for r in [r for r in self.reminders if time.time() >= r[0]]:
            self.reminders.remove(r)
            p = self.pick_pet(r[1])
            p.touch()
            p.burst("sparkle", 6)
            p.act("happy", 4)
            p.say(text=random.choice(p.lines("remind")) + f"（{r[2]} 分鐘）", force=True, secs=6)
        if now.hour != self.last_hour:
            self.last_hour = now.hour
            if self.settings.get("hourly", True) and not self.study and 8 <= now.hour <= 23:
                p = self.pick_pet()
                p.act("stretch" if p.char.has("stretch") else "happy", 4)
                p.say(text=f"{time_text(now)}了～" + random.choice(p.lines("hourly")), force=True, secs=4)
        if self.settings.get("meal", True):
            for hh, mm in ((12, 0), (18, 30)):
                tag = f"{now.date()}-{hh}"
                if (now.hour, now.minute) >= (hh, mm) and (now.hour, now.minute) < (hh, mm + 20) \
                        and tag not in self.settings.get("meals_done", ""):
                    self.settings["meals_done"] = tag
                    p = self.pick_pet("deepseek")
                    p.act("eat" if p.char.has("eat") else "happy", 4)
                    p.say(text=f"{time_text(now)}了，" + ("該吃午餐囉！" if hh == 12 else "該吃晚餐囉！"), force=True, secs=4)
        if self.settings.get("late", True) and now.hour < 5 and now.minute % 30 == 0 \
                and self.last_late != (now.hour, now.minute):
            self.last_late = (now.hour, now.minute)
            p = self.pick_pet()
            p.act("yawn" if p.char.has("yawn") else "tired", 4)
            p.say(text=random.choice([f"現在{time_text(now)}了，你還不睡覺！", f"都{time_text(now)}了，快去睡～",
                                      f"{time_text(now)}了……明天會起不來喔"]), force=True, secs=5)
        if self.tick % 300 == 0:
            self.save()

    def social(self):
        if self.study or self.giant or self.tag or self.hs or len(self.pets) < 2:
            return
        # 有人在賭氣 → 別隻跑去安慰
        if not self.comforting and self.tick % 60 == 0:
            sulkers = [p for p in self.pets.values() if p.state == "sulk"]
            helpers = [p for p in self.pets.values() if p.free()]
            if sulkers and helpers and random.random() < 0.35:
                s, h = sulkers[0], random.choice(helpers)
                self.comforting = True
                self.root.after(15000, lambda: setattr(self, "comforting", False))
                h.go_to(s.x + (100 if h.x > s.x else -100), 2.4)

                def arrive(h=h, s=s):
                    self.comforting = False
                    if s.state == "sulk":
                        h.burst("heart", 3)
                        h.act("pat" if h.char.has("pat") else "happy", 2.5, "comfort")
                        self.root.after(900, lambda: (setattr(s, "anger", max(0.0, s.anger - 15)), s.say("sulk_ignore")))
                h.then = arrive
        if self.dialog_busy or self.tick < self.next_dialog:
            return
        self.next_dialog = self.tick + int(random.uniform(25, 50) * FPS)
        free = [p for p in self.pets.values() if p.free() and not p.plat]
        if len(free) < 2:
            return
        roll = random.random()
        if roll < .12:                                 # 互相摸頭
            a, b = random.sample(free, 2)
            a.go_to(b.x + (100 if a.x > b.x else -100), 2.2)

            def arrive(a=a, b=b):
                if b.state in ("idle", "walk", "act"):
                    a.act("happy", 2.5, "pat_friend")
                    b.burst("heart", 4)
                    b.act("pat", 2.8, "pat")
            a.then = arrive
            return
        if roll < .17:                                 # 自己玩起鬼抓人
            self.start_tag()
            return
        if self.settings.get("talk_mode", "daily") == "pro":
            return
        tags = time_tags()
        ok_time = lambda dl: "when" not in dl or dl["when"] in tags
        ids = {p.base_id: p for p in free}
        specific = []
        for dl in self.dialogs:
            who = dl["who"]
            if "*" in who or not ok_time(dl) or not set(who) <= set(ids):
                continue
            xs = [ids[c].x for c in who]
            if max(xs) - min(xs) < 120 * len(who) + 200:
                specific.append(dl)
        pairs = [(a, b) for i, a in enumerate(free) for b in free[i + 1:] if abs(a.x - b.x) < 320]
        generic = [dl for dl in self.dialogs if "*" in dl["who"] and ok_time(dl)]
        if specific and (random.random() < 0.7 or not (pairs and generic)):
            dl = random.choice(specific)
            lines = dl["lines"]
        elif pairs and generic:
            a, b = random.sample(random.choice(pairs), 2)
            dl = random.choice(generic)
            m = {"a": a.base_id, "b": b.base_id}
            lines = [[m[s], pose, text.replace("{a}", a.name).replace("{b}", b.name)] for s, pose, text in dl["lines"]]
        else:
            return
        self.dialog_busy = True
        who = [self.pets[c] for c in dict.fromkeys(c for c, _, _ in lines)]
        for i, p in enumerate(who[1:], 1):          # 靠近一點再講話
            if abs(p.x - who[0].x) > 260:
                p.go_to(who[0].x + (160 if p.x > who[0].x else -160) * i)
        self.root.after(1500, lambda: self.run_dialog(lines))

    def run_dialog(self, lines, i=0):
        if i >= len(lines) or any(c not in self.pets for c, _, _ in lines):
            self.dialog_busy = False
            return
        cid, pose, text = lines[i]
        p = self.pets[cid]
        if p.state in ("idle", "walk", "act"):
            p.act(pose, 3.2)
        p.say(text=text, secs=3)
        self.root.after(3000, lambda: self.run_dialog(lines, i + 1))

    # ---------- 選單 ----------
    def show_menu(self, p, e):
        """右鍵選單只放日常會用的；其他都在控制面板。"""
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"♥ {p.name}　Lv{self.love_level(p.base_id)} {self.love_title(p.base_id)}", state="disabled")
        m.add_separator()
        m.add_command(label="摸摸頭", command=p.pat)
        m.add_command(label="餵食", command=lambda: self.feed(p))
        m.add_command(label="戳一下", command=p.poke)
        m.add_command(label="撒嬌", command=lambda: self.mischief(p))
        m.add_command(label="說說話", command=lambda: self.chat(p))
        mean = tk.Menu(m, tearoff=0)
        for label, key, amt, pose in TEASES:
            mean.add_command(label=label, command=lambda key=key, amt=amt, pose=pose: p.tease(key, amt, pose))
        games = tk.Menu(m, tearoff=0)
        for label, fn, secs in self.game_list(p):
            if label.startswith(("猜拳", "抽卡", "今日運勢", "今天吃什麼", "講冷笑話")):
                games.add_command(label=label, command=lambda fn=fn, secs=secs: self.enqueue(p, fn, secs))
        m.add_cascade(label="跟她玩", menu=games)
        m.add_cascade(label="惹她生氣", menu=mean)
        if self.study:
            left = max(0, int((self.study - time.time()) // 60) + 1)
            m.add_command(label=f"陪讀中（剩 {left} 分）— 結束", command=self.stop_study)
        else:
            m.add_command(label="陪讀 25 分鐘", command=self.start_study)
        m.add_separator()
        if self.giant is p:
            if p.card_lock:
                m.add_command(label="取消卡片（恢復動作）", command=self.clear_card)
            m.add_command(label="結束巨大化", command=self.exit_giant)
        else:
            m.add_command(label="巨大化", command=lambda: self.enter_giant(p.base_id))
        sz = tk.Menu(m, tearoff=0)
        for name in SIZES:
            sz.add_command(label=("✓ " if self.settings.get("size", "中") == name else "　") + name,
                           command=lambda n=name: self.set_size(n))
        m.add_cascade(label="大小", menu=sz)
        who = tk.Menu(m, tearoff=0)
        for cid in self.base_ids():
            name = self.disp_name(cid)
            if cid in self.pets:
                who.add_command(label=f"✓ {name}", command=lambda cid=cid: self.dismiss(self.pets[cid]))
            else:
                who.add_command(label=f"　{name}", command=lambda cid=cid: self.spawn(cid))
        m.add_cascade(label="叫誰來玩", menu=who)
        m.add_command(label=f"讓{p.name}回家", command=lambda: self.dismiss(p))
        m.add_command(label="開啟控制面板…", command=lambda: self.open_panel(p))
        m.tk_popup(e.x_root, e.y_root)

    # ---------- 巨大化 ----------
    def enter_giant(self, cid, rest=False):
        if self.giant:
            self.exit_giant()
        if cid not in self.pets:
            self.spawn(cid, greet=False)
        p = self.pets[cid]
        if p.state in ("drag", "air", "leaving"):
            return
        for o in self.pets.values():
            if o is not p:
                o.win.withdraw()
        for it in self.items:
            it.win.withdraw()
        L, T, R, B = work_area(p.x, p.floor - 10)
        self.giant_x, self.giant_y = L, T
        self.giant_w, self.giant_hh = R - L, B - T
        self.giant_h = int((B - T) * .96)
        self.giant_cw = min(self.giant_w, int(self.giant_h * 1.3))          # 角色視窗只要包住她就好
        self.giant_cx = L + (self.giant_w - self.giant_cw) // 2
        self.giant = p
        self.giant_dim = rest
        self.giant_rest_end = time.time() + 5 * 60 if rest else None
        p.to_ground()
        p.giant = True
        p.follow = False
        p.edge = None
        p.parts = []
        p.state = "idle"
        p.next_action = self.tick + int(6 * FPS)
        p._bub = None
        self.giant_bg_win = tk.Toplevel(self.root)
        self.giant_bg_win.geometry(f"1x1+{L}+{T}")
        self.giant_bg_win.overrideredirect(True)
        self.giant_bg_win.attributes("-topmost", True)
        self.giant_bg_lw = LayeredWindow(self.giant_bg_win)
        ex = user32.GetWindowLongW(self.giant_bg_lw.hwnd, -20)
        user32.SetWindowLongW(self.giant_bg_lw.hwnd, -20, ex | 0x08000000)      # NOACTIVATE：點了也不會跑到最上面
        self.giant_bg_win.bind("<ButtonPress>", lambda e: self.root.after(1, self.giant_order))
        self.giant_bg_win.bind("<ButtonRelease>", lambda e: self.root.after(1, self.giant_order))
        self.render_giant_bg()
        p.render()
        p.lw.raise_()
        self.giant_bar = GiantBar(self, p)
        if self.panel:
            self.panel.top.attributes("-topmost", True)
        p.act("happy", 2.5)
        p.say(text="休息一下吧，我陪你～" if rest else random.choice(p.lines("love") or ["嗨～"]), force=True, secs=4)
        p.win.focus_force()


    def exit_giant(self):
        p = self.giant
        if not p:
            return
        self.giant = None
        self.giant_rest_end = None
        self.giant_dim = False
        for win in ("giant_bar", "giant_bg_win"):
            obj = getattr(self, win, None)
            if obj is not None:
                try:
                    (obj.top if win == "giant_bar" else obj).destroy()
                except tk.TclError:
                    pass
                setattr(self, win, None)
        if self.panel:
            self.panel.top.attributes("-topmost", False)
        p._bub = None
        p.giant = False
        p.card_lock = None
        p.parts = []
        p.bubble = None
        p.idle()                 # 陪讀中會自動回去讀書
        p.render()
        for o in self.pets.values():
            if o is not p:
                o.win.deiconify()
                o.dirty = True
        for it in self.items:
            it.win.deiconify()
            it.render()

    def giant_bg_pct(self):
        return self.settings.get("giant_rest_bg", 60) if self.giant_dim else self.settings.get("giant_bg", 0)

    def render_giant_bg(self):
        """巨大化的背景：只有暗度改變、休息倒數時才重畫。全透明就藏起來，才點得穿。"""
        win = getattr(self, "giant_bg_win", None)
        if win is None:
            return
        pct = max(0, min(100, self.giant_bg_pct()))
        W, H = self.giant_w, self.giant_hh
        img = Image.new("RGBA", (W, H), (20, 18, 30, int(255 * pct / 100)))
        if self.giant_rest_end:
            d = ImageDraw.Draw(img)
            left = max(0, int(self.giant_rest_end - time.time()))
            d.text((W // 2, int(H * .08)), f"休息中　{left // 60}:{left % 60:02d}", font=TEXT.font(0, int(H * .07)),
                   fill=(255, 255, 255, 230), anchor="mm")
            d.text((W // 2, int(H * .14)), "按 Esc 或右下角「結束」提早結束", font=TEXT.font(0, int(H * .022)),
                   fill=(255, 255, 255, 170), anchor="mm")
        self.giant_bg_lw.show(img, self.giant_x, self.giant_y)
        self.giant_order()

    def giant_order(self):
        """巨大化的上下層：背景 < 角色 < 控制列。"""
        if self.giant:
            self.giant.lw.raise_()
        bar = getattr(self, "giant_bar", None)
        if bar:
            try:
                hwnd = user32.GetParent(bar.top.winfo_id()) or bar.top.winfo_id()
                user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
            except tk.TclError:
                pass

    def owned_cards(self, cid):
        ch = self.chars[cid]
        order = {"SSR": 0, "SR": 1, "R": 2, "N": 3}
        own = [q for q in self.settings.get("cards", {}).get(cid, []) if ch.has(q)]
        return sorted(own, key=lambda q: (order[rarity_of(ch, ch, q)], POSE_NAMES.get(q, q)))

    def show_card(self, cid, pose):
        """圖鑑：巨大化並換成這張卡。"""
        if self.giant is None or self.giant.base_id != cid:
            self.enter_giant(cid)
        g = self.giant
        if not g:
            return
        g.card_lock = None
        g.state = "idle"
        g.card_lock = pose
        g.pose = pose
        g.dirty = True
        g.say(text=f"【{rarity_of(g.base, g.base, pose)}】{POSE_NAMES.get(pose, pose)}的{g.name}", force=True, secs=3)
        if getattr(self, "giant_bar", None):
            self.giant_bar.update_card()

    def clear_card(self):
        if self.giant and self.giant.card_lock:
            self.giant.card_lock = None
            self.giant.idle()
            if getattr(self, "giant_bar", None):
                self.giant_bar.update_card()

    def open_panel(self, p=None):
        if self.panel is None:
            self.panel = Panel(self)
        self.panel.show(p.base_id if p else None)

    def toggle_follow(self, p):
        p.follow = not p.follow
        p.touch()
        if p.follow:
            p.say("follow")
            p.state = "walk"
            p.speed = 2.2
            p.set_pose("idle", 0)
        else:
            p.idle()

    def toggle(self, key, value):
        self.settings[key] = value
        self.save()

    def set_size(self, name):
        self.settings["size"] = name
        self.sprite_h = SIZES[name]
        self.set_size_dims()
        for p in self.pets.values():
            p.dirty = True
        self.save()

    def run(self):
        self.start_tray()
        self.root.after(3000, self.daily)
        self.loop()
        self.root.mainloop()


# ---------------------------------------------------------------- 巨大化的控制列
class GiantBar:
    """巨大化時右上角的小視窗：背景暗度、換卡片、開圖鑑、結束；可以縮小成兩顆小圓鈕。"""

    def __init__(self, world, pet):
        self.w, self.p = world, pet
        bg, fg, mute = "#2b2530", "#ffffff", "#bfb4c4"
        self.bg = bg
        top = self.top = tk.Toplevel(world.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=bg)
        top.attributes("-alpha", .92)
        font = ("Microsoft JhengHei", 10)
        self.btn = btn = dict(bg="#463d4d", fg=fg, activebackground="#5d5266", activeforeground=fg, relief="flat",
                              font=font, padx=8, pady=2, cursor="hand2", bd=0)
        # 展開的樣子
        f = self.full = tk.Frame(top, bg=bg, padx=12, pady=10)
        head = tk.Frame(f, bg=bg)
        head.grid(row=0, column=0, columnspan=4, sticky="ew")
        tk.Label(head, text="巨大化", bg=bg, fg=mute, font=font).pack(side="left")
        tk.Button(head, text="×", command=world.exit_giant, **dict(btn, bg="#c0533d", activebackground="#d8654d", padx=6)).pack(side="right")
        tk.Button(head, text="－", command=self.collapse, **dict(btn, padx=7)).pack(side="right", padx=4)
        tk.Label(f, text="背景暗度", bg=bg, fg=mute, font=font).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.key = "giant_rest_bg" if world.giant_dim else "giant_bg"
        self.v = tk.IntVar(value=world.giant_bg_pct())
        self.pct = tk.Label(f, text=f"{self.v.get()}%", bg=bg, fg=fg, font=font, width=5)
        self.pct.grid(row=1, column=3, sticky="e", pady=(8, 0))
        tk.Scale(f, from_=0, to=100, orient="horizontal", variable=self.v, showvalue=False, length=170,
                 bg=bg, fg=fg, troughcolor="#4a4152", highlightthickness=0, bd=0, sliderrelief="flat",
                 command=self.changed).grid(row=1, column=1, columnspan=2, padx=6, pady=(8, 0))
        tk.Button(f, text="◀", command=lambda: self.step(-1), **btn).grid(row=2, column=0, pady=(8, 0), sticky="w")
        self.card = tk.Label(f, text="", bg=bg, fg=fg, font=font, width=16)
        self.card.grid(row=2, column=1, columnspan=2, pady=(8, 0))
        tk.Button(f, text="▶", command=lambda: self.step(1), **btn).grid(row=2, column=3, pady=(8, 0), sticky="e")
        row = tk.Frame(f, bg=bg)
        row.grid(row=3, column=0, columnspan=4, pady=(8, 0), sticky="ew")
        tk.Button(row, text="恢復動作", command=world.clear_card, **btn).pack(side="left")
        tk.Button(row, text="開圖鑑", command=self.gallery, **btn).pack(side="left", padx=6)
        # 縮小的樣子：兩顆小圓鈕
        m = self.mini = tk.Frame(top, bg=bg, padx=6, pady=6)
        tk.Button(m, text="≡", command=self.expand, **dict(btn, padx=8)).pack(side="left")
        tk.Button(m, text="×", command=world.exit_giant, **dict(btn, bg="#c0533d", activebackground="#d8654d", padx=8)).pack(side="left", padx=(6, 0))
        top.bind("<Escape>", lambda e: world.exit_giant())
        self.area = work_area(pet.x, pet.floor - 10)
        self.expand()
        self.update_card()

    def place(self):
        self.top.update_idletasks()
        L, T, R, B = self.area
        self.top.geometry(f"+{R - self.top.winfo_reqwidth() - 16}+{T + 16}")     # 右上角

    def collapse(self):
        self.full.pack_forget()
        self.mini.pack()
        self.place()

    def expand(self):
        self.mini.pack_forget()
        self.full.pack()
        self.place()

    def changed(self, val):
        n = int(float(val))
        self.pct.config(text=f"{n}%")
        self.w.settings[self.key] = n
        self.w.render_giant_bg()

    def update_card(self):
        lock = self.p.card_lock
        self.card.config(text=f"【{rarity_of(self.p.base, self.p.base, lock)}】{POSE_NAMES.get(lock, lock)}" if lock
                         else f"動作模式（{len(self.w.owned_cards(self.p.base_id))} 張卡）")

    def step(self, d):
        cards = self.w.owned_cards(self.p.base_id)
        if not cards:
            self.card.config(text="還沒抽到卡喔")
            return
        cur = self.p.card_lock
        i = cards.index(cur) if cur in cards else (-1 if d > 0 else len(cards))
        i = (i + d) % len(cards)
        self.w.show_card(self.p.base_id, cards[i])
        self.update_card()

    def gallery(self):
        w = self.w
        w.open_panel(self.p)
        pn = w.panel
        pn.ensure("圖鑑")
        pn.nb.select(pn.tabs["圖鑑"])
        pn.gal_pick.set(w.chars[self.p.base_id].cfg.get("name", self.p.base_id))
        pn.gallery_fill()
        pn.top.attributes("-topmost", True)
        pn.top.lift()


# ---------------------------------------------------------------- 控制面板
C_BG, C_CARD, C_LINE = "#fbf6f0", "#ffffff", "#eadfd4"
C_TEXT, C_MUTED, C_ACCENT = "#3a2a25", "#9a8a80", "#e8763a"
C_PINK, C_RED = "#ec6f95", "#e0533d"
FONT = "Microsoft JhengHei"
STATE_NAMES = {"idle": "閒晃中", "walk": "散步中", "act": "表演中", "sleep": "睡覺中", "sulk": "賭氣中",
               "study": "陪讀中", "edge": "躲在螢幕邊邊", "drag": "被你拎著", "air": "飛在空中",
               "stack": "疊在別人頭上", "tag": "玩鬼抓人中", "hide": "躲起來了", "chase": "追東西中",
               "race": "賽跑中", "leaving": "回家中"}


def avatar(char, size, bg=C_CARD):
    """角色頭像：從 idle 裁出頭，做成圓形。"""
    from PIL import ImageTk
    im = Image.open(char.poses["idle"][0]).convert("RGBA")
    bb = im.getbbox()
    side = int((bb[2] - bb[0]) * .62)
    cx = (bb[0] + bb[2]) // 2
    head = im.crop((cx - side // 2, bb[1], cx + side // 2, bb[1] + side)).resize((size * 2, size * 2), Image.LANCZOS)
    disc = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    mask = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 2 - 1, size * 2 - 1), fill=255)
    c = (char.cfg.get("accent") or C_ACCENT).lstrip("#")
    ring = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    ImageDraw.Draw(disc).ellipse((0, 0, size * 2 - 1, size * 2 - 1), fill=(255, 248, 240, 255))
    disc.alpha_composite(head)
    out = Image.new("RGBA", (size * 2, size * 2), bg)
    out.paste(disc, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((1, 1, size * 2 - 2, size * 2 - 2), outline=ring, width=4)
    return ImageTk.PhotoImage(out.resize((size, size), Image.LANCZOS))


class ScrollFrame(tk.Frame):
    """可以用滾輪捲動的區塊。"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_BG)
        self.canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=C_BG)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.item = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.item, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self.wheel))
        self.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def wheel(self, e):
        # 滑鼠在清單、文字框、下拉選單裡 → 讓它自己捲，不要捲整頁
        try:
            if e.widget.winfo_class() in ("Listbox", "Text", "TCombobox", "Scale", "TScale"):
                return
        except (AttributeError, tk.TclError):
            return
        # 內容比視窗短就不捲（不然上面會多出一塊空白）
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            self.canvas.yview_moveto(0)
            return
        self.canvas.yview_scroll(int(-e.delta / 120), "units")


class Panel:
    """控制面板：大家、待辦、紀錄、設定，後面每隻角色一頁。"""

    def __init__(self, world):
        self.w = world
        top = self.top = tk.Toplevel(world.root)
        top.title("DesktopPet 控制面板")
        top.configure(bg=C_BG)
        top.geometry("760x780")
        top.minsize(560, 520)
        top.protocol("WM_DELETE_WINDOW", top.withdraw)
        icon = BASE / "dev" / "icon.ico"
        try:
            top.iconbitmap(str(icon) if icon.exists() else sys.executable)
        except Exception:
            pass
        self.style()
        self.imgs = []
        self.job = None
        self.nb = ttk.Notebook(top)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabs = {}
        self.cw = {}               # 每隻角色頁的元件
        self.todo_sig = None
        self.lazy = {}
        self.build_all()
        for name, fn in (("待辦", self.build_todo), ("話題", self.build_topics), ("圖鑑", self.build_gallery),
                         ("紀錄", self.build_stats), ("設定", self.build_settings)):
            self.new_page(name)
            self.lazy[name] = fn
        for cid in world.base_ids():
            img = avatar(world.chars[cid], 22, bg="#efe4d8")
            self.imgs.append(img)
            self.new_page(world.disp_name(cid), image=img, key=cid)
            self.lazy[cid] = (lambda cid=cid: self.build_char(cid))
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.ensure_current())
        self.refresh()

    def ensure(self, key):
        fn = self.lazy.pop(key, None)
        if fn:
            fn()

    def ensure_current(self):
        cur = self.nb.select()
        for key, sf in self.tabs.items():
            if str(sf) == cur:
                if key in self.lazy:
                    self.ensure(key)
                    self.refresh()
                return

    # ---------- 樣式 ----------
    def style(self):
        st = ttk.Style(self.top)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", font=(FONT, 10), background=C_CARD, foreground=C_TEXT)
        st.configure("TNotebook", background=C_BG, borderwidth=0, tabmargins=(2, 4, 2, 0))
        st.configure("TNotebook.Tab", padding=(8, 5), background="#efe4d8", foreground=C_TEXT, borderwidth=0,
                     font=(FONT, 10))
        st.map("TNotebook.Tab", background=[("selected", C_CARD)], foreground=[("selected", C_ACCENT)])
        # 分頁標籤不要畫焦點虛線框
        st.layout("TNotebook.Tab", [("Notebook.tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                ("Notebook.label", {"side": "top", "sticky": ""})]})]})])
        st.configure("TButton", background="#f6eee6", foreground=C_TEXT, borderwidth=0, focusthickness=0,
                     padding=(6, 4), relief="flat")
        st.map("TButton", background=[("disabled", "#f7f3ef"), ("active", "#ffe2cc")],
               foreground=[("disabled", "#cbbfb6")])
        st.configure("Accent.TButton", background=C_ACCENT, foreground="#ffffff", font=(FONT, 10, "bold"))
        st.map("Accent.TButton", background=[("disabled", "#f2c9ae"), ("active", "#f08c55")])
        st.configure("Mean.TButton", background="#fdecea", foreground="#b13a2a")
        st.map("Mean.TButton", background=[("disabled", "#f7f3ef"), ("active", "#fbd3cd")])
        self.check_images(st)
        for w in ("TCheckbutton", "TRadiobutton"):
            st.configure(w, background=C_CARD, foreground=C_TEXT, indicatorbackground="#ffffff",
                         indicatorforeground="#ffffff", upperbordercolor=C_LINE, lowerbordercolor=C_LINE)
            st.map(w, background=[("active", C_CARD)],
                   indicatorbackground=[("selected", C_ACCENT), ("pressed", "#ffe2cc")],
                   indicatorforeground=[("selected", "#ffffff")])
        st.configure("Love.Horizontal.TProgressbar", troughcolor="#f8e4ea", background=C_PINK, bordercolor="#f8e4ea",
                     lightcolor=C_PINK, darkcolor=C_PINK, thickness=10)
        st.configure("Anger.Horizontal.TProgressbar", troughcolor="#f6e3df", background=C_RED, bordercolor="#f6e3df",
                     lightcolor=C_RED, darkcolor=C_RED, thickness=10)
        st.configure("TCombobox", fieldbackground="#fffaf5")
        st.configure("TEntry", fieldbackground="#fffaf5")

    def check_images(self, st):
        from PIL import ImageTk
        n = 18

        def box(checked, dim=False):
            im = Image.new("RGBA", (n * 4, n * 4), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            fill = (C_ACCENT if not dim else "#f2c9ae") if checked else "#ffffff"
            d.rounded_rectangle((2, 2, n * 4 - 3, n * 4 - 3), radius=14, fill=fill,
                                outline=fill if checked else "#d8c8bb", width=5)
            if checked:
                d.line([(n * .9, n * 2.1), (n * 1.7, n * 2.9), (n * 3.1, n * 1.2)], fill="#ffffff", width=9, joint="curve")
            return ImageTk.PhotoImage(im.resize((n, n), Image.LANCZOS))
        self.ck = [box(False), box(True), box(True, True), box(False)]
        st.element_create("Pet.check", "image", self.ck[0], ("disabled", "selected", self.ck[2]),
                          ("selected", self.ck[1]), ("disabled", self.ck[3]), sticky="w")
        st.layout("TCheckbutton", [("Checkbutton.padding", {"sticky": "nswe", "children": [
            ("Pet.check", {"side": "left", "sticky": ""}),
            ("Checkbutton.focus", {"side": "left", "sticky": "w", "children": [
                ("Checkbutton.label", {"sticky": "nswe"})]})]})])
        st.configure("TCheckbutton", padding=(2, 2))

    # ---------- 小工具 ----------
    def page(self, text, image=None, key=None):
        k = key if key is not None else text
        if k in self.tabs:                    # 已經先建好空分頁了
            return self.tabs[k].inner
        return self.new_page(text, image, key)

    def new_page(self, text, image=None, key=None):
        sf = ScrollFrame(self.nb)
        if image:
            self.nb.add(sf, text=text, image=image, compound="left")
        else:
            self.nb.add(sf, text=text)
        self.tabs[key if key is not None else text] = sf
        return sf.inner

    def card(self, parent, title, color=C_ACCENT, note=None):
        outer = tk.Frame(parent, bg=C_LINE)
        outer.pack(fill="x", padx=10, pady=5)
        inner = tk.Frame(outer, bg=C_CARD, padx=12, pady=9)
        inner.pack(fill="both", padx=1, pady=1)
        head = tk.Frame(inner, bg=C_CARD)
        head.pack(fill="x")
        tk.Label(head, text=title, bg=C_CARD, fg=color, font=(FONT, 11, "bold")).pack(side="left")
        if note:
            tk.Label(head, text=note, bg=C_CARD, fg=C_MUTED, font=(FONT, 9)).pack(side="left", padx=8)
        body = tk.Frame(inner, bg=C_CARD)
        body.pack(fill="x", pady=(6, 0))
        return body

    @staticmethod
    def buttons(parent, items, cols=4, style="TButton"):
        for i in range(cols):
            parent.columnconfigure(i, weight=1, uniform="b")
        for i, (label, cmd) in enumerate(items):
            ttk.Button(parent, text=label, command=cmd, style=style).grid(
                row=i // cols, column=i % cols, padx=3, pady=3, sticky="ew")

    def label(self, parent, text="", muted=False, size=10, bold=False, **kw):
        return tk.Label(parent, text=text, bg=C_CARD, fg=C_MUTED if muted else C_TEXT,
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

    def pet(self, cid):
        return self.w.pets.get(cid)

    def do(self, cid, fn):
        p = self.pet(cid)
        if p:
            fn(p)

    # ---------- 大家 ----------
    def build_all(self):
        w = self.w
        f = self.page("大家", key=None)
        body = self.card(f, "叫誰來玩", note="點頭像叫出來或送回家")
        self.summon_vars = {}
        for i, cid in enumerate(w.base_ids()):
            ch = w.chars[cid]
            img = avatar(ch, 52)
            self.imgs.append(img)
            v = tk.BooleanVar(value=cid in w.pets)
            self.summon_vars[cid] = v
            ttk.Checkbutton(body, text=ch.cfg.get("name", cid), image=img, compound="top", variable=v,
                            command=lambda c=cid, v=v: self.toggle_pet(c, v.get())).grid(row=0, column=i, padx=6)

        body = self.card(f, "大家一起")
        self.buttons(body, [("集合到滑鼠旁", w.gather), ("排排站", w.line_up), ("開派對", w.party),
                            ("賽跑", w.start_race), ("捉迷藏", w.start_hide_seek), ("鬼抓人", w.start_tag),
                            ("一起睡覺", w.all_sleep), ("叫醒大家", w.all_wake)], cols=4)

        body = self.card(f, "丟東西給大家", note="會掉在畫面上方；拿到她身上她就會吃或接住")
        items = [(n, lambda n=n: self.drop(n)) for n in ITEMS] + [("全部收起來", lambda: [it.remove() for it in list(w.items)])]
        self.buttons(body, items, cols=5)

        body = self.card(f, "陪讀")
        self.study_btn = ttk.Button(body, text="陪讀 25 分鐘", style="Accent.TButton", command=self.toggle_study)
        self.study_btn.grid(row=0, column=0, sticky="w")
        self.study_giant = tk.BooleanVar(value=w.settings.get("study_giant", True))
        ttk.Checkbutton(body, text="結束時用巨大化陪我休息 5 分鐘", variable=self.study_giant,
                        command=lambda: w.toggle("study_giant", self.study_giant.get())).grid(row=0, column=1, padx=10)

        body = self.card(f, "巨大化", note="只留一隻，佔滿整個螢幕")
        names = {w.chars[c].cfg.get("name", c): c for c in w.base_ids()}
        self.giant_pick = ttk.Combobox(body, values=list(names), state="readonly", width=8)
        self.giant_pick.current(0)
        self.giant_pick.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(body, text="巨大化", style="Accent.TButton",
                   command=lambda: w.enter_giant(names[self.giant_pick.get()])).grid(row=0, column=1, padx=3)
        ttk.Button(body, text="巨大化休息 5 分鐘",
                   command=lambda: w.enter_giant(names[self.giant_pick.get()], rest=True)).grid(row=0, column=2, padx=3)
        ttk.Button(body, text="結束巨大化", command=w.exit_giant).grid(row=0, column=3, padx=3)
        self.label(body, "摸頭、戳臉頰、碰身體反應都不一樣；在頭上來回晃是一直摸；按 Esc 或右上角 × 結束",
                   muted=True, size=9, wraplength=520, justify="left").grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
        for r, (key, label, default) in enumerate((("giant_bg", "一般巨大化的背景暗度", 0),
                                                   ("giant_rest_bg", "休息模式的背景暗度", 60)), 2):
            self.label(body, label).grid(row=r, column=0, columnspan=2, sticky="w", pady=(8, 0))
            v = tk.IntVar(value=w.settings.get(key, default))
            txt = self.label(body, f"{v.get()}%", muted=True)
            txt.grid(row=r, column=3, sticky="w", pady=(8, 0))

            def changed(val, key=key, v=v, txt=txt):
                n = int(float(val))
                txt.config(text=f"{n}%")
                w.settings[key] = n
                if w.giant:
                    w.giant.dirty = True
            ttk.Scale(body, from_=0, to=100, variable=v, command=changed, length=180).grid(
                row=r, column=2, sticky="w", pady=(8, 0))
        self.label(body, "背景不是全透明時，點到背景不會穿透到後面的視窗", muted=True, size=9).grid(
            row=4, column=0, columnspan=4, sticky="w", pady=(4, 0))

    def toggle_pet(self, cid, on):
        if on:
            self.w.spawn(cid)
        elif cid in self.w.pets:
            self.w.dismiss(self.w.pets[cid])

    def drop(self, name):
        L, T, R, B = work_area()
        self.w.drop_item_at(name, (L + R) / 2 + random.randint(-300, 300), T + 80)

    def toggle_study(self):
        self.w.stop_study() if self.w.study else self.w.start_study()

    # ---------- 待辦 ----------
    def build_todo(self):
        f = self.page("待辦")
        body = self.card(f, "新增待辦", note="時間可以不填；填了時間到會有人來提醒你")
        self.todo_text = ttk.Entry(body, width=30)
        self.todo_text.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.todo_time = ttk.Entry(body, width=7)
        self.todo_time.grid(row=0, column=1, padx=(0, 6))
        self.todo_time.insert(0, "HH:MM")
        self.todo_time.bind("<FocusIn>", lambda e: self.todo_time.get() == "HH:MM" and self.todo_time.delete(0, "end"))
        ttk.Button(body, text="新增", style="Accent.TButton", command=self.add_todo).grid(row=0, column=2)
        body.columnconfigure(0, weight=1)
        self.todo_text.bind("<Return>", lambda e: self.add_todo())
        self.todo_body = self.card(f, "清單", note="打勾＝完成，她們會誇你")

    def add_todo(self):
        t = self.todo_text.get().strip()
        if not t:
            return
        tm = self.todo_time.get().strip()
        m = re.fullmatch(r"(\d{1,2})[:：](\d{2})", tm)
        tm = f"{int(m.group(1)):02d}:{m.group(2)}" if m and int(m.group(1)) < 24 and int(m.group(2)) < 60 else ""
        self.w.settings.setdefault("todos", []).append({"text": t, "time": tm, "done": False, "notified": ""})
        self.w.save()
        self.todo_text.delete(0, "end")
        self.todo_sig = None
        self.refresh_todos()

    def refresh_todos(self):
        todos = self.w.settings.get("todos", [])
        sig = json.dumps(todos, ensure_ascii=False)
        if sig == self.todo_sig:
            return
        self.todo_sig = sig
        for c in self.todo_body.winfo_children():
            c.destroy()
        if not todos:
            self.label(self.todo_body, "目前沒有待辦事項 🎉", muted=True).pack(anchor="w")
            return
        for td in sorted(todos, key=lambda d: (d.get("done"), d.get("time") or "99:99")):
            row = tk.Frame(self.todo_body, bg=C_CARD)
            row.pack(fill="x", pady=2)
            v = tk.BooleanVar(value=td.get("done"))
            cb = ttk.Checkbutton(row, text=td["text"], variable=v,
                                 command=lambda td=td, v=v: self.todo_toggle(td, v.get()))
            cb.pack(side="left")
            if td.get("time"):
                self.label(row, td["time"], muted=True).pack(side="left", padx=8)
            ttk.Button(row, text="刪除", width=5, command=lambda td=td: self.todo_del(td)).pack(side="right")
        ttk.Button(self.todo_body, text="清除已完成", command=self.todo_clear).pack(anchor="e", pady=(6, 0))

    def todo_toggle(self, td, done):
        if done:
            self.w.todo_done(td)
        else:
            td["done"] = False
            self.w.save()
        self.todo_sig = None
        self.refresh_todos()

    def todo_del(self, td):
        self.w.settings["todos"].remove(td)
        self.w.save()
        self.todo_sig = None
        self.refresh_todos()

    def todo_clear(self):
        self.w.settings["todos"] = [t for t in self.w.settings.get("todos", []) if not t.get("done")]
        self.w.save()
        self.todo_sig = None
        self.refresh_todos()

    # ---------- 話題 ----------
    def build_topics(self):
        w = self.w
        f = self.page("話題")
        body = self.card(f, "說話模式")
        self.mode_var = tk.StringVar(value=w.settings.get("talk_mode", "daily"))
        for i, (k, label) in enumerate((("daily", "日常：平常的閒聊"), ("pro", "認真：只講勾選的專業話題"),
                                        ("mix", "混合：兩種都有"))):
            ttk.Radiobutton(body, text=label, value=k, variable=self.mode_var,
                            command=lambda: w.toggle("talk_mode", self.mode_var.get())).grid(row=0, column=i, padx=8, sticky="w")
        self.label(body, "多久講一次專業話題：", muted=True).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.freq_var = tk.StringVar(value=w.settings.get("talk_freq", "偶爾"))
        fr = tk.Frame(body, bg=C_CARD)
        fr.grid(row=1, column=1, columnspan=2, sticky="w", pady=(6, 0))
        for n in TALK_FREQ:
            ttk.Radiobutton(fr, text=n, value=n, variable=self.freq_var,
                            command=lambda: w.toggle("talk_freq", self.freq_var.get())).pack(side="left", padx=6)
        ttk.Button(body, text="現在講一句", style="Accent.TButton",
                   command=lambda: w.talk_topic(force=True)).grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.cat_body = self.card(f, "要講哪些類別", note="可以勾好幾個")
        body = self.card(f, "編輯句子", note="選一個類別，新增或刪除她們會說的句子")
        top = tk.Frame(body, bg=C_CARD)
        top.pack(fill="x")
        self.cat_pick = ttk.Combobox(top, state="readonly", width=12)
        self.cat_pick.pack(side="left")
        self.cat_pick.bind("<<ComboboxSelected>>", lambda e: self.topic_fill())
        ttk.Button(top, text="還原這一類的預設", command=self.topic_reset).pack(side="left", padx=6)
        ttk.Button(top, text="刪除這一類", command=self.topic_del_cat).pack(side="left")
        mid = tk.Frame(body, bg=C_CARD)
        mid.pack(fill="x", pady=6)
        self.topic_list = tk.Listbox(mid, height=9, bg="#fffaf5", fg=C_TEXT, selectbackground="#ffd9bf",
                                     selectforeground=C_TEXT, relief="flat", highlightthickness=1, activestyle="none",
                                     highlightcolor=C_LINE, highlightbackground=C_LINE, font=(FONT, 10))
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.topic_list.yview)
        self.topic_list.configure(yscrollcommand=sb.set)
        self.topic_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        bot = tk.Frame(body, bg=C_CARD)
        bot.pack(fill="x")
        self.topic_entry = ttk.Entry(bot)
        self.topic_entry.pack(side="left", fill="x", expand=True)
        self.topic_entry.bind("<Return>", lambda e: self.topic_add())
        ttk.Button(bot, text="新增句子", style="Accent.TButton", command=self.topic_add).pack(side="left", padx=6)
        ttk.Button(bot, text="刪除選取的", command=self.topic_del).pack(side="left")
        newc = tk.Frame(body, bg=C_CARD)
        newc.pack(fill="x", pady=(10, 0))
        self.label(newc, "新增類別：", muted=True).pack(side="left")
        self.cat_entry = ttk.Entry(newc, width=14)
        self.cat_entry.pack(side="left")
        ttk.Button(newc, text="新增", command=self.topic_add_cat).pack(side="left", padx=6)
        self.topic_cats()

    def topic_cats(self, select=None):
        tp = self.w.topics()
        for c in self.cat_body.winfo_children():
            c.destroy()
        on = set(self.w.settings.get("topic_on", []))
        for i, cat in enumerate(tp):
            v = tk.BooleanVar(value=cat in on)
            ttk.Checkbutton(self.cat_body, text=f"{cat}（{len(tp[cat])}）", variable=v,
                            command=lambda c=cat, v=v: self.topic_toggle(c, v.get())).grid(
                row=i // 4, column=i % 4, padx=6, pady=2, sticky="w")
        self.cat_pick["values"] = list(tp)
        if select and select in tp:
            self.cat_pick.set(select)
        elif self.cat_pick.get() not in tp:
            self.cat_pick.set(next(iter(tp), ""))
        self.topic_fill()

    def topic_toggle(self, cat, on):
        lst = self.w.settings.setdefault("topic_on", [])
        if on and cat not in lst:
            lst.append(cat)
        elif not on and cat in lst:
            lst.remove(cat)
        self.w.save()

    def topic_fill(self):
        self.topic_list.delete(0, "end")
        for line in self.w.topics().get(self.cat_pick.get(), []):
            self.topic_list.insert("end", line)

    def topic_add(self):
        t = self.topic_entry.get().strip()
        cat = self.cat_pick.get()
        if t and cat:
            tp = self.w.edit_topics()
            tp.setdefault(cat, [])
            tp[cat] = [l for l in tp[cat] if not l.startswith("（這一類是給你自己填的")] + [t]
            self.w.save()
            self.topic_entry.delete(0, "end")
            self.topic_cats(cat)
            self.topic_list.see("end")

    def topic_del(self):
        cat = self.cat_pick.get()
        tp = self.w.edit_topics()
        for i in reversed(self.topic_list.curselection()):
            del tp[cat][i]
        self.w.save()
        self.topic_cats(cat)

    def topic_reset(self):
        cat = self.cat_pick.get()
        d = self.w.default_topics()
        if cat in d:
            self.w.edit_topics()[cat] = list(d[cat])
            self.w.save()
            self.topic_cats(cat)

    def topic_add_cat(self):
        name = self.cat_entry.get().strip()
        if name:
            self.w.edit_topics().setdefault(name, [])
            self.topic_toggle(name, True)
            self.cat_entry.delete(0, "end")
            self.topic_cats(name)

    def topic_del_cat(self):
        cat = self.cat_pick.get()
        tp = self.w.edit_topics()
        if cat in tp:
            del tp[cat]
            self.topic_toggle(cat, False)
            self.w.save()
            self.topic_cats()

    # ---------- 圖鑑 ----------
    def build_gallery(self):
        w = self.w
        f = self.page("圖鑑")
        body = self.card(f, "抽卡圖鑑", note="點已經抽到的卡：她會巨大化並換成那張（只說話、不做動作）")
        top = tk.Frame(body, bg=C_CARD)
        top.pack(fill="x")
        names = {w.chars[c].cfg.get("name", c): c for c in w.base_ids()}
        self.gal_names = names
        self.gal_pick = ttk.Combobox(top, values=list(names), state="readonly", width=8)
        self.gal_pick.current(0)
        self.gal_pick.pack(side="left")
        self.gal_pick.bind("<<ComboboxSelected>>", lambda e: self.gallery_fill())
        self.gal_count = self.label(top, "", muted=True)
        self.gal_count.pack(side="left", padx=10)
        ttk.Button(top, text="取消卡片（恢復動作）", command=w.clear_card).pack(side="right")
        legend = tk.Frame(body, bg=C_CARD)
        legend.pack(fill="x", pady=(6, 0))
        for r in ("SSR", "SR", "R", "N"):
            tk.Label(legend, text=f" {r} ", bg=RARITY_COLOR[r], fg="#ffffff", font=(FONT, 8, "bold")).pack(side="left", padx=3)
        self.label(legend, "還沒抽到的是灰色剪影", muted=True, size=9).pack(side="left", padx=8)
        self.gal_grid = tk.Frame(body, bg=C_CARD)
        self.gal_grid.pack(fill="x", pady=(8, 0))
        self.gal_thumbs = {}
        self.gal_sig = None
        self.gallery_fill()

    def thumb(self, ch, pose, owned):
        from PIL import ImageTk
        key = (ch.id, pose, owned)
        if key not in self.gal_thumbs:
            im = Image.open(ch.poses[pose][0]).convert("RGBA")
            im = im.crop(im.getbbox())
            k = 96 / im.height
            im = im.resize((max(1, int(im.width * k)), 96), Image.LANCZOS)
            if not owned:
                a = im.getchannel("A")
                im = Image.new("RGBA", im.size, (205, 195, 188, 255))
                im.putalpha(a)
            box = Image.new("RGBA", (84, 100), (255, 255, 255, 0))
            if im.width > 84:
                im = im.resize((84, int(im.height * 84 / im.width)), Image.LANCZOS)
            box.alpha_composite(im, ((84 - im.width) // 2, 100 - im.height))
            bg = Image.new("RGBA", box.size, (255, 255, 255, 255))
            bg.alpha_composite(box)
            self.gal_thumbs[key] = ImageTk.PhotoImage(bg)
        return self.gal_thumbs[key]

    def gallery_fill(self):
        w = self.w
        cid = self.gal_names.get(self.gal_pick.get())
        if not cid:
            return
        ch = w.chars[cid]
        owned = set(w.settings.get("cards", {}).get(cid, []))
        poses = card_poses(ch)
        order = {"SSR": 0, "SR": 1, "R": 2, "N": 3}
        poses.sort(key=lambda q: (order[rarity_of(ch, ch, q)], POSE_NAMES.get(q, q)))
        self.gal_sig = (cid, tuple(sorted(owned)))
        for c in self.gal_grid.winfo_children():
            c.destroy()
        self.gal_count.config(text=f"已收集 {len(owned & set(poses))}/{len(poses)}")
        cols = 7
        for i, q in enumerate(poses):
            have = q in owned
            r = rarity_of(ch, ch, q)
            cell = tk.Frame(self.gal_grid, bg=C_CARD, padx=2, pady=3)
            cell.grid(row=i // cols, column=i % cols)
            tk.Label(cell, text=r, bg=RARITY_COLOR[r] if have else "#d9cfc7", fg="#ffffff",
                     font=(FONT, 8, "bold"), width=4).pack()
            img = tk.Label(cell, image=self.thumb(ch, q, have), bg="#ffffff", relief="flat",
                           cursor="hand2" if have else "arrow", highlightthickness=1, highlightbackground=C_LINE)
            img.pack()
            tk.Label(cell, text=POSE_NAMES.get(q, q) if have else "？？？", bg=C_CARD,
                     fg=C_TEXT if have else C_MUTED, font=(FONT, 8), width=10).pack()
            if have:
                img.bind("<Button-1>", lambda e, q=q: w.show_card(cid, q))

    # ---------- 紀錄 ----------
    def build_stats(self):
        w = self.w
        f = self.page("紀錄")
        body = self.card(f, "我們的日子")
        self.days_label = self.label(body, "", size=11)
        self.days_label.pack(anchor="w")
        body = self.card(f, "統計")
        self.stat_labels = {}
        for j, head in enumerate(("", "今天", "這週", "全部")):
            self.label(body, head, muted=True, bold=True).grid(row=0, column=j, sticky="w", padx=8)
        for i, (k, name) in enumerate(STAT_NAMES, 1):
            self.label(body, name).grid(row=i, column=0, sticky="w", padx=8, pady=1)
            for j in (1, 2, 3):
                lb = self.label(body, "0", bold=j == 1)
                lb.grid(row=i, column=j, sticky="w", padx=8)
                self.stat_labels[(k, j)] = lb
        body = self.card(f, "好感度")
        self.love_rows = {}
        for i, cid in enumerate(w.base_ids()):
            ch = w.chars[cid]
            img = avatar(ch, 30)
            self.imgs.append(img)
            tk.Label(body, image=img, bg=C_CARD).grid(row=i, column=0, pady=2)
            self.label(body, ch.cfg.get("name", cid), bold=True).grid(row=i, column=1, sticky="w", padx=6)
            t = self.label(body, "", muted=True)
            t.grid(row=i, column=2, sticky="w", padx=6)
            bar = ttk.Progressbar(body, style="Love.Horizontal.TProgressbar", length=160, maximum=100)
            bar.grid(row=i, column=3, padx=6)
            c = self.label(body, "", muted=True, size=9)
            c.grid(row=i, column=4, sticky="w")
            self.love_rows[cid] = (t, bar, c)

    # ---------- 設定 ----------
    def build_settings(self):
        w = self.w
        f = self.page("設定")
        body = self.card(f, "大小")
        self.size_var = tk.StringVar(value=w.settings.get("size", "中"))
        for i, n in enumerate(SIZES):
            ttk.Radiobutton(body, text=n, value=n, variable=self.size_var,
                            command=lambda: w.set_size(self.size_var.get())).grid(row=0, column=i, padx=8, sticky="w")
        body = self.card(f, "她們會做的事")
        flags = [("hourly", "整點提醒喝水"), ("meal", "吃飯提醒"), ("late", "深夜催睡"), ("climb", "爬到視窗上"),
                 ("visit", "會走來找你"), ("watch_app", "看你在做什麼（只在本機判斷）"),
                 ("cling", "撒嬌：會抓你的滑鼠去玩"), ("cling_force", "撒嬌時強制拖走（你動滑鼠也不放手）"),
                 ("quiet", "安靜模式：不主動說話")]
        self.flag_vars = {}
        for i, (k, label) in enumerate(flags):
            v = tk.BooleanVar(value=w.settings.get(k, k not in ("quiet", "cling", "cling_force")))
            self.flag_vars[k] = v
            ttk.Checkbutton(body, text=label, variable=v, command=lambda k=k, v=v: w.toggle(k, v.get())).grid(
                row=i // 2, column=i % 2, padx=6, pady=2, sticky="w")
        body = self.card(f, "你的生日", note="格式 月-日，例如 03-14；當天大家會幫你慶生")
        self.bd = ttk.Entry(body, width=8)
        self.bd.insert(0, w.settings.get("birthday", ""))
        self.bd.grid(row=0, column=0)
        ttk.Button(body, text="儲存", command=self.save_bd).grid(row=0, column=1, padx=6)
        self.bd_msg = self.label(body, "", muted=True)
        self.bd_msg.grid(row=0, column=2, sticky="w")

        body = self.card(f, "今天吃什麼的清單", note="問她「今天吃什麼」時從這裡挑")
        self.food_list = tk.Listbox(body, height=7, bg="#fffaf5", fg=C_TEXT, selectbackground="#ffd9bf",
                                    selectforeground=C_TEXT, relief="flat", highlightthickness=1,
                                    highlightcolor=C_LINE, highlightbackground=C_LINE, font=(FONT, 10))
        self.food_list.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=(0, 8))
        body.columnconfigure(0, weight=1)
        self.food_entry = ttk.Entry(body, width=14)
        self.food_entry.grid(row=0, column=1, sticky="ew")
        self.food_entry.bind("<Return>", lambda e: self.food_add())
        ttk.Button(body, text="新增", style="Accent.TButton", command=self.food_add).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Button(body, text="刪除選取的", command=self.food_del).grid(row=2, column=1, sticky="ew", pady=3)
        ttk.Button(body, text="還原預設", command=self.food_reset).grid(row=3, column=1, sticky="ew", pady=3)
        self.food_fill()

        body = self.card(f, "其他")
        if getattr(sys, "frozen", False):
            self.startup_var = tk.BooleanVar(value=startup_link().exists())
            ttk.Checkbutton(body, text="開機自動啟動", variable=self.startup_var,
                            command=lambda: set_startup(self.startup_var.get())).pack(anchor="w")
        self.label(body, "快捷鍵 Ctrl+Alt+P：全部藏起來／叫回來", muted=True).pack(anchor="w", pady=(4, 0))
        ttk.Button(body, text="全部掰掰（關閉程式）", command=w.quit).pack(anchor="e", pady=(6, 0))

    def save_bd(self):
        v = self.bd.get().strip().replace("/", "-")
        m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", v)
        if v and not (m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31):
            self.bd_msg.config(text="格式不對喔，例如 03-14")
            return
        v = f"{int(m.group(1)):02d}-{int(m.group(2)):02d}" if v else ""
        self.w.settings["birthday"] = v
        self.w.save()
        self.bd_msg.config(text="記住了！" if v else "已清除")

    def food_fill(self):
        self.food_list.delete(0, "end")
        for x in self.w.settings.get("foods") or []:
            self.food_list.insert("end", x)

    def food_add(self):
        t = self.food_entry.get().strip()
        if t and t not in self.w.settings.setdefault("foods", []):
            self.w.settings["foods"].append(t)
            self.w.save()
            self.food_fill()
            self.food_list.see("end")
        self.food_entry.delete(0, "end")

    def food_del(self):
        for i in reversed(self.food_list.curselection()):
            del self.w.settings["foods"][i]
        self.w.save()
        self.food_fill()

    def food_reset(self):
        self.w.settings["foods"] = list(FOODS)
        self.w.save()
        self.food_fill()

    # ---------- 每隻角色 ----------
    def build_char(self, cid):
        w = self.w
        ch = w.chars[cid]
        color = ch.cfg.get("accent") or C_ACCENT
        f = self.page(w.disp_name(cid), key=cid)
        wd = self.cw[cid] = {"frames": []}

        # 名片
        outer = tk.Frame(f, bg=C_LINE)
        outer.pack(fill="x", padx=10, pady=(8, 5))
        card = tk.Frame(outer, bg=C_CARD, padx=12, pady=10)
        card.pack(fill="both", padx=1, pady=1)
        img = avatar(ch, 84)
        self.imgs.append(img)
        tk.Label(card, image=img, bg=C_CARD).grid(row=0, column=0, rowspan=5, padx=(0, 14))
        nm = tk.Frame(card, bg=C_CARD)
        nm.grid(row=0, column=1, columnspan=2, sticky="w")
        tk.Label(nm, text=ch.cfg.get("name", cid), bg=C_CARD, fg=color, font=(FONT, 17, "bold")).pack(side="left")
        wd["title"] = self.label(nm, "", muted=True, size=10)
        wd["title"].pack(side="left", padx=10, pady=(6, 0))
        self.label(card, "好感度", muted=True, size=9).grid(row=1, column=1, sticky="w")
        wd["love"] = ttk.Progressbar(card, style="Love.Horizontal.TProgressbar", length=220, maximum=100)
        wd["love"].grid(row=1, column=2, sticky="w", padx=6)
        wd["love_t"] = self.label(card, "", muted=True, size=9)
        wd["love_t"].grid(row=1, column=3, sticky="w")
        self.label(card, "怒氣", muted=True, size=9).grid(row=2, column=1, sticky="w")
        wd["anger"] = ttk.Progressbar(card, style="Anger.Horizontal.TProgressbar", length=220, maximum=100)
        wd["anger"].grid(row=2, column=2, sticky="w", padx=6)
        wd["anger_t"] = self.label(card, "", muted=True, size=9)
        wd["anger_t"].grid(row=2, column=3, sticky="w")
        wd["unlock"] = self.label(card, "", muted=True, size=9)
        wd["unlock"].grid(row=3, column=1, columnspan=3, sticky="w", pady=(2, 0))
        wd["status"] = self.label(card, "", size=10)
        wd["status"].grid(row=4, column=1, columnspan=2, sticky="w", pady=(4, 0))
        wd["summon"] = ttk.Button(card, text="", style="Accent.TButton",
                                  command=lambda: self.toggle_pet(cid, cid not in w.pets))
        wd["summon"].grid(row=4, column=3, sticky="e", pady=(4, 0))

        body = self.card(f, "名字", color, note="留空就是原本的名字")
        ent = ttk.Entry(body, width=14)
        ent.insert(0, w.settings.get("names", {}).get(cid, ""))
        ent.pack(side="left")

        def rename(e=None):
            v = ent.get().strip()
            names = w.settings.setdefault("names", {})
            if v:
                names[cid] = v
            else:
                names.pop(cid, None)
            w.save()
            self.nb.tab(self.tabs[cid], text=w.disp_name(cid))
        ent.bind("<Return>", rename)
        ttk.Button(body, text="儲存", command=rename).pack(side="left", padx=6)

        body = self.card(f, "互動", color)
        wd["frames"].append(body)
        self.buttons(body, [
            ("摸摸頭", lambda: self.do(cid, lambda p: p.pat())),
            ("餵食", lambda: self.do(cid, w.feed)),
            ("跳一下", lambda: self.do(cid, lambda p: (p.touch(), p.act("happy", 1.4)))),
            ("巨大化", lambda: w.enter_giant(cid)),
            ("貼到左邊", lambda: self.do(cid, lambda p: p.char.has("edge_left") and p.enter_edge("left"))),
            ("貼到右邊", lambda: self.do(cid, lambda p: p.char.has("edge_right") and p.enter_edge("right"))),
            ("回到地上", lambda: self.do(cid, lambda p: (p.leave_edge() if p.state == "edge" else (p.to_ground(), p.idle())))),
            ("撒嬌", lambda: self.do(cid, w.mischief)),
            ("說說話", lambda: self.do(cid, w.chat)),
            ("講專業話題", lambda: self.do(cid, lambda p: w.talk_topic(p, force=True))),
        ], cols=4)
        wd["follow"] = tk.BooleanVar()
        ttk.Checkbutton(body, text="跟著滑鼠走", variable=wd["follow"],
                        command=lambda: self.do(cid, w.toggle_follow)).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        body = self.card(f, "跟她玩", color)
        wd["frames"].append(body)
        def game(i):
            def run():
                p = self.pet(cid)
                if p:
                    label, fn, secs = [g for g in w.game_list(p) if g[0] != "-"][i]
                    w.enqueue(p, fn, secs)
            return run
        names = [g[0] for g in w.game_list(None) if g[0] != "-"]
        self.buttons(body, [(n.replace("猜拳：出", "猜拳："), game(i)) for i, n in enumerate(names)], cols=4)

        body = self.card(f, "惹她生氣", C_RED, note="怒氣滿了會賭氣不理你，要餵她吃東西才會消氣")
        wd["frames"].append(body)
        self.buttons(body, [("戳一下", lambda: self.do(cid, lambda p: p.poke()))] +
                     [(label, lambda key=key, amt=amt, pose=pose: self.do(cid, lambda p: p.tease(key, amt, pose)))
                      for label, key, amt, pose in TEASES], cols=3, style="Mean.TButton")

        body = self.card(f, "做個動作", color)
        wd["frames"].append(body)
        poses = [q for q in ch.poses if not q.startswith("edge_") and q != "idle-blink"]
        poses.sort(key=lambda q: (q.startswith(("greet_", "fest_")), list(POSE_NAMES).index(q) if q in POSE_NAMES else 999))
        self.buttons(body, [(POSE_NAMES.get(q, q), lambda q=q: self.do(cid, lambda p: w.do_pose(p, q)))
                            for q in poses], cols=5)

        skins = w.skins_of(cid)
        if len(skins) > 1:
            body = self.card(f, "換衣服", color)
            wd["frames"].append(body)
            wd["outfit"] = tk.StringVar(value=w.settings["outfits"].get(cid, cid))
            for i, sk in enumerate(skins):
                ttk.Radiobutton(body, text=w.chars[sk].cfg.get("skinName", "原本的衣服"), value=sk, variable=wd["outfit"],
                                command=lambda sk=sk: self.do(cid, lambda p: w.change_outfit(p, sk))).grid(
                    row=0, column=i, padx=6)

        body = self.card(f, "提醒我、讓她說", color)
        wd["frames"].append(body)
        for i, m in enumerate((5, 10, 25, 60)):
            ttk.Button(body, text=f"{m} 分鐘後", command=lambda m=m: self.do(cid, lambda p: w.remind_in(p, m))).grid(
                row=0, column=i, padx=3, sticky="ew")
            body.columnconfigure(i, weight=1)
        ent = ttk.Entry(body)
        ent.grid(row=1, column=0, columnspan=3, sticky="ew", padx=3, pady=(8, 0))

        def speak(e=None):
            t = ent.get().strip()
            if t:
                self.do(cid, lambda p: (p.act("happy", 2), p.say(text=t, force=True, secs=4)))
                ent.delete(0, "end")
        ent.bind("<Return>", speak)
        ttk.Button(body, text="讓她說", style="Accent.TButton", command=speak).grid(row=1, column=3, padx=3, pady=(8, 0), sticky="ew")

    # ---------- 顯示、更新 ----------
    def show(self, cid=None):
        if self.job:
            self.top.after_cancel(self.job)
            self.job = None
        self.top.deiconify()
        self.top.lift()
        self.nb.select(self.tabs.get(cid) or self.tabs["大家"])
        self.ensure_current()
        self.refresh()

    def set_state(self, widget, enabled):
        for c in widget.winfo_children():
            try:
                c.state(["!disabled"] if enabled else ["disabled"])
            except (AttributeError, tk.TclError):
                pass
            self.set_state(c, enabled)

    def refresh(self):
        try:
            if not self.top.winfo_exists():
                return
        except tk.TclError:
            return
        w = self.w
        for cid, v in self.summon_vars.items():
            v.set(cid in w.pets)
        if w.study:
            left = max(0, int((w.study - time.time()) // 60) + 1)
            self.study_btn.config(text=f"陪讀中・剩 {left} 分（按這裡結束）")
        else:
            self.study_btn.config(text="陪讀 25 分鐘")
        for cid, wd in self.cw.items():
            p = w.pets.get(cid)
            v, lo, hi = w.love_progress(cid)
            lv = w.love_level(cid)
            wd["title"].config(text=f"Lv{lv}・{w.love_title(cid)}")
            wd["love"]["value"] = 100 if hi is None else (v - lo) / max(1, hi - lo) * 100
            wd["love_t"].config(text=f"{v}" + (f"/{hi}" if hi else "（MAX）"))
            wd["unlock"].config(text=w.next_unlock(cid))
            anger = p.anger if p else 0
            wd["anger"]["value"] = anger
            lvname = {"annoyed": "不耐煩", "puffed": "鼓臉", "redhot": "氣炸了"}.get(p.anger_level() if p else None, "")
            wd["anger_t"].config(text=("賭氣中" if p and p.sulking else lvname) or ("平靜" if p else ""))
            if p:
                st = STATE_NAMES.get(p.state, p.state)
                full = p.belly / p.stomach()
                if full > .2:
                    st += "・" + ("吃不下了" if p.is_full() else "有點飽" if full < .6 else "很飽")
                if p.plat:
                    st += "・站在視窗上"
                if p.giant:
                    st = "巨大化中"
                wd["status"].config(text=f"在桌面上・{st}")
                wd["summon"].config(text="讓她回家")
            else:
                wd["status"].config(text="還在家裡")
                wd["summon"].config(text="叫她出來")
            if wd.get("here") != (p is not None):
                wd["here"] = p is not None
                for fr in wd["frames"]:
                    self.set_state(fr, p is not None)
            if p:
                wd["follow"].set(p.follow)
                if "outfit" in wd:
                    wd["outfit"].set(p.char.id)
        # 紀錄（建好才更新）
        if not hasattr(self, "days_label"):
            self.refresh_tail()
            return
        ci = w.settings.get("checkin", {})
        try:
            days = (datetime.date.today() - datetime.date.fromisoformat(w.settings.get("first_day"))).days + 1
        except (TypeError, ValueError):
            days = 1
        self.days_label.config(text=f"認識第 {days} 天　・　簽到 {ci.get('total', 0)} 天　・　連續 {ci.get('streak', 0)} 天")
        sums = {1: w.stat_sum(1), 2: w.stat_sum(7), 3: w.stat_sum()}
        for (k, j), lb in self.stat_labels.items():
            lb.config(text=str(sums[j].get(k, 0)))
        for cid, (t, bar, c) in self.love_rows.items():
            v, lo, hi = w.love_progress(cid)
            t.config(text=f"Lv{w.love_level(cid)} {w.love_title(cid)}")
            bar["value"] = 100 if hi is None else (v - lo) / max(1, hi - lo) * 100
            total = len(card_poses(w.chars[cid]))
            c.config(text=f"卡片 {len(w.settings.get('cards', {}).get(cid, []))}/{total}")
        self.refresh_tail()

    def refresh_tail(self):
        w = self.w
        if hasattr(self, "todo_body"):
            self.refresh_todos()
        if hasattr(self, "gal_pick"):
            cid = self.gal_names.get(self.gal_pick.get())
            if cid and self.gal_sig != (cid, tuple(sorted(w.settings.get("cards", {}).get(cid, [])))):
                self.gallery_fill()
        self.job = self.top.after(700, self.refresh) if self.top.state() != "withdrawn" else None


def startup_link():
    import os
    return Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/DesktopPet.lnk"


def set_startup(on):
    link = startup_link()
    if on:
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
              f"$s.TargetPath='{sys.executable}';$s.WorkingDirectory='{BASE}';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
    elif link.exists():
        link.unlink()


def main():
    kernel32.CreateMutexW(None, False, "DesktopPet_single_instance")
    if kernel32.GetLastError() == 183:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        w = World()
        w.run()
    except Exception:
        log_error()
        raise


if __name__ == "__main__":
    main()
