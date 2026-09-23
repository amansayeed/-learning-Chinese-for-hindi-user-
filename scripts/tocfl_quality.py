# -*- coding: utf-8 -*-
"""Learner-facing cleanup for TOCFL and CCCC entries.

Simplified Chinese is a character conversion of the Traditional headword.
Mainland synonyms such as 出租车 for 計程車 are not substituted.
Dictionary debris (classifiers, variant notes) is removed. A short list of
verified wrong matches is replaced with the Taiwan Mandarin learner sense.
"""
from __future__ import annotations

import re

from opencc import OpenCC

TW2S = OpenCC("tw2s")
HAN = re.compile(r"[\u3400-\u9fff]")
BOPOMOFO = re.compile(r"[\u3100-\u312F˙]")
LATIN = re.compile(r"[A-Za-z]")
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
CLASSIFIER_ONLY = re.compile(
    r"^[个位本张張台臺辆輛条條只隻支枝间間家所部册冊片场場棵颗顆封顶頂份块塊瓶杯件套粒滴群班次趟遍顿頓双雙]+$"
)

# Verified against the headword, part of speech, and reading.
# These entries had inherited another word's dictionary gloss.
BY_TRADITIONAL = {
    "小孩(子)": ("child; kid", "बच्चा"),
    "籃(子)": ("basket", "टोकरी"),
    "脖(子)": ("neck", "गर्दन"),
    "橘(子)": ("tangerine; mandarin orange", "संतरा"),
    "案(子)": ("case; matter", "मामला"),
    "凳(子)": ("stool", "स्टूल"),
    "罐(子)": ("jar; can", "जार; डिब्बा"),
    "旗(子)": ("flag", "झंडा"),
    "繩(子)": ("rope", "रस्सी"),
    "巷(子)": ("alley; lane", "गली"),
    "鴿(子)": ("pigeon", "कबूतर"),
    "管(子)": ("tube; pipe", "पाइप; नली"),
    "棍(子)": ("stick; rod", "डंडा"),
    "籠(子)": ("cage", "पिंजरा"),
    "麥(子)": ("wheat", "गेहूँ"),
    "燕(子)": ("swallow (the bird)", "अबाबील"),
    "單(子)": ("list; form; bill", "सूची; फॉर्म"),
    "帶(子)": ("belt; strap; ribbon", "पट्टी; बेल्ट"),
    "棒(子)": ("stick; club; bat", "डंडा"),
    "爐(子)": ("stove", "स्टोव"),
    "盤/盤(子)": ("plate; dish; tray", "थाली; तश्तरी"),
    "布/佈置": ("to arrange; to decorate", "सजाना; व्यवस्थित करना"),
    "決/絕": ("definitely; absolutely", "बिल्कुल; निश्चित रूप से"),
    "冷氣(機)": ("air conditioner", "एयर-कंडीशनर"),
    "手指(頭)/指頭": ("finger", "उंगली"),
    "剎(ㄕㄚ)車/煞車": ("to brake; brake", "ब्रेक लगाना"),
}

BY_READING = {
    ("著", "zhe"): ("aspect particle: an action is ongoing", "काम जारी होने का चिह्न"),
    ("著", "zhuó"): ("to wear; to touch; to apply", "पहनना; छूना"),
}


def head_candidates(value: str) -> list[str]:
    """Forms worth looking up. Parenthetical pieces are not separate words."""
    values = [value, *re.split(r"[/／]", value)]
    values += [re.sub(r"[()（）]", "", item) for item in list(values)]
    values += [re.sub(r"[(（][^)）]*[)）]", "", item) for item in list(values)]
    return list(dict.fromkeys(item.strip() for item in values if item.strip()))


def reading(pinyin: str) -> str:
    text = re.sub(r"[(（][^)）]*[)）]", "", pinyin or "")
    return re.sub(r"[\s/／]", "", text).lower()


def clean_pinyin_spacing(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = re.sub(r"[(（]\s+", lambda match: match.group(0).strip(), text)
    text = re.sub(r"\s+[)）]", lambda match: match.group(0).strip(), text)
    return text


def learner_simplified(traditional: str) -> str:
    """Script conversion only. Optional syllables stay; pronunciation notes do not."""
    parts: list[str] = []
    for part in re.split(r"[/／]", traditional or ""):
        def drop_note(match: re.Match[str]) -> str:
            inner = match.group(1)
            if BOPOMOFO.search(inner):
                return ""
            return inner

        part = re.sub(r"[(（]([^)）]*)[)）]", drop_note, part).strip()
        if not part:
            continue
        simplified = TW2S.convert(part)
        if simplified and simplified not in parts:
            parts.append(simplified)
    return "/".join(parts)


def _drop_classifier_parens(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        inner = match.group(1)
        bare = re.sub(r"[\s;；,，、/／]", "", inner)
        if not bare or CLASSIFIER_ONLY.fullmatch(bare):
            return ""
        return match.group(0)

    return re.sub(r"[(（]([^)）]*)[)）]", replace, text)


def _tidy(text: str) -> str:
    text = _drop_classifier_parens(text)
    text = re.sub(r"[(（]\s*[;；,，]?\s*[)）]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,;；，])", r"\1", text)
    text = re.sub(r"(?:;\s*){2,}", "; ", text)
    return text.strip(" ;,，、")


def _classifier_token(segment: str) -> bool:
    bare = re.sub(r"[\s\[\]()（）,，、/／:：.]", "", segment)
    return bool(bare) and bool(CLASSIFIER_ONLY.fullmatch(bare))


def _keep_english_segment(segment: str) -> str:
    segment = segment.strip()
    if not segment:
        return ""
    lowered = segment.lower()
    if lowered.startswith(("variant of", "see also", "old variant", "abbr. for", "also pr")):
        return ""
    if "kangxi radical" in lowered or re.search(r"\bclassifier\b", lowered):
        return ""
    if re.match(r"^CL\b", segment, re.I) or _classifier_token(segment):
        return ""
    segment = _tidy(segment)
    if not segment or not LATIN.search(segment):
        return ""
    if segment.lower() in {"cl", "variant of", "see also"}:
        return ""
    return segment


def split_senses(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in text or "":
        if char in "(（":
            depth += 1
        elif char in ")）" and depth:
            depth -= 1
        if char in ";；" and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(char)
    parts.append("".join(buf))
    return parts


def clean_english(text: str) -> str:
    kept: list[str] = []
    seen: set[str] = set()
    for segment in split_senses(text):
        cleaned = _keep_english_segment(segment)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            kept.append(cleaned)
    result = _tidy("; ".join(kept))
    return result or _tidy(text or "")


def clean_hindi(text: str) -> str:
    kept: list[str] = []
    seen: set[str] = set()
    for segment in split_senses(text):
        segment = re.sub(r"\[[^\]]*\]", "", segment)
        if "सीएल" in segment or re.search(r"\bCL\b", segment) or "वर्गीकरण" in segment:
            continue
        if _classifier_token(segment):
            continue
        if HAN.search(segment) and not DEVANAGARI.search(segment):
            continue
        segment = _tidy(segment)
        if not segment or segment in seen or not DEVANAGARI.search(segment):
            continue
        if segment in {"पीआर भी"}:
            continue
        seen.add(segment)
        kept.append(segment)
    result = _tidy("; ".join(kept))
    return result or _tidy(HAN.sub("", text or ""))


def polish_entry(word: dict) -> dict:
    traditional = word.get("traditional") or ""
    word["pinyin"] = clean_pinyin_spacing(word.get("pinyin") or "")
    simplified = learner_simplified(traditional)
    if simplified:
        word["simplified"] = simplified
    english = clean_english(word.get("english") or "")
    hindi = clean_hindi(word.get("hindi") or "")
    fix = BY_READING.get((traditional, reading(word.get("pinyin") or "")))
    if fix is None:
        fix = BY_TRADITIONAL.get(traditional)
    if fix:
        english, hindi = fix
    # 砲 and 炮 are variant characters of one word. Fold 砲 into 炮 so the
    # learner sees a single entry. 牠 and 它 stay separate: Taiwan uses 牠
    # for animals and 它 for things.
    if traditional == "砲":
        word["simplified"] = "炮"
    word["english"] = english
    word["hindi"] = hindi
    return word


def _forms(word: dict) -> list[str]:
    found: list[str] = []
    for value in (word.get("traditional") or "", word.get("simplified") or ""):
        for form in re.split(r"[/／]", value):
            form = re.sub(r"\s+", "", form)
            if form and form not in found:
                found.append(form)
    return found


def _group_count(rows: list[dict]) -> int:
    parent = list(range(len(rows)))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    owner: dict[str, int] = {}
    for index, word in enumerate(rows):
        read = re.sub(r"\s+", "", (word.get("pinyin") or "").lower().replace("u:", "ü"))
        for form in _forms(word):
            key = form + "\t" + read
            if key in owner:
                left, right = root(index), root(owner[key])
                if left != right:
                    parent[right] = left
            else:
                owner[key] = index
    return len({root(index) for index in range(len(rows))})


def apply_payloads(write: bool) -> None:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "data"
    files = (
        (root / "tocfl-8000.json", root / "tocfl-8000.js", "window.__TOCFL_8000__ = "),
        (root / "tocfl-cccc.json", root / "tocfl-cccc.js", "window.__TOCFL_CCCC__ = "),
    )
    english_changed = simplified_changed = hindi_changed = pinyin_changed = 0
    overrides = 0
    still_long = 0
    empty_english = 0
    samples: list[str] = []
    before_rows: list[dict] = []
    after_rows: list[dict] = []

    for json_path, js_path, prefix in files:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        for word in payload["words"]:
            before_rows.append(dict(word))
            original = dict(word)
            polish_entry(word)
            after_rows.append(dict(word))
            if word["english"] != original.get("english"):
                english_changed += 1
            if word["hindi"] != original.get("hindi"):
                hindi_changed += 1
            if word["simplified"] != original.get("simplified"):
                simplified_changed += 1
                if len(samples) < 12 and original.get("simplified") not in (word["simplified"],):
                    samples.append(
                        f"{original.get('traditional')} | {original.get('simplified')} -> {word['simplified']}"
                    )
            if word["pinyin"] != original.get("pinyin"):
                pinyin_changed += 1
            if word["traditional"] in BY_TRADITIONAL or (word["traditional"], reading(word["pinyin"])) in BY_READING:
                overrides += 1
            if len(word["english"]) > 140:
                still_long += 1
            if not word["english"] or not word["hindi"] or not word["simplified"]:
                empty_english += 1
        if write:
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            js_path.write_text(
                prefix + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                encoding="utf-8",
            )
            print(f"Wrote {json_path.name} and {js_path.name}")

    print(f"entries {len(before_rows)}")
    print(f"english changed {english_changed}")
    print(f"hindi changed {hindi_changed}")
    print(f"simplified changed {simplified_changed}")
    print(f"pinyin spacing {pinyin_changed}")
    print(f"verified meaning replacements {overrides}")
    print(f"english still over 140 characters {still_long}")
    print(f"empty required fields {empty_english}")
    print(f"deduped groups before { _group_count(before_rows) } after { _group_count(after_rows) }")
    print("simplified samples:")
    for line in samples:
        print(" ", line)


if __name__ == "__main__":
    import sys

    apply_payloads(write="--write" in sys.argv)
