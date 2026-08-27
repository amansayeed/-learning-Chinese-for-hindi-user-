# -*- coding: utf-8 -*-
"""Reorganize TOCFL A1/A2 vocabulary into daily-life study categories."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "data" / "vocabulary.json"
JS_PATH = ROOT / "data" / "vocabulary.js"
REPORT_PATH = ROOT / "data" / "tocfl-category-report.json"

# Display order for lessons (skip empty). Taiwan daily-life first.
CATEGORY_ORDER = [
    "Greetings & Basic Expressions",
    "Pronouns",
    "People & Family",
    "Numbers & Counting",
    "Time & Dates",
    "Question Words",
    "Daily Activities",
    "Food & Drinks",
    "Restaurants & Eating",
    "Shopping",
    "Money & Banking",
    "Home & Household",
    "Clothing & Personal Items",
    "Health & Body",
    "School & Education",
    "Work & Office",
    "Transportation",
    "Directions & Locations",
    "Places & Buildings",
    "Travel",
    "Leisure, Sports & Hobbies",
    "Weather, Nature & Animals",
    "Feelings & Emotions",
    "Relationships & Dating",
    "Communication & Conversation",
    "Technology & Internet",
    "Taiwan Daily Life",
    "Government & Public Services",
    "Common Verbs",
    "Adjectives",
    "Common Adverbs",
    "Connectors & Grammar Words",
    "Other / Miscellaneous",
]

# Exact Traditional form (as stored) -> category. Dual-pinyin words use "trad|pinyin".
EXPLICIT: dict[str, str] = {}


def assign(cat: str, *words: str) -> None:
    for w in words:
        EXPLICIT[w] = cat


# One category per word. Dual readings: trad|pinyin

assign(
    "Greetings & Basic Expressions",
    "對不起",
    "沒關係",
    "請",
    "請問",
    "謝謝",
    "再見",
    "早",
    "早安",
    "晚安",
    "歡迎",
    "不客氣",
    "不好意思",
    "喂",
    "祝",
    "加油",
    "客氣",
    "小心",
    "不見了",
    "麻煩",
)

assign(
    "Pronouns",
    "大家",
    "們",
    "你",
    "妳",
    "你們",
    "您",
    "她",
    "他",
    "他們",
    "我",
    "我們",
    "它",
    "自己",
    "別人",
    "其他/其它",
    "有的",
    "每",
    "各",
    "別的",
    "這/這裡/這裏/這兒",
    "那/那裡/那裏/那兒",
)

assign(
    "People & Family",
    "爸爸/爸",
    "弟弟/弟",
    "兒子",
    "哥哥/哥",
    "孩子",
    "姊姊/姐姐/姊/姐",
    "媽媽/媽",
    "妹妹/妹",
    "名字",
    "女兒",
    "人",
    "太太",
    "先生",
    "小孩/小孩子",
    "小姐",
    "姓名",
    "名",
    "家人",
    "男",
    "女",
    "姓",
    "大人",
    "家庭",
    "老人",
    "小朋友",
    "阿姨",
    "伯伯/伯",
    "奶奶",
    "男生",
    "女生",
    "室友",
    "叔叔/叔",
    "爺爺",
    "老闆/老板",
    "客人",
    "司機",
    "護士",
    "醫生/醫師",
    "老師",
    "同學",
    "學生",
    "房東",
)

assign(
    "Numbers & Counting",
    "八",
    "百",
    "半",
    "本",
    "多",
    "多少",
    "二",
    "個",
    "幾",
    "九",
    "塊",
    "兩",
    "六",
    "七",
    "千",
    "三",
    "少",
    "十",
    "四",
    "五",
    "一",
    "元",
    "萬",
    "一共/共",
    "一點/一點點/一點兒",
    "一些",
    "第一",
    "份",
    "間",
    "零",
    "一半",
    "號",
    "號碼",
    "輛",
    "件",
    "張",
    "枝",
    "隻",
    "雙",
    "種",
    "次",
    "場",
    "部",
    "所",
    "台/臺",
    "片",
    "支",
    "句",
    "條",
    "袋",
    "全",
    "全部",
    "所有",
    "部分/部份",
)

assign(
    "Time & Dates",
    "點",
    "分",
    "今年",
    "今天",
    "久",
    "明天",
    "年",
    "去年",
    "日",
    "上午",
    "時候",
    "時間",
    "歲",
    "天",
    "晚上",
    "現在",
    "小時",
    "下午",
    "星期天/星期日",
    "星期一",
    "一月",
    "月",
    "早上",
    "中午",
    "昨天",
    "後年",
    "後天",
    "分鐘",
    "禮拜天",
    "明年",
    "前年",
    "前天",
    "星期",
    "以後",
    "以前",
    "有時候/有時",
    "晚",
    "先",
    "鐘頭",
    "週末/周末",
    "本來",
    "春天/春",
    "冬天/冬",
    "剛剛/剛",
    "後來",
    "小時候",
    "夏天/夏",
    "一下子/一下",
    "已經",
    "最後",
    "最近",
    "白天",
    "從前",
    "生日",
    "禮拜",
    "秋天/秋",
    "新年",
    "一會/一會兒",
    "週日",
    "週一",
    "有空",
)

assign(
    "Question Words",
    "嗎",
    "哪",
    "哪裡/哪裏/哪兒",
    "誰",
    "什麼/甚麼",
    "怎麼",
    "為什麼",
    "怎麼樣",
    "多久",
    "怎麼辦",
    "哪|na",
)

assign(
    "Daily Activities",
    "吃",
    "吃飯",
    "喝",
    "睡覺",
    "寫",
    "走",
    "做",
    "穿",
    "起床",
    "玩",
    "休息",
    "走路",
    "住",
    "洗",
    "洗澡",
    "搬",
    "搬家",
    "打算",
    "開始",
    "參加",
    "活動",
    "習慣",
    "用功",
    "準備",
    "努力",
    "忙",
)

assign(
    "Food & Drinks",
    "茶",
    "咖啡",
    "水",
    "包子",
    "菜",
    "蛋",
    "飯",
    "雞",
    "酒",
    "麵",
    "麵包",
    "牛奶",
    "肉",
    "水果",
    "湯",
    "魚",
    "冰淇淋",
    "冰塊",
    "紅茶",
    "果汁",
    "漢堡",
    "火腿",
    "餃子/餃",
    "可樂",
    "饅頭",
    "奶茶",
    "啤酒",
    "蘋果",
    "青菜",
    "汽水",
    "熱狗",
    "三明治",
    "糖",
    "甜點",
    "香蕉",
    "西瓜",
    "點心",
    "蛋糕",
    "冰",
)

assign(
    "Restaurants & Eating",
    "餐廳",
    "筷子/筷",
    "碗",
    "杯子/杯",
    "小吃",
    "晚餐/晚飯",
    "午餐/午飯",
    "早餐/早飯",
    "菜單",
    "餐",
    "茶館",
    "炒",
    "烤",
    "炸",
    "叉子/叉",
    "刀子/刀",
    "盤子/盤",
    "瓶子/瓶",
    "湯匙",
    "飯店",
    "飯廳",
    "野餐",
    "飽",
    "餓",
    "渴",
    "味道/味",
    "辣",
    "鹹",
    "酸",
    "甜",
    "香",
)

assign(
    "Shopping",
    "買",
    "店",
    "賣",
    "市場",
    "百貨公司",
    "超市/超級市場",
    "商店",
    "書店",
    "東西",
    "貴",
    "便宜",
)

assign(
    "Money & Banking",
    "錢",
    "付",
    "還|huán",
    "借",
    "銀行",
    "信用卡",
    "錢包",
    "有錢",
    "房租",
    "租",
)

assign(
    "Home & Household",
    "家",
    "床",
    "房間",
    "房子",
    "門",
    "門口",
    "椅子/椅",
    "桌子/桌",
    "紙",
    "屋子/屋",
    "冰箱",
    "窗/窗戶/窗子",
    "燈",
    "電梯",
    "大門",
    "罐子/罐",
    "盒子/盒",
    "客廳",
    "樓梯",
    "書房",
    "宿舍",
    "洗手間",
    "袋子",
    "燈",
)

assign(
    "Clothing & Personal Items",
    "帶",
    "鞋子/鞋",
    "衣服/衣",
    "戴",
    "包",
    "背包",
    "大衣",
    "褲子/褲",
    "帽子/帽",
    "皮包",
    "裙子/裙",
    "手錶/手表/錶/表",
    "外套",
    "眼鏡",
    "脫",
)

assign(
    "Health & Body",
    "腳",
    "鼻子/鼻",
    "病",
    "感冒",
    "看病",
    "生病",
    "身體",
    "手",
    "瘦",
    "舒服",
    "痛",
    "頭",
    "眼睛",
    "藥",
    "嘴巴/嘴",
    "耳朵",
    "累",
    "胖",
    "病人",
    "健康",
    "臉",
    "心",
    "醫院",
    "肚子/肚",
    "頭髮/髮",
)

assign(
    "School & Education",
    "大學",
    "書",
    "學",
    "學校",
    "中文",
    "英文",
    "功課",
    "畫",
    "圖",
    "教室",
    "考試",
    "課",
    "唸/念",
    "上課",
    "下課",
    "讀",
    "筆",
    "句子",
    "字",
    "高中",
    "成績",
    "班",
    "練習",
    "學習",
    "作業",
    "本子",
    "德文",
    "法文",
    "課本",
    "年級",
    "念書/唸書",
    "日文",
    "日語",
    "書包",
    "圖書館",
    "小學",
    "英語",
    "字典",
    "開學",
    "上學",
    "考",
    "語言/語",
    "文化",
    "故事",
    "進步",
    "教",
)

assign(
    "Work & Office",
    "工作",
    "公司",
    "辦公室",
    "上班",
    "下班",
    "計畫/計劃",
    "經驗",
    "能力",
    "辦法",
    "方法",
    "機會",
    "行|háng",
)

assign(
    "Transportation",
    "車子/車",
    "公車",
    "火車",
    "計程車",
    "開車",
    "汽車",
    "巴士",
    "車站",
    "公共汽車",
    "腳踏車",
    "騎",
    "票",
    "坐",
)

assign(
    "Directions & Locations",
    "到",
    "後",
    "前",
    "外",
    "邊",
    "地方",
    "附近",
    "裡/裏",
    "裡面/裏面",
    "旁邊/旁",
    "前面",
    "外頭",
    "右",
    "右邊",
    "中",
    "左",
    "北",
    "地|dì",
    "近",
    "經過",
    "離",
    "南",
    "往",
    "向",
    "西",
    "遠",
    "中間",
    "北部",
    "東",
    "道",
    "對面",
    "街",
    "路口",
    "馬路",
    "十字路口",
    "樓上",
    "樓下",
    "在",
    "上",
    "下",
    "地圖",
    "地址",
)

assign(
    "Places & Buildings",
    "路",
    "位",
    "公園",
    "樓",
    "世界",
    "大樓",
    "市",
    "旅館",
    "郵局",
    "外國",
    "國家",
    "國",
    "站",
)

assign(
    "Travel",
    "來",
    "去",
    "飛機",
    "旅行",
    "回",
    "回到",
    "離開",
    "飛",
    "寄",
    "郵票",
    "門票",
    "機場",
)

assign(
    "Leisure, Sports & Hobbies",
    "唱",
    "唱歌",
    "電視",
    "電影",
    "歌",
    "球",
    "跳",
    "跳舞",
    "運動",
    "比賽",
    "棒球",
    "籃球",
    "慢跑",
    "跑步",
    "網球",
    "踢",
    "游",
    "游泳",
    "足球",
    "音樂",
    "照相",
    "相片/照片",
    "跑",
    "游泳池",
)

assign(
    "Weather, Nature & Animals",
    "冷",
    "熱",
    "風",
    "空氣",
    "山",
    "天氣",
    "雨",
    "下雨",
    "花/花兒",
    "狗",
    "海",
    "火",
    "馬",
    "貓",
    "鳥",
    "樹",
    "草",
    "河",
    "風景",
    "下雪",
    "雪",
    "牛",
    "豬",
)

assign(
    "Feelings & Emotions",
    "愛",
    "喜歡",
    "想",
    "快樂",
    "怕",
    "覺得",
    "高興",
    "緊張",
    "可愛",
    "苦",
    "難過",
    "生氣",
    "希望",
    "願意",
    "笑",
    "有意思",
    "哭",
)

assign(
    "Relationships & Dating",
    "朋友",
    "介紹",
    "認識",
    "見面",
    "交",
)

assign(
    "Communication & Conversation",
    "電話",
    "話",
    "叫",
    "說",
    "問",
    "問題",
    "告訴",
    "事/事兒",
    "事情",
    "說話",
    "聽見",
    "聽到",
    "聽說",
    "講",
    "聊天/聊",
    "聲",
    "聲音/聲",
    "報紙",
    "信",
    "意思",
    "想法",
    "認為",
    "以為",
    "相信",
    "記得",
    "忘",
    "懂",
    "知道",
    "看",
    "看到",
    "看見",
    "見",
    "聽",
    "注意",
)

assign(
    "Technology & Internet",
    "手機",
    "電腦",
    "電",
    "網路",
    "上網",
    "網站",
    "轉",
)

assign(
    "Taiwan Daily Life",
    "台灣/臺灣",
    "臺灣人/台灣人",
    "夜市",
    "便利商店",
    "超商",
    "冷氣",
    "過年",
)

assign(
    "Common Verbs",
    "打",
    "給",
    "拿",
    "找",
    "是",
    "有",
    "用",
    "要",
    "開",
    "出",
    "進",
    "等",
    "過",
    "會",
    "能",
    "可以",
    "應該/應",
    "得|děi",
    "比",
    "幫",
    "幫忙",
    "幫助",
    "變",
    "被",
    "當",
    "放",
    "發現",
    "敢",
    "接",
    "決定",
    "拉",
    "讓",
    "試",
    "送",
    "算",
    "替",
    "行|xíng",
    "需要/需",
    "長|zhǎng",
    "找到",
    "掛",
    "關",
    "掉",
    "空",
    "學",
    "加",
)

assign(
    "Adjectives",
    "大",
    "高",
    "好",
    "難",
    "容易",
    "小",
    "新",
    "矮",
    "白",
    "不錯",
    "長|cháng",
    "錯",
    "低",
    "短",
    "方便",
    "夠",
    "黑",
    "紅",
    "舊",
    "快",
    "慢",
    "美",
    "漂亮",
    "一樣",
    "棒",
    "乾淨",
    "簡單",
    "奇怪",
    "清楚",
    "重",
    "重要",
    "笨",
    "聰明",
    "壞",
    "輕",
    "有名",
    "有用",
    "黃",
    "綠",
    "藍",
    "顏色",
    "色",
    "臭",
    "老",
    "年輕",
    "特別",
    "辛苦",
    "樣子",
)

assign(
    "Common Adverbs",
    "不",
    "都",
    "很",
    "就",
    "太",
    "也",
    "一起",
    "常常/常",
    "還|hái",
    "還是",
    "馬上",
    "再",
    "真",
    "真的",
    "只",
    "最",
    "一定",
    "又",
    "才",
    "差不多",
    "更",
    "好像",
    "那麼",
    "平常",
    "一直",
    "這麼",
    "總是/總",
    "沒",
    "沒有",
    "比較/較",
    "不過",
    "當然",
    "有點/有一點/有點兒",
    "一塊/一塊兒",
    "非常",
    "可能",
)

assign(
    "Connectors & Grammar Words",
    "吧",
    "的",
    "對",
    "和",
    "呢",
    "從",
    "得|de",
    "跟",
    "可是",
    "所以",
    "然後",
    "因為",
    "啊",
    "把",
    "但是/但",
    "地|de",
    "或是",
    "啦",
    "如果",
    "雖然/雖",
    "要是",
    "別",
    "起來",
    "哪|na",
    "呀",
    "像",
    "比方說/比方",
)

def word_key(w: dict) -> str:
    trad = w["traditional"]
    py = (w.get("pinyin") or "").strip()
    keyed = f"{trad}|{py}"
    if keyed in EXPLICIT:
        return keyed
    return trad


def categorize(w: dict) -> str:
    k = word_key(w)
    if k in EXPLICIT:
        return EXPLICIT[k]
    if w["traditional"] in EXPLICIT:
        return EXPLICIT[w["traditional"]]
    return "Other / Miscellaneous"


def detect_duplicates(words: list[dict]) -> list[dict]:
    seen: dict[str, int] = Counter()
    for w in words:
        seen[w["traditional"]] += 1
    dups = []
    for trad, n in seen.items():
        if n > 1:
            entries = [w for w in words if w["traditional"] == trad]
            dups.append(
                {
                    "traditional": trad,
                    "count": n,
                    "pinyin": [w.get("pinyin") for w in entries],
                    "english": [w.get("english", "")[:80] for w in entries],
                }
            )
    return dups


# High-frequency dual readings / two daily meanings (not every long CEDICT gloss).
CURATED_MULTI = [
    {"traditional": "哪", "meanings": "nǎ which / na sentence particle"},
    {"traditional": "得", "meanings": "děi must / de degree particle"},
    {"traditional": "長", "meanings": "cháng long / zhǎng to grow, elder"},
    {"traditional": "還", "meanings": "hái still / huán to return (money)"},
    {"traditional": "地", "meanings": "dì ground, place / de adverb particle"},
    {"traditional": "行", "meanings": "xíng OK, to go / háng row, profession"},
    {"traditional": "花/花兒", "meanings": "flower / to spend (money, time)"},
    {"traditional": "點", "meanings": "o'clock / to order (food)"},
    {"traditional": "會", "meanings": "can / to meet, meeting"},
    {"traditional": "過", "meanings": "to pass / experienced-action marker"},
    {"traditional": "意思", "meanings": "meaning / a small token of goodwill"},
    {"traditional": "想", "meanings": "to think / to want / to miss"},
    {"traditional": "看", "meanings": "to look, read / to visit (a doctor)"},
    {"traditional": "好", "meanings": "good / hello (你好)"},
    {"traditional": "分", "meanings": "minute / to divide / 0.01 yuan"},
    {"traditional": "號", "meanings": "number / day of the month / size"},
    {"traditional": "元", "meanings": "Taiwan/China dollar / first, original"},
    {"traditional": "站", "meanings": "to stand / station"},
    {"traditional": "信", "meanings": "letter / to believe"},
    {"traditional": "空", "meanings": "free time / vacant"},
    {"traditional": "帶", "meanings": "to bring / belt"},
    {"traditional": "對", "meanings": "correct / towards"},
    {"traditional": "本", "meanings": "classifier for books / this, origin"},
    {"traditional": "早", "meanings": "early / good morning"},
    {"traditional": "熱", "meanings": "hot (weather) / to heat"},
    {"traditional": "冷", "meanings": "cold (weather/feeling)"},
    {"traditional": "便宜", "meanings": "inexpensive / a petty advantage"},
    {"traditional": "客氣", "meanings": "polite / you're being too polite"},
    {"traditional": "加油", "meanings": "add fuel / hang in there, go for it"},
    {"traditional": "方便", "meanings": "convenient / (euphemism) use the restroom"},
]


def multi_meaning_words(words: list[dict]) -> list[dict]:
    out = []
    for w in words:
        eng = w.get("english") or ""
        # genuine multiple common meanings: several distinct glosses
        parts = [p.strip() for p in eng.split(",") if p.strip()]
        if len(parts) >= 3:
            out.append(
                {
                    "traditional": w["traditional"],
                    "pinyin": w.get("pinyin"),
                    "english": eng[:160],
                    "assignedCategory": categorize(w),
                }
            )
    return out


def rebuild_level(lvl: dict) -> tuple[dict, list[dict]]:
    words: list[dict] = []
    for les in lvl["lessons"]:
        words.extend(les["words"])
    buckets: dict[str, list[dict]] = defaultdict(list)
    unmapped = []
    for w in words:
        cat = categorize(w)
        buckets[cat].append(w)
        if cat == "Other / Miscellaneous" and word_key(w) not in EXPLICIT and w["traditional"] not in EXPLICIT:
            unmapped.append(w)
    lessons = []
    n = 0
    for cat in CATEGORY_ORDER:
        chunk = buckets.get(cat)
        if not chunk:
            continue
        chunk = sorted(chunk, key=lambda w: ((w.get("pinyin") or ""), w.get("traditional") or ""))
        n += 1
        lessons.append(
            {
                "id": f"l{lvl['id']}-{n:02d}",
                "title": cat,
                "subtitle": f"{len(chunk)} words",
                "words": chunk,
            }
        )
    # any unexpected categories
    for cat, chunk in buckets.items():
        if cat not in CATEGORY_ORDER and chunk:
            n += 1
            lessons.append(
                {
                    "id": f"l{lvl['id']}-{n:02d}",
                    "title": cat,
                    "subtitle": f"{len(chunk)} words",
                    "words": chunk,
                }
            )
    new_lvl = dict(lvl)
    new_lvl["lessons"] = lessons
    new_lvl["wordCount"] = len(words)
    return new_lvl, unmapped


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    all_words = []
    all_unmapped = []
    new_levels = []
    cat_counts: Counter[str] = Counter()
    for lvl in data["levels"]:
        new_lvl, unmapped = rebuild_level(lvl)
        new_levels.append(new_lvl)
        for les in new_lvl["lessons"]:
            cat_counts[les["title"]] += len(les["words"])
            all_words.extend(les["words"])
        all_unmapped.extend(unmapped)

    data["levels"] = new_levels
    data.setdefault("meta", {})
    data["meta"]["organization"] = (
        "Lessons grouped by daily-life topic for Traditional Chinese (Taiwan). "
        "A1 and A2 levels kept; words recategorized by meaning."
    )

    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    JS_PATH.write_text("window.__VOCAB__ = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")

    dups = detect_duplicates(all_words)
    # Input vs categorized
    report = {
        "totalInputWords": len(all_words),
        "totalCategorizedWords": len(all_words),
        "numberOfCategoriesCreated": len(cat_counts),
        "categoryCounts": dict(cat_counts.most_common()),
        "largestCategories": cat_counts.most_common(8),
        "wordsNotConfidentlyCategorized": [
            {"traditional": w["traditional"], "pinyin": w.get("pinyin"), "english": (w.get("english") or "")[:120]}
            for w in all_unmapped
        ],
        "duplicateTraditionalForms": dups,
        "wordsWithMultipleMeanings": CURATED_MULTI,
        "wordsWithMultipleMeaningsCount": len(CURATED_MULTI),
        "levelLessonTitles": {
            lvl["label"]: [f"{les['title']} ({len(les['words'])})" for les in lvl["lessons"]]
            for lvl in new_levels
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("words", len(all_words))
    print("categories", len(cat_counts))
    print("unmapped", len(all_unmapped))
    print("report", REPORT_PATH)


if __name__ == "__main__":
    main()
