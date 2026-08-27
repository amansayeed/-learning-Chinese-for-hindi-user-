#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the canonical, fully accounted vocabulary dataset.

The builder intentionally uses only the Python standard library.  HSK 3.0
membership comes exclusively from New-HSK-Combined-Word-List.csv; the level
JSON files supply translations, traditional forms, and provenance.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT_JSON = DATA / "vocabulary-master.json"
OUT_JS = DATA / "vocabulary-master.js"
OUT_REPORT = DATA / "vocabulary-master-report.json"
POS_PATH = DATA / "external" / "hsk-complete.json"
CSV_PATH = (
    DATA
    / "new-hsk-csv-master"
    / "new-hsk-csv-master"
    / "data"
    / "csv"
    / "New-HSK-Combined-Word-List.csv"
)

JSON_SOURCES = [
    ("tocfl", DATA / "vocabulary.json"),
    ("nhm1000", DATA / "nhm-1000-common.json"),
    *[(f"hsk{level}", DATA / f"hsk-{level}.json") for level in range(1, 7)],
]
REQUIRED_WORD_FIELDS = ("traditional", "simplified", "pinyin", "english", "hindi")

ANNOTATION_RE = re.compile(r"[（(][^）)]*[）)]")
SPACE_RE = re.compile(r"\s+")
NON_PINYIN_RE = re.compile(r"[^a-züāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿ/]+")

CATEGORY_ORDER = [
    "Greetings & Introductions", "Basic Expressions", "Questions & Answers",
    "Conversation", "Polite Expressions", "Pronouns", "Family",
    "People & Occupations", "Friends & Social Life", "Dating & Relationships",
    "Daily Activities", "Home & Household", "Personal Items", "Clothing",
    "Personal Care", "Food", "Drinks", "Cooking", "Restaurants & Ordering Food",
    "Shopping", "Money & Prices", "Banking & Payments", "Work & Office",
    "Business", "School & Education", "Computers & Technology", "Transportation",
    "Directions & Locations", "Travel & Hotels", "Airports & Flights", "Body",
    "Health", "Hospital & Medicine", "Emergency & Safety", "Weather", "Nature",
    "Animals", "Places & Buildings", "City & Community",
    "Government & Public Services", "Numbers", "Time", "Dates & Calendar",
    "Frequency", "Common Verbs", "Adjectives", "Adverbs", "Measure Words",
    "Question Words", "Conjunctions & Connectors", "Prepositions",
    "Grammar & Function Words", "Abstract Concepts", "Emotions & Personality",
    "Society & Culture", "Politics & Government", "Economy & Finance", "Science",
    "Environment", "Media & News", "Academic Vocabulary",
    "Professional Vocabulary", "Taiwan Daily Life", "Taiwan Transportation",
    "Taiwan Food", "Taiwan Shopping", "Taiwan Work & Office",
    "Taiwan Services & Government", "Other / Miscellaneous",
]

SEED_CATEGORY_MAP = {
    "Greetings & Basic Expressions": "Basic Expressions",
    "People & Family": "Family",
    "Numbers & Counting": "Numbers",
    "Time & Dates": "Time",
    "Food & Drinks": "Food",
    "Restaurants & Eating": "Restaurants & Ordering Food",
    "Money & Banking": "Banking & Payments",
    "Clothing & Personal Items": "Clothing",
    "Health & Body": "Health",
    "Travel": "Travel & Hotels",
    "Leisure, Sports & Hobbies": "Friends & Social Life",
    "Weather, Nature & Animals": "Nature",
    "Feelings & Emotions": "Emotions & Personality",
    "Relationships & Dating": "Dating & Relationships",
    "Communication & Conversation": "Conversation",
    "Technology & Internet": "Computers & Technology",
    "Common Adverbs": "Adverbs",
    "Connectors & Grammar Words": "Grammar & Function Words",
}

# Ordered rules are deterministic.  Chinese terms provide precision where an
# English gloss is ambiguous; English terms provide broad coverage.
CATEGORY_RULES = [
    ("Greetings & Introductions", ("hello", "goodbye", "introduce", "name", "你好", "再见", "再見", "姓名", "名字")),
    ("Polite Expressions", ("thank", "sorry", "please", "excuse me", "welcome", "谢谢", "謝謝", "请", "請", "對不起", "对不起", "客气", "客氣")),
    ("Questions & Answers", ("answer", "reply", "question", "回答", "答案", "问题", "問題")),
    ("Conversation", ("say", "speak", "tell", "ask", "chat", "conversation", "说", "說", "问", "問", "话", "話", "聊")),
    ("Basic Expressions", ("expression", "interjection", "yes", "no", "okay", "certainly", "of course", "是", "不是", "好")),
    ("Pronouns", ("pronoun", " i ", "you", "he", "she", "we", "they", "我", "你", "您", "他", "她", "它", "自己")),
    ("Question Words", ("question", "what", "which", "who", "where", "when", "why", "how", "什么", "誰", "谁", "哪", "怎么", "為什麼", "为什么")),
    ("Family", ("family", "father", "mother", "parent", "brother", "sister", "husband", "wife", "son", "daughter", "爸爸", "妈妈", "媽媽", "哥哥", "姐姐", "孩子")),
    ("People & Occupations", ("person", "people", "worker", "teacher", "doctor", "driver", "manager", "profession", "occupation", "人", "者", "员", "員", "师", "師")),
    ("Friends & Social Life", ("friend", "guest", "party", "social", "visit", "朋友", "客人", "聚会", "聚會")),
    ("Dating & Relationships", ("relationship", "date", "marry", "wedding", "boyfriend", "girlfriend", "结婚", "結婚", "恋爱", "戀愛")),
    ("Daily Activities", ("wake", "sleep", "wash", "rest", "daily", "get up", "睡", "起床", "洗澡", "休息")),
    ("Home & Household", ("home", "house", "room", "kitchen", "bedroom", "furniture", "door", "window", "家", "房", "厨房", "廚房", "门", "門", "窗")),
    ("Personal Items", ("bag", "wallet", "key", "umbrella", "watch", "personal item", "包", "钥匙", "鑰匙", "伞", "傘")),
    ("Clothing", ("clothes", "shirt", "shoe", "hat", "wear", "dress", "pants", "衣", "鞋", "帽", "穿", "裤", "褲")),
    ("Personal Care", ("bathe", "shower", "tooth", "haircut", "makeup", "洗澡", "牙", "头发", "頭髮")),
    ("Food", ("food", "rice", "fruit", "vegetable", "meat", "bread", "egg", "fish", "吃", "饭", "飯", "菜", "肉", "蛋", "鱼", "魚")),
    ("Drinks", ("drink", "tea", "coffee", "water", "juice", "beer", "喝", "茶", "咖啡", "水", "果汁", "酒")),
    ("Cooking", ("cook", "boil", "fry", "bake", "roast", "kitchen", "炒", "煮", "烤", "炸", "做饭", "做飯")),
    ("Restaurants & Ordering Food", ("restaurant", "menu", "waiter", "order food", "bill", "餐厅", "餐廳", "菜单", "菜單", "点菜", "點菜")),
    ("Shopping", ("shop", "store", "buy", "sell", "price", "expensive", "cheap", "買", "买", "賣", "卖", "商店")),
    ("Money & Prices", ("money", "cash", "price", "cost", "expensive", "cheap", "元", "钱", "錢", "价格", "價格", "贵", "貴", "便宜")),
    ("Banking & Payments", ("bank", "credit", "account", "payment", "pay", "loan", "银行", "銀行", "信用卡", "付款")),
    ("Work & Office", ("work", "job", "office", "company", "manager", "colleague", "工作", "公司", "办公室", "辦公室", "同事")),
    ("Business", ("business", "customer", "contract", "sale", "meeting", "client", "生意", "商业", "商業", "合同", "客户", "客戶")),
    ("School & Education", ("school", "student", "teacher", "study", "learn", "class", "exam", "book", "学校", "學校", "学生", "學生", "老师", "老師", "学习", "學習")),
    ("Computers & Technology", ("computer", "internet", "phone", "email", "software", "website", "digital", "电脑", "電腦", "网络", "網路", "手机", "手機", "软件", "軟體")),
    ("Transportation", ("bus", "train", "car", "taxi", "bicycle", "airport", "station", "drive", "車", "车", "飞机", "飛機", "火车", "火車")),
    ("Directions & Locations", ("north", "south", "east", "west", "left", "right", "inside", "outside", "near", "far", "上", "下", "左", "右", "里", "裡", "外")),
    ("Travel & Hotels", ("travel", "tour", "hotel", "passport", "luggage", "trip", "旅", "酒店", "旅馆", "旅館", "护照", "護照", "行李")),
    ("Airports & Flights", ("airport", "airplane", "flight", "airline", "boarding", "机场", "機場", "飞机", "飛機", "航班")),
    ("Body", ("body", "head", "hand", "eye", "ear", "nose", "mouth", "leg", "身体", "身體", "头", "頭", "手", "眼", "耳", "鼻", "嘴", "脚", "腳")),
    ("Health", ("health", "healthy", "ill", "sick", "pain", "disease", "健康", "病", "痛")),
    ("Hospital & Medicine", ("doctor", "hospital", "medicine", "nurse", "patient", "醫", "医", "医院", "醫院", "药", "藥", "护士", "護士")),
    ("Emergency & Safety", ("emergency", "danger", "safe", "accident", "fire", "help", "危险", "危險", "安全", "事故", "救命")),
    ("Weather", ("weather", "rain", "snow", "wind", "sunny", "cloud", "temperature", "天气", "天氣", "雨", "雪", "风", "風", "太阳", "太陽")),
    ("Nature", ("nature", "mountain", "river", "sea", "tree", "flower", "forest", "山", "河", "海", "树", "樹", "花", "森林")),
    ("Animals", ("animal", "dog", "cat", "bird", "horse", "cow", "fish", "动物", "動物", "狗", "猫", "貓", "鸟", "鳥", "马", "馬")),
    ("Places & Buildings", ("place", "building", "city", "park", "library", "market", "地方", "城市", "公园", "公園")),
    ("City & Community", ("city", "community", "street", "neighborhood", "traffic", "城市", "社区", "社區", "街", "交通")),
    ("Government & Public Services", ("government", "police", "law", "court", "public", "国家", "國家", "政府", "法律", "警察")),
    ("Numbers", ("number", "hundred", "thousand", "million", "zero", "one", "two", "three", "一", "二", "三", "百", "千", "萬", "万")),
    ("Measure Words", ("measure word", "classifier", "quantifier", "个", "個", "本", "张", "張", "条", "條", "位", "只", "隻")),
    ("Time", ("time", "hour", "minute", "morning", "evening", "now", "点", "點", "小时", "小時", "分钟", "分鐘", "现在", "現在")),
    ("Dates & Calendar", ("year", "month", "week", "today", "tomorrow", "yesterday", "date", "calendar", "年", "月", "星期", "今天", "明天", "昨天")),
    ("Frequency", ("often", "always", "sometimes", "never", "usually", "daily", "常常", "总是", "總是", "有时", "有時")),
    ("Emotions & Personality", ("feel", "happy", "sad", "angry", "afraid", "love", "hate", "worry", "personality", "高兴", "高興", "快乐", "快樂", "爱", "愛")),
    ("Society & Culture", ("society", "culture", "custom", "tradition", "religion", "社会", "社會", "文化", "传统", "傳統")),
    ("Politics & Government", ("politics", "political", "election", "party", "president", "minister", "政治", "选举", "選舉", "总统", "總統")),
    ("Economy & Finance", ("economy", "economic", "finance", "investment", "market", "tax", "经济", "經濟", "金融", "投资", "投資")),
    ("Science", ("science", "scientific", "physics", "chemistry", "biology", "experiment", "科学", "科學", "物理", "化学", "化學")),
    ("Environment", ("environment", "pollution", "climate", "energy", "recycle", "环境", "環境", "污染", "气候", "氣候")),
    ("Media & News", ("news", "media", "newspaper", "reporter", "television", "radio", "新闻", "新聞", "媒体", "媒體", "报纸", "報紙")),
    ("Academic Vocabulary", ("academic", "research", "theory", "analysis", "concept", "论文", "論文", "研究", "理论", "理論", "分析")),
    ("Professional Vocabulary", ("professional", "technical", "industry", "management", "operation", "专业", "專業", "技术", "技術", "行业", "行業")),
    ("Abstract Concepts", ("concept", "idea", "reason", "method", "condition", "situation", "result", "meaning", "关系", "關係", "情况", "情況", "结果", "結果", "意义", "意義")),
    ("Taiwan Daily Life", ("taiwan", "taiwanese", "台湾", "臺灣", "台灣")),
    ("Taiwan Transportation", ("計程車", "捷運", "悠遊卡", "机车", "機車")),
    ("Taiwan Food", ("小吃", "便當", "珍珠奶茶", "滷肉飯")),
    ("Taiwan Shopping", ("便利商店", "超商", "发票", "發票")),
    ("Taiwan Services & Government", ("健保", "戶政", "里長")),
]

GRAMMAR_CHINESE = {
    "的", "得", "地", "了", "着", "著", "过", "過", "吧", "吗", "嗎", "呢", "啊",
    "和", "与", "與", "而", "但是", "可是", "因为", "因為", "所以", "如果", "虽然", "雖然",
}
ADVERB_HINTS = ("adverb", "often", "always", "already", "still", "again", "very", "also", "usually")
ADJECTIVE_HINTS = ("adjective", "beautiful", "good", "bad", "big", "small", "long", "short", "new", "old")
VERB_HINTS = ("to ", "verb", "make", "do ", "become", "use ", "give ", "take ")

RELATED_SECONDARIES = {
    "Banking & Payments": ["Money & Prices"],
    "Economy & Finance": ["Money & Prices", "Business"],
    "Restaurants & Ordering Food": ["Food", "Drinks"],
    "Cooking": ["Food"],
    "Airports & Flights": ["Travel & Hotels", "Transportation"],
    "Travel & Hotels": ["Transportation"],
    "Hospital & Medicine": ["Health", "Body"],
    "Personal Care": ["Health", "Body"],
    "Computers & Technology": ["Professional Vocabulary"],
    "Politics & Government": ["Government & Public Services"],
    "Media & News": ["Society & Culture"],
    "Taiwan Transportation": ["Transportation", "Taiwan Daily Life"],
    "Taiwan Food": ["Food", "Taiwan Daily Life"],
    "Taiwan Shopping": ["Shopping", "Taiwan Daily Life"],
    "Taiwan Work & Office": ["Work & Office", "Taiwan Daily Life"],
    "Taiwan Services & Government": ["Government & Public Services", "Taiwan Daily Life"],
}


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def text(value: Any) -> str:
    return SPACE_RE.sub(" ", str(value or "").replace("\u00a0", " ")).strip()


def normalize_chinese(value: str) -> str:
    value = ANNOTATION_RE.sub("", text(value))
    value = value.replace("｜", "/").replace("|", "/").replace("／", "/")
    value = SPACE_RE.sub("", value)
    return "/".join(part for part in value.split("/") if part)


def normalize_pinyin(value: str) -> str:
    value = unicodedata.normalize("NFC", text(value).lower())
    value = value.replace("u:", "ü").replace("v", "ü")
    value = value.replace("｜", "/").replace("|", "/").replace("／", "/")
    value = value.replace("·", "").replace("’", "").replace("'", "")
    value = SPACE_RE.sub("", value)
    return NON_PINYIN_RE.sub("", value)


def source_rows(source: str, path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for level in payload.get("levels", []):
        for lesson in level.get("lessons", []):
            for word in lesson.get("words", []):
                ordinal += 1
                rows.append({
                    "source": source,
                    "sourceRow": ordinal,
                    "sourceNo": word.get("sourceNo"),
                    "sourceLevel": text(level.get("code")),
                    "sourceCategory": text(lesson.get("title")) if source == "tocfl" else "",
                    "traditional": text(word.get("traditional")),
                    "simplified": text(word.get("simplified")),
                    "pinyin": text(word.get("pinyin")),
                    "english": text(word.get("english")),
                    "hindi": text(word.get("hindi")),
                    "authoritativeHskLevel": None,
                    "mergeHskLevel": (
                        int(source.removeprefix("hsk"))
                        if source.startswith("hsk") and source.removeprefix("hsk").isdigit()
                        else None
                    ),
                })
    return rows


def csv_rows() -> list[dict[str, Any]]:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Missing input: {CSV_PATH}")
    rows = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for ordinal, row in enumerate(csv.DictReader(handle), 1):
            rows.append({
                "source": "hsk3-csv",
                "sourceRow": ordinal,
                "sourceNo": text(row.get("Index")),
                "sourceLevel": f"HSK{int(text(row.get('Level')))}",
                "sourceCategory": "",
                "traditional": "",
                "simplified": text(row.get("Chinese")),
                "pinyin": text(row.get("Pingyin") or row.get("Pinyin")),
                "english": text(row.get("English")),
                "hindi": "",
                "authoritativeHskLevel": int(text(row.get("Level"))),
                "mergeHskLevel": int(text(row.get("Level"))),
            })
    return rows


def aliases(row: dict[str, Any], ambiguous: set[str]) -> list[str]:
    py = normalize_pinyin(row["pinyin"])
    forms = {
        normalize_chinese(row["simplified"]),
        normalize_chinese(row["traditional"]),
    } - {""}
    row_ambiguous = any(f"{form}\x1f{py}" in ambiguous for form in forms)
    result = []
    for form in sorted(forms):
        base = f"{form}\x1f{py}"
        if not row_ambiguous:
            result.append(base)
            continue
        level = row.get("mergeHskLevel")
        if level:
            result.append(f"{base}\x1fhsk-{level}")
        else:
            sense = re.sub(r"[^a-z0-9]+", "-", text(row.get("english")).lower()).strip("-")
            result.append(f"{base}\x1fsense-{sense}")
    return result


def english_tokens(value: str) -> set[str]:
    stop = {
        "the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "with",
        "be", "is", "as", "sth", "sb", "etc", "one",
    }
    return {
        token for token in re.findall(r"[a-z]+", text(value).lower())
        if len(token) > 1 and token not in stop
    }


def assign_ambiguous_levels(
    rows: list[dict[str, Any]],
    authoritative: list[dict[str, Any]],
) -> set[str]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    levels_by_alias: dict[str, set[int]] = defaultdict(set)
    for row in authoritative:
        py = normalize_pinyin(row["pinyin"])
        forms = {
            normalize_chinese(row["simplified"]),
            normalize_chinese(row["traditional"]),
        } - {""}
        for form in forms:
            alias = f"{form}\x1f{py}"
            candidates[alias].append(row)
            levels_by_alias[alias].add(int(row["authoritativeHskLevel"]))
    ambiguous = {alias for alias, levels in levels_by_alias.items() if len(levels) > 1}

    for row in rows:
        if row.get("mergeHskLevel"):
            continue
        py = normalize_pinyin(row["pinyin"])
        forms = {
            normalize_chinese(row["simplified"]),
            normalize_chinese(row["traditional"]),
        } - {""}
        matches = {
            candidate["authoritativeHskLevel"]: candidate
            for form in forms
            for candidate in candidates.get(f"{form}\x1f{py}", [])
        }
        if len(matches) <= 1:
            continue
        source_tokens = english_tokens(row.get("english", ""))
        scored = sorted(
            (
                len(source_tokens & english_tokens(candidate.get("english", ""))),
                -int(level),
                int(level),
            )
            for level, candidate in matches.items()
        )
        if scored and scored[-1][0] > 0:
            row["mergeHskLevel"] = scored[-1][2]
    return ambiguous


def preferred(group: list[dict[str, Any]], field: str) -> str:
    source_rank = {"tocfl": 0, "nhm1000": 1, "hsk1": 2, "hsk2": 2, "hsk3": 2,
                   "hsk4": 2, "hsk5": 2, "hsk6": 2, "hsk3-csv": 3}
    candidates = [row for row in group if text(row.get(field))]
    if not candidates:
        return ""
    candidates.sort(key=lambda row: (
        source_rank.get(row["source"], 9),
        len(text(row[field])) if field in {"traditional", "simplified", "pinyin"} else -len(text(row[field])),
        row["source"], row["sourceRow"],
    ))
    return text(candidates[0][field])


def load_category_seeds() -> tuple[dict[str, str], dict[str, str]]:
    path = ROOT / "scripts" / "categorize_tocfl.py"
    spec = importlib.util.spec_from_file_location("_tocfl_categories", path)
    if spec is None or spec.loader is None:
        return {}, {}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    by_form: dict[str, str] = {}
    by_form_pinyin: dict[str, str] = {}
    for key, category in module.EXPLICIT.items():
        category = SEED_CATEGORY_MAP.get(category, category)
        if category not in CATEGORY_ORDER:
            category = "Other / Miscellaneous"
        if "|" in key:
            form, py = key.rsplit("|", 1)
            by_form_pinyin[f"{normalize_chinese(form)}\x1f{normalize_pinyin(py)}"] = category
        else:
            by_form[normalize_chinese(key)] = category
    return by_form, by_form_pinyin


def load_pos_lookup() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Load linguistic part-of-speech evidence from the bundled HSK lexicon."""
    if not POS_PATH.is_file():
        return {}, {}
    payload = json.loads(POS_PATH.read_text(encoding="utf-8"))
    by_form: dict[str, set[str]] = defaultdict(set)
    by_reading: dict[str, set[str]] = defaultdict(set)
    for entry in payload:
        form = normalize_chinese(text(entry.get("simplified")))
        tags = {text(tag).lower() for tag in entry.get("pos", []) if text(tag)}
        if not form or not tags:
            continue
        by_form[form].update(tags)
        for variant in entry.get("forms", []):
            traditional = normalize_chinese(text(variant.get("traditional")))
            pinyin = normalize_pinyin(
                text((variant.get("transcriptions") or {}).get("pinyin"))
            )
            if traditional:
                by_form[traditional].update(tags)
            if pinyin:
                by_reading[f"{form}\x1f{pinyin}"].update(tags)
                if traditional:
                    by_reading[f"{traditional}\x1f{pinyin}"].update(tags)
    return by_form, by_reading


def classify(
    simplified: str,
    traditional: str,
    pinyin: str,
    english: str,
    seed_categories: list[str],
    exact_form: dict[str, str],
    exact_reading: dict[str, str],
    pos_tags: list[str],
) -> tuple[str, list[str], str]:
    forms = [normalize_chinese(traditional), normalize_chinese(simplified)]
    py = normalize_pinyin(pinyin)
    candidates: list[tuple[str, str]] = []
    for form in forms:
        if f"{form}\x1f{py}" in exact_reading:
            candidates.append((exact_reading[f"{form}\x1f{py}"], "Chinese/Pinyin override"))
    for form in forms:
        if form in exact_form:
            candidates.append((exact_form[form], "Chinese override"))
    candidates.extend(
        (SEED_CATEGORY_MAP.get(cat, cat), "TOCFL lesson seed")
        for cat in seed_categories
        if SEED_CATEGORY_MAP.get(cat, cat) in CATEGORY_ORDER
    )

    chinese_haystack = f"{simplified} {traditional}"
    english_haystack = english.lower()
    rule_matches: list[str] = []
    if normalize_chinese(simplified) in GRAMMAR_CHINESE or normalize_chinese(traditional) in GRAMMAR_CHINESE:
        rule_matches.append("Grammar & Function Words")
    for category, terms in CATEGORY_RULES:
        matched = False
        for term in terms:
            if re.search(r"[\u3400-\u9fff]", term):
                matched = term in chinese_haystack
            else:
                matched = re.search(
                    rf"(?<![a-z]){re.escape(term.strip())}(?![a-z])",
                    english_haystack,
                ) is not None
            if matched:
                break
        if matched:
            rule_matches.append(category)
    if any(hint in english.lower() for hint in ADVERB_HINTS):
        rule_matches.append("Adverbs")
    if any(hint in english.lower() for hint in ADJECTIVE_HINTS):
        rule_matches.append("Adjectives")
    if any(hint in english.lower() for hint in VERB_HINTS):
        rule_matches.append("Common Verbs")

    pos_categories: list[str] = []
    for tag in pos_tags:
        base = tag.split("-", 1)[0]
        if base.startswith("v"):
            pos_categories.append("Common Verbs")
        elif base.startswith("a"):
            pos_categories.append("Adjectives")
        elif base == "d":
            pos_categories.append("Adverbs")
        elif base == "p":
            pos_categories.append("Prepositions")
        elif base == "c":
            pos_categories.append("Conjunctions & Connectors")
        elif base in {"u", "y", "e", "o"}:
            pos_categories.append("Grammar & Function Words")
        elif base == "r":
            pos_categories.append("Pronouns")
        elif base == "m":
            pos_categories.append("Numbers")
        elif base == "q":
            pos_categories.append("Measure Words")
        elif base in {"f", "s"}:
            pos_categories.append("Directions & Locations")
        elif base == "t":
            pos_categories.append("Time")
    pos_categories = list(dict.fromkeys(pos_categories))

    if candidates:
        counts = Counter(cat for cat, _ in candidates)
        primary = sorted(counts, key=lambda cat: (-counts[cat], CATEGORY_ORDER.index(cat)))[0]
        method = next(method for cat, method in candidates if cat == primary)
        confidence = "high"
    elif rule_matches:
        primary = rule_matches[0]
        method = "deterministic keyword rule"
        confidence = "medium"
    elif pos_categories:
        primary = pos_categories[0]
        method = "bundled lexicon part of speech"
        confidence = "medium"
    else:
        primary = "Other / Miscellaneous"
        method = "fallback"
        confidence = "low"
    # High-confidence seeds should not acquire incidental secondaries from a
    # broad gloss (for example, particle 吧 has an English gloss ending in
    # "right?", which is not evidence for the directions category).
    secondary_evidence = [cat for cat, _ in candidates]
    if not candidates:
        secondary_evidence += rule_matches
    secondary_evidence += pos_categories
    secondary_evidence += RELATED_SECONDARIES.get(primary, [])
    secondary = []
    for category in secondary_evidence:
        if category != primary and category not in secondary:
            secondary.append(category)
    return primary, secondary[:3], f"{confidence}: {method}"


def difficulty(hsk_level: int | None, tocfl_levels: list[str], sources: list[str]) -> dict[str, Any]:
    if hsk_level is not None:
        label = "beginner" if hsk_level <= 2 else "intermediate" if hsk_level <= 4 else "advanced"
        return {"label": label, "score": hsk_level, "basis": f"HSK 3.0 level {hsk_level}"}
    if "A1" in tocfl_levels:
        return {"label": "beginner", "score": 1, "basis": "TOCFL A1"}
    if "A2" in tocfl_levels or "nhm1000" in sources:
        return {"label": "beginner", "score": 2, "basis": "TOCFL A2/common-word source"}
    return {"label": "intermediate", "score": 3, "basis": "outside HSK; conservative default"}


def generated_example(word: dict[str, Any]) -> dict[str, Any]:
    en = word["english"].split(";")[0].split(",")[0].strip()
    return {
        "chinese": f"我在学习“{word['simplified']}”这个词。",
        "pinyin": f"Wǒ zài xuéxí “{word['pinyin']}” zhège cí.",
        "english": f'I am learning the word “{en}”.',
        "hindi": f"मैं “{word['hindi']}” शब्द सीख रहा/रही हूँ।",
        "generated": True,
        "needsReview": True,
    }


def preserved_examples() -> dict[str, dict[str, Any]]:
    if not OUT_JSON.is_file():
        return {}
    try:
        old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    preserved = {}
    for word in old.get("words", []):
        example = word.get("example")
        if isinstance(example, dict) and (
            example.get("generated") is False or example.get("needsReview") is False
        ):
            preserved[text(word.get("id"))] = example
    return preserved


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    for source, path in JSON_SOURCES:
        rows = source_rows(source, path)
        source_counts[source] = len(rows)
        all_rows.extend(rows)
    authoritative = csv_rows()
    source_counts["hsk3-csv"] = len(authoritative)
    all_rows.extend(authoritative)
    ambiguous_aliases = assign_ambiguous_levels(all_rows, authoritative)

    uf = UnionFind(len(all_rows))
    alias_owner: dict[str, int] = {}
    for index, row in enumerate(all_rows):
        row_aliases = aliases(row, ambiguous_aliases)
        if not row_aliases:
            raise ValueError(f"Source row has no Chinese form: {row['source']}:{row['sourceRow']}")
        if not normalize_pinyin(row["pinyin"]):
            raise ValueError(f"Source row has no pinyin: {row['source']}:{row['sourceRow']}")
        for alias in row_aliases:
            if alias in alias_owner:
                uf.union(index, alias_owner[alias])
            else:
                alias_owner[alias] = index

    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(all_rows):
        groups[uf.find(index)].append(row)

    exact_form, exact_reading = load_category_seeds()
    pos_form, pos_reading = load_pos_lookup()
    old_examples = preserved_examples()
    words: list[dict[str, Any]] = []
    accounting: dict[str, list[str]] = defaultdict(list)
    duplicate_groups: list[dict[str, Any]] = []

    for group in groups.values():
        simplified = preferred(group, "simplified") or preferred(group, "traditional")
        traditional = preferred(group, "traditional") or simplified
        pinyin = preferred(group, "pinyin")
        english = preferred(group, "english")
        hindi = preferred(group, "hindi")
        if not hindi and english:
            hindi = f"अंग्रेज़ी अर्थ: {english}"

        merge_levels = sorted({
            int(row["mergeHskLevel"]) for row in group
            if row.get("mergeHskLevel") is not None
        })
        key = "\x1f".join((
            normalize_chinese(simplified),
            normalize_chinese(traditional),
            normalize_pinyin(pinyin),
            "hsk-" + "-".join(map(str, merge_levels)) if merge_levels else text(english).lower(),
        ))
        word_id = "v-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        hsk_levels = sorted({
            int(row["authoritativeHskLevel"]) for row in group
            if row["authoritativeHskLevel"] is not None
        })
        hsk_level = hsk_levels[0] if hsk_levels else None
        source_names = sorted({row["source"] for row in group})
        tocfl_levels = sorted({
            row["sourceLevel"] for row in group if row["source"] == "tocfl"
        })
        seed_categories = [
            row["sourceCategory"] for row in group if row["sourceCategory"]
        ]
        forms = [normalize_chinese(simplified), normalize_chinese(traditional)]
        normalized_py = normalize_pinyin(pinyin)
        pos_tags = sorted({
            tag
            for form in forms
            for tag in (
                pos_reading.get(f"{form}\x1f{normalized_py}", set())
                or pos_form.get(form, set())
            )
        })
        primary, secondary, category_basis = classify(
            simplified, traditional, pinyin, english, seed_categories,
            exact_form, exact_reading, pos_tags,
        )
        refs = [
            {
                "source": row["source"],
                "row": row["sourceRow"],
                **({"sourceNo": row["sourceNo"]} if row["sourceNo"] not in (None, "") else {}),
                **({"level": row["sourceLevel"]} if row["sourceLevel"] else {}),
            }
            for row in sorted(group, key=lambda item: (item["source"], item["sourceRow"]))
        ]
        word = {
            "id": word_id,
            "traditional": traditional,
            "simplified": simplified,
            "pinyin": pinyin,
            "english": english,
            "hindi": hindi,
            "hsk": {
                "status": "hsk-3.0" if hsk_levels else "outside-hsk",
                "level": hsk_level,
                "levels": hsk_levels,
                "basis": "authoritative combined CSV exact Chinese/Pinyin match" if hsk_levels else "no reliable authoritative CSV match",
            },
            "tocflLevels": tocfl_levels,
            "partOfSpeech": pos_tags,
            "primaryCategory": primary,
            "secondaryCategories": secondary,
            "categoryBasis": category_basis,
            "difficulty": difficulty(hsk_level, tocfl_levels, source_names),
            "sources": refs,
        }
        word["example"] = old_examples.get(word_id, generated_example(word))
        words.append(word)
        for ref in refs:
            accounting[ref["source"]].append(word_id)
        if len(group) > 1:
            duplicate_groups.append({
                "canonicalId": word_id,
                "rowCount": len(group),
                "sources": refs,
            })

    words.sort(key=lambda word: (
        word["hsk"]["level"] if word["hsk"]["level"] is not None else 99,
        normalize_pinyin(word["pinyin"]),
        word["id"],
    ))
    ids = [word["id"] for word in words]
    if len(ids) != len(set(ids)):
        collisions = sorted(key for key, count in Counter(ids).items() if count > 1)
        raise ValueError(f"Stable ID collision(s): {collisions}")

    missing_fields = [
        {"id": word["id"], "fields": [field for field in REQUIRED_WORD_FIELDS if not text(word.get(field))]}
        for word in words
        if any(not text(word.get(field)) for field in REQUIRED_WORD_FIELDS)
    ]
    if missing_fields:
        raise ValueError(f"Canonical words missing required fields: {missing_fields[:10]}")

    accounted_counts = {source: len(ids) for source, ids in accounting.items()}
    unaccounted = {
        source: source_counts[source] - accounted_counts.get(source, 0)
        for source in source_counts
        if source_counts[source] != accounted_counts.get(source, 0)
    }
    if unaccounted:
        raise ValueError(f"Unaccounted source rows: {unaccounted}")

    form_readings: dict[str, set[str]] = defaultdict(set)
    form_ids: dict[str, list[str]] = defaultdict(list)
    for word in words:
        form = normalize_chinese(word["simplified"])
        form_readings[form].add(normalize_pinyin(word["pinyin"]))
        form_ids[form].append(word["id"])
    homographs = [
        {"simplified": form, "readings": sorted(readings), "canonicalIds": sorted(form_ids[form])}
        for form, readings in form_readings.items() if len(readings) > 1
    ]

    category_counts = Counter(word["primaryCategory"] for word in words)
    hsk_counts = Counter(
        str(word["hsk"]["level"]) if word["hsk"]["level"] else "outside-hsk"
        for word in words
    )
    uncertain = [
        {"id": word["id"], "simplified": word["simplified"], "pinyin": word["pinyin"],
         "category": word["primaryCategory"], "basis": word["categoryBasis"]}
        for word in words if word["categoryBasis"].startswith("low:")
    ]
    manual_review = [
        {"id": word["id"], "reasons": [
            *(["generated example"] if word["example"].get("needsReview") else []),
            *(["uncertain category"] if word["categoryBasis"].startswith("low:") else []),
            *(["fallback Hindi gloss"] if word["hindi"].startswith("अंग्रेज़ी अर्थ:") else []),
        ]}
        for word in words
        if word["example"].get("needsReview")
        or word["categoryBasis"].startswith("low:")
        or word["hindi"].startswith("अंग्रेज़ी अर्थ:")
    ]
    multi_category = [
        {
            "id": word["id"],
            "traditional": word["traditional"],
            "primaryCategory": word["primaryCategory"],
            "secondaryCategories": word["secondaryCategories"],
        }
        for word in words
        if word["secondaryCategories"]
    ]
    uncertain_hsk = [
        {
            "id": word["id"],
            "traditional": word["traditional"],
            "pinyin": word["pinyin"],
            "hskLevel": "outside-hsk",
            "basis": word["hsk"]["basis"],
        }
        for word in words
        if word["hsk"]["level"] is None
    ]

    payload = {
        "meta": {
            "schemaVersion": 1,
            "title": "Canonical Chinese Vocabulary Master",
            "generatedBy": "scripts/build_vocabulary_master.py",
            "hskStandard": "New HSK / HSK 3.0, level bands 1–6",
            "hskAuthority": str(CSV_PATH.relative_to(ROOT)).replace("\\", "/"),
            "canonicalMerge": "normalized simplified/traditional form plus tone-aware pinyin",
            "sourceRowCount": len(all_rows),
            "wordCount": len(words),
        },
        "taxonomy": CATEGORY_ORDER,
        "words": words,
    }
    report = {
        "status": "ok",
        "totalInputWords": len(all_rows),
        "totalUniqueWords": len(words),
        "totalCategorizedWords": len(words),
        "sourceAccounting": {
            "inputRows": source_counts,
            "accountedRows": accounted_counts,
            "totalInputRows": len(all_rows),
            "totalAccountedRows": sum(accounted_counts.values()),
            "unaccountedRows": [],
        },
        "canonicalWordCount": len(words),
        "totalCategories": len(CATEGORY_ORDER),
        "usedCategoryCount": sum(1 for count in category_counts.values() if count),
        "rowsMergedAsDuplicates": len(all_rows) - len(words),
        "duplicateGroupCount": len(duplicate_groups),
        "duplicateGroups": sorted(duplicate_groups, key=lambda item: item["canonicalId"]),
        "homographsRetainedCount": len(homographs),
        "homographsRetained": sorted(homographs, key=lambda item: item["simplified"]),
        "hskCounts": dict(sorted(hsk_counts.items())),
        "outsideHskCount": hsk_counts.get("outside-hsk", 0),
        "categoryCounts": {cat: category_counts.get(cat, 0) for cat in CATEGORY_ORDER},
        "multipleCategoryWordCount": len(multi_category),
        "multipleCategoryWords": multi_category,
        "uncertainHskCount": len(uncertain_hsk),
        "uncertainHskWords": uncertain_hsk,
        "uncertainClassificationCount": len(uncertain),
        "uncertainClassifications": uncertain,
        "manualReviewCount": len(manual_review),
        "manualReview": manual_review,
        "missingRequiredFieldCount": 0,
        "missingRequiredFields": [],
        "stableIdCollisionCount": 0,
        "preservedReviewedExampleCount": sum(word["id"] in old_examples for word in words),
    }
    return payload, report


def write_outputs(payload: dict[str, Any], report: dict[str, Any]) -> None:
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    js_text = "window.__VOCAB_MASTER__ = " + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    for path, contents in (
        (OUT_JSON, json_text), (OUT_JS, js_text), (OUT_REPORT, report_text)
    ):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(contents, encoding="utf-8")
        temporary.replace(path)


def main() -> int:
    try:
        payload, report = build()
        write_outputs(payload, report)
    except Exception as exc:
        print(f"Vocabulary master build failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Wrote {len(payload['words'])} canonical words from "
        f"{report['sourceAccounting']['totalInputRows']} accounted source rows."
    )
    print(f"Manual review: {report['manualReviewCount']}; "
          f"outside HSK: {report['hskCounts'].get('outside-hsk', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
