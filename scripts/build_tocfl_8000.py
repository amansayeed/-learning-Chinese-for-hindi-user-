# -*- coding: utf-8 -*-
"""Extract all seven levels from the official TOCFL 8,000-word workbook."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
from deep_translator import GoogleTranslator
from deep_translator import constants as translator_constants
from opencc import OpenCC
from category_taxonomy import apply_taxonomy_to_payload, write_taxonomy_js
from tocfl_quality import head_candidates, polish_entry

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = (
    ROOT
    / "data"
    / "tocfl"
    / "8000zhuyin_202409"
    / "華語八千詞(內含注音字型檔)"
    / "華語八千詞表20240923.xlsx"
)
MASTER = ROOT / "data" / "vocabulary-master.json"
CEDICT = ROOT / "data" / "external" / "cedict_ts.u8"
OUT = ROOT / "data" / "tocfl-8000.json"
OUT_JS = ROOT / "data" / "tocfl-8000.js"
EN_CACHE = ROOT / "data" / "tocfl-8000-english-cache.json"
HI_CACHE = ROOT / "data" / "tocfl-8000-hindi-cache.json"

LEVELS = [
    ("準備級一級(Novice 1)", "novice-1", "準備級一級 · Novice 1", 160),
    ("準備級二級(Novice 2)", "novice-2", "準備級二級 · Novice 2", 234),
    ("入門級(Level 1)", "level-1", "入門級 · Level 1", 347),
    ("基礎級(Level 2)", "level-2", "基礎級 · Level 2", 485),
    ("進階級(Level 3)", "level-3", "進階級 · Level 3", 1173),
    ("高階級(Level 4)", "level-4", "高階級 · Level 4", 2342),
    ("流利級(Level 5)", "level-5", "流利級 · Level 5", 2776),
]

CONTEXT_LABELS = {
    "個人資料": "個人資料 · Personal Information",
    "與他人的關係": "與他人的關係 · Relationships",
    "房屋與家庭、環境": "房屋與家庭、環境 · Home & Environment",
    "日常生活": "日常生活 · Daily Life",
    "閒暇時間、娛樂": "閒暇時間、娛樂 · Leisure & Entertainment",
    "旅行": "旅行 · Travel",
    "健康及身體照護": "健康及身體照護 · Health & Body Care",
    "教育": "教育 · Education",
    "購物": "購物 · Shopping",
    "飲食": "飲食 · Food & Drink",
    "工作": "工作 · Work",
    "其他": "其他 · Other",
}

BREVE_TO_CARON = str.maketrans({
    "ă": "ǎ", "ĕ": "ě", "ĭ": "ǐ", "ŏ": "ǒ", "ŭ": "ǔ",
    "Ă": "Ǎ", "Ĕ": "Ě", "Ĭ": "Ǐ", "Ŏ": "Ǒ", "Ŭ": "Ǔ",
})
T2S = OpenCC("t2s")


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def clean_pinyin(value: object) -> str:
    return clean(value).translate(BREVE_TO_CARON).replace(" /", "/").replace("/ ", "/")


def candidates(value: str) -> list[str]:
    return head_candidates(value)


def load_master() -> dict[str, dict]:
    words = json.loads(MASTER.read_text(encoding="utf-8"))["words"]
    result: dict[str, dict] = {}
    for word in words:
        for form in (word.get("traditional"), word.get("simplified")):
            if clean(form):
                result.setdefault(clean(form), word)
    return result


def load_cedict() -> dict[str, dict]:
    result: dict[str, dict] = {}
    pattern = re.compile(r"^(\S+)\s+(\S+)\s+\[[^\]]+\]\s+/(.+)/$")
    for line in CEDICT.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        traditional, simplified, definitions = match.groups()
        glosses = [
            item.strip()
            for item in definitions.split("/")
            if item.strip()
            and not item.startswith(("variant of ", "see also ", "old variant of "))
        ]
        english = glosses[0] if glosses else ""
        entry = {"simplified": simplified, "english": english}
        result.setdefault(traditional, entry)
        result.setdefault(simplified, entry)
    return result


def first_match(index: dict[str, dict], traditional: str) -> dict:
    for form in candidates(traditional):
        if form in index:
            return index[form]
    return {}


def read_cache(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_cache(path: Path, cache: dict[str, str]) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def translated(
    text: str,
    cache: dict[str, str],
    translator: GoogleTranslator | None,
) -> str:
    if text in cache:
        return cache[text]
    if not translator or not text:
        return ""
    try:
        value = clean(translator.translate(text[:4500]))
        if value:
            cache[text] = value
            time.sleep(0.08)
            return value
    except Exception as error:
        print(f"Translation warning: {text[:60]} — {error}")
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--translate-missing", action="store_true")
    args = parser.parse_args()
    if not WORKBOOK.is_file():
        raise FileNotFoundError(WORKBOOK)
    master = load_master()
    cedict = load_cedict()
    en_cache = read_cache(EN_CACHE)
    hi_cache = read_cache(HI_CACHE)
    translator_constants.BASE_URLS["GOOGLE_TRANSLATE"] = "https://translate.google.co.uk/m"
    en_translator = GoogleTranslator(source="zh-TW", target="en") if args.translate_missing else None
    hi_translator = GoogleTranslator(source="en", target="hi") if args.translate_missing else None
    direct_hi_translator = GoogleTranslator(source="zh-TW", target="hi") if args.translate_missing else None
    excel = pd.ExcelFile(WORKBOOK)
    words: list[dict] = []
    levels: list[dict] = []
    missing_english = 0
    missing_hindi = 0

    for sheet_name, level_id, label, expected_count in LEVELS:
        frame = pd.read_excel(WORKBOOK, sheet_name=sheet_name)
        has_context = len(frame.columns) == 4
        context_col = frame.columns[0] if has_context else None
        word_col = frame.columns[1] if has_context else frame.columns[0]
        pinyin_col = frame.columns[2] if has_context else frame.columns[1]
        pos_col = frame.columns[3] if has_context else frame.columns[2]
        frame = frame[frame[word_col].notna()].copy()
        if len(frame) != expected_count:
            raise ValueError(f"{sheet_name}: expected {expected_count}, found {len(frame)}")
        levels.append({
            "id": level_id,
            "code": sheet_name.split("(")[0],
            "label": label,
            "wordCount": len(frame),
        })

        for index, row in frame.iterrows():
            traditional = clean(row[word_col])
            pinyin = clean_pinyin(row[pinyin_col])
            pos = clean(row[pos_col])
            master_word = first_match(master, traditional)
            cedict_word = first_match(cedict, traditional)
            simplified = (
                clean(master_word.get("simplified"))
                or clean(cedict_word.get("simplified"))
                or T2S.convert(traditional)
            )
            english = clean(master_word.get("english")) or clean(cedict_word.get("english"))
            hindi = clean(master_word.get("hindi"))
            if not english:
                english = translated(traditional, en_cache, en_translator)
            if not hindi:
                hindi = translated(english, hi_cache, hi_translator)
            if not hindi:
                hindi = translated(traditional, hi_cache, direct_hi_translator)
            if not english:
                english = "Meaning not available in the source workbook"
                missing_english += 1
            if not hindi:
                hindi = "हिन्दी अनुवाद उपलब्ध नहीं"
                missing_hindi += 1
            context = clean(row[context_col]) if context_col is not None else ""
            words.append(polish_entry({
                "id": f"tocfl8k-{level_id}-{len(words) + 1:05d}",
                "level": level_id,
                "levelCode": sheet_name.split("(")[0],
                "traditional": traditional,
                "simplified": simplified,
                "pinyin": pinyin,
                "english": english,
                "hindi": hindi,
                "partOfSpeech": pos,
                "category": "",
                "secondaryCategories": [],
                "categoryBasis": "",
                "sourceCategory": CONTEXT_LABELS.get(context, "") if context else "",
                "subcategory": context,
                "sourceSheet": sheet_name,
                "sourceRow": int(index) + 2,
            }))
        print(f"{label}: {len(frame)} words")
        write_cache(EN_CACHE, en_cache)
        write_cache(HI_CACHE, hi_cache)

    count_sheet = pd.read_excel(WORKBOOK, sheet_name="各等詞條數(Entry Number)", header=None)
    documented_total = int(count_sheet.iloc[1, -1])
    if documented_total != len(words):
        raise ValueError(f"Documented total is {documented_total}; extracted {len(words)}")
    comparison_stats = pd.read_excel(WORKBOOK, sheet_name="Sheet1", header=None)
    regional_terms = pd.read_excel(WORKBOOK, sheet_name="兩岸常用詞語差異表")
    listed_regional_terms = [
        clean(value)
        for value in regional_terms["華測八千詞條"].dropna()
        if re.fullmatch(r"[\u3400-\u9fff]+", clean(value))
    ]
    extracted_forms = {
        form
        for word in words
        for form in re.split(r"[/／]", word["traditional"])
        if form
    }
    missing_regional_terms = [word for word in listed_regional_terms if word not in extracted_forms]
    if missing_regional_terms:
        raise ValueError(f"Regional reference terms absent from level sheets: {missing_regional_terms}")

    payload = apply_taxonomy_to_payload({
        "meta": {
            "title": "華語八千詞表 2024",
            "source": WORKBOOK.name,
            "sheetNames": excel.sheet_names,
            "wordCount": len(words),
            "missingEnglish": missing_english,
            "missingHindi": missing_hindi,
            "referenceSheets": {
                "各等詞條數(Entry Number)": len(count_sheet),
                "Sheet1": len(comparison_stats),
                "兩岸常用詞語差異表": len(regional_terms),
                "regionalTermsValidated": len(listed_regional_terms),
            },
            "note": "All seven vocabulary sheets are extracted. Count and reference sheets are read for validation, not duplicated.",
        },
        "levels": levels,
        "words": words,
    }, 7517)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_JS.write_text(
        "window.__TOCFL_8000__ = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    write_taxonomy_js(ROOT / "js" / "category-taxonomy.js")
    write_cache(EN_CACHE, en_cache)
    write_cache(HI_CACHE, hi_cache)
    print(
        f"Wrote {OUT.relative_to(ROOT)} and {OUT_JS.relative_to(ROOT)}: "
        f"{len(words)} rows, {missing_english} English fallbacks, {missing_hindi} Hindi fallbacks"
    )


if __name__ == "__main__":
    main()
