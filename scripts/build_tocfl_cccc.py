# -*- coding: utf-8 -*-
"""Extract every vocabulary level from the official multi-sheet CCCC .xls workbook."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
from deep_translator import GoogleTranslator
from build_vocabulary_master import classify, load_category_seeds

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "tocfl" / "CCCC_Vocabulary_2022 (1).xls"
MASTER = ROOT / "data" / "vocabulary-master.json"
OUT = ROOT / "data" / "tocfl-cccc.json"
OUT_JS = ROOT / "data" / "tocfl-cccc.js"
CACHE = ROOT / "data" / "tocfl-cccc-hindi-cache.json"

LEVELS = [
    ("萌芽級", "sprouting", "Sprouting Level"),
    ("成長級", "growing", "Growing Level"),
    ("茁壯級", "thriving", "Thriving Level"),
]

CATEGORY_LABELS = {
    "人物": "人物 · People",
    "形色": "形色 · Shapes & Colors",
    "數量": "數量 · Numbers",
    "時間": "時間 · Time",
    "生活": "生活 · Daily Life",
    "地方": "地方 · Places",
    "交通": "交通 · Transportation",
    "自然": "自然 · Nature",
    "程度": "程度 · Degree",
    "常用語": "常用語 · Common Expressions",
    "功能詞": "功能詞 · Function Words",
}

BREVE_TO_CARON = str.maketrans({
    "ă": "ǎ", "ĕ": "ě", "ĭ": "ǐ", "ŏ": "ǒ", "ŭ": "ǔ",
    "Ă": "Ǎ", "Ĕ": "Ě", "Ĭ": "Ǐ", "Ŏ": "Ǒ", "Ŭ": "Ǔ",
})


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def clean_pinyin(value: object) -> str:
    return clean(value).translate(BREVE_TO_CARON).replace(" /", "/").replace("/ ", "/")


def form_candidates(value: str) -> list[str]:
    candidates = [value, *re.split(r"[/／]", value)]
    candidates += [re.sub(r"[()（）]", "", item) for item in list(candidates)]
    candidates += [re.sub(r"[(（][^)）]*[)）]", "", item) for item in list(candidates)]
    candidates += re.findall(r"[\u3400-\u9fff]+", value)
    return list(dict.fromkeys(item.strip() for item in candidates if item.strip()))


def master_word_lookup() -> dict[str, dict]:
    payload = json.loads(MASTER.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for word in payload["words"]:
        for form in (word.get("traditional"), word.get("simplified")):
            if clean(form):
                result.setdefault(clean(form), word)
    return result


def translate_hindi(english: str, cache: dict[str, str], enabled: bool) -> str:
    key = english.strip()
    if key in cache:
        return cache[key]
    if enabled and key:
        try:
            short = key.split(";", 1)[0].split(",", 1)[0].strip()
            translated = clean(GoogleTranslator(source="en", target="hi").translate(short))
            if translated:
                cache[key] = translated
                time.sleep(0.12)
                return translated
        except Exception as error:
            print(f"Translation warning: {key[:50]} — {error}")
    fallback = "अर्थ: " + (key or "अज्ञात")
    cache[key] = fallback
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--translate-missing", action="store_true")
    args = parser.parse_args()

    if not WORKBOOK.is_file():
        raise FileNotFoundError(WORKBOOK)

    excel = pd.ExcelFile(WORKBOOK, engine="xlrd")
    expected_sheets = [name for name, _, _ in LEVELS] + ["三級詞彙", "詞表說明", "詞性縮寫對照表"]
    missing_sheets = [name for name in expected_sheets if name not in excel.sheet_names]
    if missing_sheets:
        raise ValueError(f"Workbook is missing sheets: {missing_sheets}")

    master_by_form = master_word_lookup()
    exact_form, exact_reading = load_category_seeds()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.is_file() else {}
    words: list[dict] = []
    level_meta: list[dict] = []

    for sheet_name, level_id, english_label in LEVELS:
        frame = pd.read_excel(WORKBOOK, sheet_name=sheet_name, header=1, engine="xlrd")
        required = {"分類", "細目", "正體字", "简体字", "漢拼", "詞性", "英文"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{sheet_name} columns do not match the documented format")
        frame = frame[frame["正體字"].notna()].copy()
        level_meta.append({
            "id": level_id,
            "code": sheet_name,
            "label": f"{sheet_name} · {english_label}",
            "wordCount": len(frame),
        })
        for index, row in frame.iterrows():
            traditional = clean(row["正體字"])
            simplified = clean(row["简体字"]) or traditional
            english = clean(row["英文"])
            master_word = next(
                (master_by_form[item] for item in form_candidates(traditional) if item in master_by_form),
                {},
            )
            matched_hindi = clean(master_word.get("hindi"))
            hindi = matched_hindi or translate_hindi(english, cache, args.translate_missing)
            broad = clean(row["分類"])
            detail = clean(row["細目"])
            if master_word:
                category = clean(master_word.get("primaryCategory")) or "Other / Miscellaneous"
                secondary = [clean(item) for item in master_word.get("secondaryCategories", []) if clean(item)]
                category_basis = "existing reviewed vocabulary category"
            else:
                category, secondary, category_basis = classify(
                    simplified,
                    traditional,
                    clean_pinyin(row["漢拼"]),
                    english,
                    [],
                    exact_form,
                    exact_reading,
                    [item.strip().lower() for item in re.split(r"[/,; ]+", clean(row["詞性"])) if item.strip()],
                )
            source_category = CATEGORY_LABELS.get(broad, broad)
            if source_category != category and source_category not in secondary:
                secondary.append(source_category)
            words.append({
                "id": f"cccc-{level_id}-{len(words) + 1:04d}",
                "level": level_id,
                "levelCode": sheet_name,
                "traditional": traditional,
                "simplified": simplified,
                "pinyin": clean_pinyin(row["漢拼"]),
                "english": english,
                "hindi": hindi,
                "partOfSpeech": clean(row["詞性"]),
                "category": category,
                "secondaryCategories": secondary[:3],
                "categoryBasis": category_basis,
                "sourceCategory": source_category,
                "categoryCode": broad,
                "subcategory": detail,
                "sourceSheet": sheet_name,
                "sourceRow": int(index) + 3,
            })
        print(f"{sheet_name}: {len(frame)} words")

    index_sheet = pd.read_excel(WORKBOOK, sheet_name="三級詞彙", header=0, engine="xlrd")
    index_rows = index_sheet[index_sheet["詞彙"].notna() & index_sheet["等級"].notna()]
    if len(index_rows) != len(words):
        raise ValueError(f"Combined index has {len(index_rows)} words; level sheets have {len(words)}")
    instructions = pd.read_excel(WORKBOOK, sheet_name="詞表說明", header=None, engine="xlrd")
    pos_legend = pd.read_excel(WORKBOOK, sheet_name="詞性縮寫對照表", header=None, engine="xlrd")

    payload = {
        "meta": {
            "title": "Children's Chinese Competency Certification Vocabulary 2022",
            "source": WORKBOOK.name,
            "sheetNames": excel.sheet_names,
            "wordCount": len(words),
            "referenceSheets": {
                "三級詞彙": len(index_rows),
                "詞表說明": len(instructions),
                "詞性縮寫對照表": len(pos_legend),
            },
            "note": "Vocabulary comes from the three level sheets; the combined index and documentation sheets are validated but not duplicated.",
        },
        "levels": level_meta,
        "words": words,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_JS.write_text(
        "window.__TOCFL_CCCC__ = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} and {OUT_JS.relative_to(ROOT)} ({len(words)} rows)")


if __name__ == "__main__":
    main()
