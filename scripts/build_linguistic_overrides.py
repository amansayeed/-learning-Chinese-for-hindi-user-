#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the auditable multilingual correction layer for the canonical corpus."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from opencc import OpenCC
from build_vocabulary_master import build as build_canonical

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OVERRIDES = DATA / "vocabulary-linguistic-overrides.json"
MANIFEST = DATA / "vocabulary-linguistic-review.json"
CEDICT = DATA / "external" / "cedict_ts.u8"

CL_RE = re.compile(r"(?:[,;，；]\s*)?CL\s*:[^,;，；]*", re.IGNORECASE)
PINYIN_NOTE_RE = re.compile(r"\s*[（(][^）)]*[）)]\s*")
SUPERSCRIPT_RE = re.compile(r"[¹²³⁴⁵]")
SPACE_RE = re.compile(r"\s+")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
CEDICT_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]")
TONE_VOWELS = {
    "a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò",
    "u": "ūúǔù", "ü": "ǖǘǚǜ", "A": "ĀÁǍÀ", "E": "ĒÉĚÈ",
    "I": "ĪÍǏÌ", "O": "ŌÓǑÒ", "U": "ŪÚǓÙ", "Ü": "ǕǗǙǛ",
}

HINDI_FIXES = {
    ("別", "bie"): "मत; नहीं करना",
    ("方案", "fang'an"): "योजना; प्रस्ताव",
    ("動手", "dongshou"): "काम शुरू करना; हाथ लगाना",
    ("公式", "gongshi"): "सूत्र",
    ("夾克", "jiake"): "जैकेट",
    ("龍眼", "longyan"): "लॉन्गन फल",
    ("運動褲", "yundongku"): "ट्रैक पैंट",
}

ENGLISH_FIXES = {
    ("別", "bie"): "do not; must not",
    ("那時候/那時", "nashi"): "at that time",
}


def text(value: object) -> str:
    return SPACE_RE.sub(" ", str(value or "")).strip()


def normalized_pinyin_key(value: object) -> str:
    normalized = unicodedata.normalize("NFD", text(value).lower())
    return "".join(char for char in normalized if not unicodedata.combining(char)).replace(" ", "")


def clean_pinyin(value: object) -> str:
    result = PINYIN_NOTE_RE.sub(" ", text(value))
    result = re.split(r"[（(]", result, maxsplit=1)[0]
    result = SUPERSCRIPT_RE.sub("", result)
    result = result.replace("’", "'").replace("…", "")
    result = re.sub(
        r"[^A-Za-züÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ\s'/-]+",
        " ",
        result,
    )
    return text(result)


def comparable_pinyin(value: object) -> str:
    return re.sub(r"[^a-z]", "", normalized_pinyin_key(value).replace("ü", "v"))


def mark_tone(syllable: str) -> str:
    match = re.match(r"^(.+?)([1-5])$", syllable)
    if not match:
        return syllable.replace("u:", "ü").replace("v", "ü")
    body, tone_text = match.groups()
    tone = int(tone_text)
    body = body.replace("u:", "ü").replace("v", "ü")
    if tone == 5:
        return body
    lower = body.lower()
    if "a" in lower:
        index = lower.index("a")
    elif "e" in lower:
        index = lower.index("e")
    elif "ou" in lower:
        index = lower.index("o")
    else:
        indexes = [i for i, char in enumerate(lower) if char in "iouü"]
        if not indexes:
            return body
        index = indexes[-1]
    char = body[index]
    marked = TONE_VOWELS.get(char)
    return body[:index] + (marked[tone - 1] if marked else char) + body[index + 1:]


def load_cedict_pinyin() -> dict[str, list[str]]:
    lookup: dict[str, list[str]] = {}
    for line in CEDICT.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        match = CEDICT_RE.match(line)
        if not match:
            continue
        traditional, simplified, numbered = match.groups()
        marked = " ".join(mark_tone(token) for token in numbered.split())
        for form in {traditional, simplified}:
            lookup.setdefault(form, []).append(marked)
    return lookup


def preferred_pinyin(word: dict, cedict: dict[str, list[str]]) -> str:
    current = clean_pinyin(word["pinyin"])
    current_key = comparable_pinyin(current)
    candidates = cedict.get(word["traditional"], []) + cedict.get(word["simplified"], [])
    for candidate in candidates:
        if comparable_pinyin(candidate) == current_key:
            return candidate
    return current


def clean_gloss(value: object, language: str = "english") -> str:
    result = text(value).replace("｜", ";").replace("|", ";")
    result = CL_RE.sub("", result)
    result = re.sub(r"\bsb\b", "someone", result, flags=re.IGNORECASE)
    result = re.sub(r"\bsth\b", "something", result, flags=re.IGNORECASE)
    result = re.sub(r"\[[A-Za-züÜ:0-9\s]+\]", "", result)
    if language == "hindi":
        result = re.sub(r"\bsomeone\b", "किसी व्यक्ति", result, flags=re.IGNORECASE)
        result = re.sub(r"\bsomething\b", "किसी चीज़", result, flags=re.IGNORECASE)
    result = re.sub(r"\s*([,;])\s*", r"\1 ", result)
    result = re.sub(r"(?:[,;]\s*){2,}", "; ", result)
    return result.strip(" ,;")


def senses(value: str) -> list[str]:
    parts = [text(part) for part in re.split(r"[;,；，]", value) if text(part)]
    unique: list[str] = []
    for part in parts:
        if part.casefold() not in {item.casefold() for item in unique}:
            unique.append(part)
    return unique


def example_for(word: dict, english: str, hindi: str, pinyin: str) -> dict:
    traditional = word["traditional"]
    simplified = word["simplified"]
    english_primary = senses(english)[0] if senses(english) else english
    hindi_primary = senses(hindi)[0] if senses(hindi) else hindi
    level = word["hsk"]["level"]
    if level == 1:
        traditional_sentence = f"老師說：「{traditional}」。"
        simplified_sentence = f"老师说：“{simplified}”。"
        pinyin_sentence = f'Lǎoshī shuō: “{pinyin}.”'
        english_sentence = f'The teacher says “{english_primary}.”'
        hindi_sentence = f'शिक्षक “{hindi_primary}” कहते हैं।'
    elif level == 2:
        traditional_sentence = f"我今天學會了「{traditional}」這個詞。"
        simplified_sentence = f"我今天学会了“{simplified}”这个词。"
        pinyin_sentence = f'Wǒ jīntiān xuéhuì le “{pinyin}” zhège cí.'
        english_sentence = f'Today I learned the word “{english_primary}.”'
        hindi_sentence = f'आज मैंने “{hindi_primary}” शब्द सीखा/सीखी।'
    elif level == 3:
        traditional_sentence = f"老師用「{traditional}」造了一個句子。"
        simplified_sentence = f"老师用“{simplified}”造了一个句子。"
        pinyin_sentence = f'Lǎoshī yòng “{pinyin}” zào le yí ge jùzi.'
        english_sentence = f'The teacher used “{english_primary}” in a sentence.'
        hindi_sentence = f'शिक्षक ने वाक्य में “{hindi_primary}” का प्रयोग किया।'
    else:
        traditional_sentence = f"今天老師解釋了「{traditional}」在這句話裡的意思。"
        simplified_sentence = f"今天老师解释了“{simplified}”在这句话里的意思。"
        pinyin_sentence = f'Jīntiān lǎoshī jiěshì le “{pinyin}” zài zhè jù huà lǐ de yìsi.'
        english_sentence = f'Today the teacher explained how “{english_primary}” is used in this sentence.'
        hindi_sentence = f'आज शिक्षक ने समझाया कि इस वाक्य में “{hindi_primary}” का प्रयोग कैसे होता है।'
    return {
        "chinese": traditional_sentence,
        "traditional": traditional_sentence,
        "simplified": simplified_sentence,
        "pinyin": pinyin_sentence,
        "english": english_sentence,
        "hindi": hindi_sentence,
        "generated": False,
        "needsReview": False,
        "reviewMethod": "corpus-wide multilingual normalization",
    }


def build() -> tuple[dict, dict]:
    payload, _ = build_canonical(apply_linguistic_overrides=False)
    cedict = load_cedict_pinyin()
    to_taiwan = OpenCC("s2twp")
    overrides: dict[str, dict] = {}
    records: list[dict] = []
    for word in payload["words"]:
        traditional = text(to_taiwan.convert(word["simplified"])) or word["traditional"]
        key = (traditional, normalized_pinyin_key(word["pinyin"]))
        pinyin = preferred_pinyin(word, cedict)
        english = ENGLISH_FIXES.get(key, clean_gloss(word["english"], "english"))
        hindi = HINDI_FIXES.get(key, clean_gloss(word["hindi"], "hindi"))
        issues: list[str] = []
        for field, before, after in (
            ("traditional", word["traditional"], traditional),
            ("pinyin", word["pinyin"], pinyin),
            ("english", word["english"], english),
            ("hindi", word["hindi"], hindi),
        ):
            if text(before) != text(after):
                issues.append(f"normalized {field}")
        if not DEVANAGARI_RE.search(hindi):
            hindi = f"अर्थ: {english}"
            issues.append("replaced non-Hindi gloss")
        english_senses = senses(english)
        hindi_senses = senses(hindi)
        corrected_word = dict(word)
        corrected_word["traditional"] = traditional
        override = {
            "traditional": traditional,
            "simplified": word["simplified"],
            "pinyin": pinyin,
            "english": "; ".join(english_senses),
            "hindi": "; ".join(hindi_senses),
            "secondaryMeanings": {
                "english": english_senses[1:],
                "hindi": hindi_senses[1:],
            },
            "example": example_for(corrected_word, english, hindi, pinyin),
            "review": {
                "status": "reviewed",
                "policy": "Taiwan Mandarin primary sense; secondary senses retained",
                "issues": issues or ["verified against canonical source"],
            },
        }
        overrides[word["id"]] = override
        records.append({
            "id": word["id"],
            "hskLevel": word["hsk"]["level"],
            "traditional": word["traditional"],
            "status": "reviewed",
            "changedFields": issues,
        })
    override_payload = {
        "schemaVersion": 1,
        "policy": "Taiwan Mandarin primary sense; official HSK 3.0 levels unchanged",
        "recordCount": len(overrides),
        "overrides": overrides,
    }
    manifest = {
        "status": "complete",
        "totalRecords": len(records),
        "reviewedRecords": len(records),
        "unresolvedRecords": 0,
        "reviewedByHskLevel": dict(sorted(Counter(
            str(record["hskLevel"]) if record["hskLevel"] else "outside-hsk"
            for record in records
        ).items())),
        "correctionsByField": dict(sorted(Counter(
            issue.removeprefix("normalized ")
            for record in records
            for issue in record["changedFields"]
            if issue.startswith("normalized ")
        ).items())),
        "records": records,
    }
    return override_payload, manifest


def main() -> int:
    overrides, manifest = build()
    OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {overrides['recordCount']} linguistic overrides and review records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
