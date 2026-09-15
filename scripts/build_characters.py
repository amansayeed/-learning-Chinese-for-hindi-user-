#!/usr/bin/env python3
"""Build the 3,000-character frequency browser from Taiwan MOE data."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source" / "86rest17.TXT"
CEDICT = ROOT / "data" / "external" / "cedict_ts.u8"
MASTER = ROOT / "data" / "vocabulary-master.json"
HINDI_CACHE = ROOT / "data" / "character-hindi-cache.json"
OUT_JSON = ROOT / "data" / "characters.json"
OUT_JS = ROOT / "data" / "characters.js"
SOURCE_URL = (
    "https://language.moe.gov.tw/001/Upload/files/SITE_CONTENT/"
    "M0001/86NEWS/download/86rest17.TXT"
)

LEVELS = [
    {"id": "1000", "label": "1,000 Characters", "description": "Basic Reading", "limit": 1000},
    {
        "id": "2000",
        "label": "2,000 Characters",
        "description": "Useful Everyday Reading",
        "limit": 2000,
    },
    {
        "id": "3000",
        "label": "3,000 Characters",
        "description": "Strong Everyday Reading",
        "limit": 3000,
    },
]

# After the 100 most frequent characters, these high-value building blocks are
# promoted in a teacher-curated sequence. Remaining characters are ranked by a
# blend of corpus frequency, earliest HSK use, and common-word productivity.
FOUNDATION_ORDER = "".join(
    [
        "零一二三四五六七八九十百千萬",
        "我你您好他她它我們你們他們這那哪誰什麼怎麼",
        "上下左右前後裡外中東西南北大小多少長短高低",
        "天日月年今天明昨早晚時分秒星期",
        "人男女子父母爸媽哥弟姐妹妹兒家",
        "口手足目耳心頭身水火木土金山石田雨風",
        "吃喝看聽說讀寫學問答來去走坐站住",
        "要想知道會能可以應該喜歡愛給拿用做買賣",
        "好壞對錯是有沒有不很也都和跟就還再",
        "個本張隻件杯元塊",
        "飯菜茶奶水果肉魚蛋書車門路店校工作朋友",
    ]
)

CEDICT_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$")
SKIP_GLOSS = (
    "variant of ",
    "old variant of ",
    "see ",
    "see also ",
    "surname ",
    "used in ",
)
PINYIN_VOWELS = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
    "A": "ĀÁǍÀA",
    "E": "ĒÉĚÈE",
    "I": "ĪÍǏÌI",
    "O": "ŌÓǑÒO",
    "U": "ŪÚǓÙU",
    "Ü": "ǕǗǙǛÜ",
}

FALLBACK_EXAMPLES = {
    "妳": ("妳好", "你好", "nǐ hǎo", "hello (addressing a woman)", "नमस्ते"),
    "牠": ("牠們", "它们", "tā men", "they (animals)", "वे (जानवर)"),
    "吋": ("英吋", "英寸", "yīng cùn", "inch", "इंच"),
    "噢": ("噢，是的", "噢，是的", "ō, shì de", "oh, yes", "ओह, हाँ"),
    "喔": ("喔，我懂了", "哦，我懂了", "ō, wǒ dǒng le", "oh, I understand", "ओह, मैं समझ गया"),
    "艘": ("一艘船", "一艘船", "yī sōu chuán", "one ship", "एक जहाज़"),
    "呎": ("一英呎", "一英尺", "yī yīng chǐ", "one foot", "एक फुट"),
    "裴": ("裴先生", "裴先生", "péi xiān sheng", "Mr. Pei", "श्री पेई"),
}

# CEDICT generally lists these bound characters only inside compounds, so they
# need a character-level reading and gloss rather than borrowing a whole word.
FALLBACK_DETAILS = {
    "啡": ("啡", "fēi", "coffee (in 咖啡)"),
    "諮": ("咨", "zī", "to consult"),
    "蔡": ("蔡", "cài", "surname Cai"),
    "廖": ("廖", "liào", "surname Liao"),
    "彭": ("彭", "péng", "surname Peng"),
    "盪": ("荡", "dàng", "to swing; to wash"),
    "玫": ("玫", "méi", "rose"),
    "祕": ("秘", "mì", "secret"),
    "鄧": ("邓", "dèng", "surname Deng"),
    "傢": ("家", "jiā", "used in 傢伙 and 傢具"),
    "鍊": ("链", "liàn", "chain; to forge"),
    "萄": ("萄", "táo", "grape (in 葡萄)"),
    "碌": ("碌", "lù", "busy; mediocre"),
    "蜥": ("蜥", "xī", "lizard"),
    "蜴": ("蜴", "yì", "lizard"),
    "囉": ("啰", "luo", "sentence-final particle"),
    "齣": ("出", "chū", "act of a play; classifier for plays"),
    "唸": ("念", "niàn", "to read aloud"),
    "芙": ("芙", "fú", "lotus (in 芙蓉)"),
    "僱": ("雇", "gù", "to hire"),
    "蜘": ("蜘", "zhī", "spider (in 蜘蛛)"),
    "豔": ("艳", "yàn", "gorgeous; colorful"),
    "捱": ("挨", "ái", "to endure; to delay"),
    "崑": ("昆", "kūn", "Kunlun Mountains"),
    "蔔": ("卜", "bo", "radish (in 蘿蔔)"),
    "燻": ("熏", "xūn", "to smoke; to fumigate"),
    "哉": ("哉", "zāi", "exclamatory particle"),
    # Polyphonic/variant characters use the reading and Simplified form most
    # useful in everyday Taiwan Mandarin rather than CEDICT's first rare sense.
    "著": ("着", "zhe", "aspect particle; to wear; to write"),
    "參": ("参", "cān", "to participate; to attend; to consult"),
    "乾": ("干", "gān", "dry; clean; to do"),
    "覆": ("覆", "fù", "to cover; to overturn; to reply"),
    "菸": ("烟", "yān", "tobacco; cigarette; smoke"),
    "蒐": ("搜", "sōu", "to search; to collect"),
    "瞭": ("了", "liǎo", "to understand clearly; clear-sighted"),
    "汙": ("污", "wū", "dirty; filthy; to stain"),
    "榜": ("榜", "bǎng", "list; ranking; public notice"),
    "彷": ("仿", "fǎng", "seemingly; as if"),
    "薰": ("熏", "xūn", "fragrance; to smoke; to fumigate"),
}

PREFERRED_HINDI = {
    "著": "पक्ष सूचक; पहनना; लिखना",
    "參": "भाग लेना; उपस्थित होना; परामर्श करना",
    "乾": "सूखा; साफ़; करना",
    "覆": "ढकना; पलटना; उत्तर देना",
    "菸": "तंबाकू; सिगरेट; धुआँ",
    "蒐": "खोजना; इकट्ठा करना",
    "瞭": "स्पष्ट रूप से समझना",
    "汙": "गंदा; दाग लगाना",
    "榜": "सूची; रैंकिंग; सार्वजनिक सूचना",
    "彷": "मानो; जैसे",
    "鍊": "ज़ंजीर; गढ़ना",
    "薰": "सुगंध; धूनी देना",
}

# Single characters can be polyphonic. These are the neutral, everyday
# readings a beginner should meet first; details/examples still provide the
# context that determines alternate readings.
PREFERRED_READINGS = {
    "中": "zhōng", "了": "le", "行": "xíng", "和": "hé", "作": "zuò",
    "得": "de", "說": "shuō", "長": "cháng", "場": "chǎng", "當": "dāng",
    "將": "jiāng", "好": "hǎo", "種": "zhǒng", "重": "zhòng", "合": "hé",
    "只": "zhǐ", "應": "yīng", "那": "nà", "更": "gèng", "空": "kōng",
    "量": "liàng", "強": "qiáng", "打": "dǎ", "幾": "jǐ", "片": "piàn",
    "覺": "jué", "劃": "huà", "令": "lìng", "遠": "yuǎn", "節": "jié",
    "落": "luò", "切": "qiē", "聽": "tīng", "號": "hào", "角": "jiǎo",
    "差": "chā", "待": "dài", "答": "dá", "漲": "zhǎng", "彈": "tán",
    "檔": "dǎng", "吧": "ba", "背": "bèi", "雨": "yǔ", "跑": "pǎo",
    "搶": "qiǎng", "塞": "sāi", "沉": "chén", "混": "hùn", "踏": "tà",
    "卷": "juǎn", "夾": "jiá", "橫": "héng", "磨": "mó", "涼": "liáng",
    "汗": "hàn", "頁": "yè", "讀": "dú", "追": "zhuī", "藏": "cáng",
    "尺": "chǐ", "露": "lù", "湯": "tāng", "折": "zhé", "圈": "quān",
    "鳥": "niǎo", "咳": "ké", "騎": "qí", "淺": "qiǎn", "弄": "nòng",
    "蒙": "méng", "嚇": "xià", "拾": "shí", "胖": "pàng", "炮": "pào",
    "掙": "zhèng",
}


def parse_source() -> list[dict]:
    text = SOURCE.read_bytes().decode("cp950")
    rows: list[dict] = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("│")]
        if len(cells) < 7 or not cells[1].isdigit():
            continue
        character = cells[3]
        if len(character) != 1:
            continue
        rows.append(
            {
                "rank": int(cells[1]),
                "frequencyRank": int(cells[2]),
                "traditional": character,
                "frequency": int(cells[4]),
                "percentage": float(cells[5]),
                "standardRank": int(cells[6]),
            }
        )
    if len(rows) != 4155:
        raise ValueError(f"Expected 4,155 MOE rows, found {len(rows):,}")
    if [row["rank"] for row in rows] != list(range(1, 4156)):
        raise ValueError("MOE frequency ranks are not contiguous")
    return rows


def marked_syllable(value: str) -> str:
    match = re.match(r"^([A-Za-züÜvV:]+)([1-5])$", value)
    if not match:
        return value
    syllable, raw_tone = match.groups()
    tone = int(raw_tone)
    syllable = syllable.replace("u:", "ü").replace("U:", "Ü").replace("v", "ü").replace("V", "Ü")
    if tone == 5:
        return syllable
    lower = syllable.lower()
    if "a" in lower:
        index = lower.index("a")
    elif "e" in lower:
        index = lower.index("e")
    elif "ou" in lower:
        index = lower.index("o")
    else:
        indexes = [i for i, char in enumerate(lower) if char in "aeiouü"]
        if not indexes:
            return syllable
        index = indexes[-1]
    char = syllable[index]
    return syllable[:index] + PINYIN_VOWELS[char][tone - 1] + syllable[index + 1 :]


def display_pinyin(value: str) -> str:
    return " ".join(marked_syllable(part) for part in value.split())


def useful_glosses(raw: str) -> list[str]:
    result = []
    for value in raw.split("/"):
        value = re.sub(r"\([^)]*\)", "", value).strip()
        if not value or value.lower().startswith(SKIP_GLOSS):
            continue
        if value not in result:
            result.append(value)
        if len(result) == 3:
            break
    return result


def plain_pinyin(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower().replace("ü", "v"))
    return "".join(character for character in normalized if not unicodedata.combining(character))


def load_cedict(reading_counts: dict[str, dict[str, int]]) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    direct_candidates: dict[str, list[dict]] = defaultdict(list)
    alias_exact: dict[str, dict] = {}
    examples: dict[str, list[dict]] = defaultdict(list)
    for line in CEDICT.read_text(encoding="utf-8").splitlines():
        match = CEDICT_RE.match(line)
        if not match:
            continue
        traditional, simplified, pinyin, definitions = match.groups()
        glosses = useful_glosses(definitions)
        if not glosses:
            continue
        entry = {
            "traditional": traditional,
            "simplified": simplified,
            "pinyin": display_pinyin(pinyin),
            "english": "; ".join(glosses),
        }
        if len(traditional) == 1:
            direct_candidates[traditional].append(entry)
            alias_exact.setdefault(simplified, entry)
        elif 2 <= len(traditional) <= 6:
            for character in set(traditional + simplified):
                examples[character].append(entry)
    direct_exact = {}
    rare_markers = ("classifier", "measure for", "one of the", "penis", "archaic", "dialect")
    for character, candidates in direct_candidates.items():
        counts = reading_counts.get(character, {})

        def candidate_key(entry: dict) -> tuple:
            reading = plain_pinyin(entry["pinyin"])
            preferred = plain_pinyin(PREFERRED_READINGS.get(character, ""))
            proper_name = bool(entry["pinyin"][:1].isupper())
            rare = any(marker in entry["english"].lower() for marker in rare_markers)
            return (
                bool(preferred and reading == preferred),
                counts.get(reading, 0),
                not proper_name,
                not rare,
                len(entry["english"]),
            )

        direct_exact[character] = max(candidates, key=candidate_key)
    # A character's own dictionary entry must win over another Traditional
    # character that merely simplifies to the same glyph (e.g. 干/乾/幹).
    return {**alias_exact, **direct_exact}, examples


def load_master() -> tuple[dict[str, dict], dict[str, list[dict]], dict[str, dict], dict[str, dict[str, int]]]:
    words = json.loads(MASTER.read_text(encoding="utf-8"))["words"]
    exact: dict[str, dict] = {}
    examples: dict[str, list[dict]] = defaultdict(list)
    utility: dict[str, dict] = defaultdict(lambda: {"wordCount": 0, "earliestHsk": 99})
    reading_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for word in words:
        traditional = str(word.get("traditional", ""))
        simplified = str(word.get("simplified", ""))
        raw_hsk = (word.get("hsk") or {}).get("level")
        try:
            hsk = int(raw_hsk)
        except (TypeError, ValueError):
            hsk = 99
        for character in set(traditional + simplified):
            utility[character]["wordCount"] += 1
            utility[character]["earliestHsk"] = min(utility[character]["earliestHsk"], hsk)
        syllables = str(word.get("pinyin", "")).split()
        if len(syllables) == len(traditional):
            for index, character in enumerate(traditional):
                reading_counts[character][plain_pinyin(syllables[index])] += 1
            for index, character in enumerate(simplified):
                reading_counts[character][plain_pinyin(syllables[index])] += 1
        if len(traditional) == 1:
            exact.setdefault(traditional, word)
            exact.setdefault(simplified, word)
        if not 2 <= len(traditional) <= 4:
            continue
        example = {
            "traditional": traditional,
            "simplified": simplified,
            "pinyin": word.get("pinyin", ""),
            "english": word.get("english", ""),
            "hindi": word.get("hindi", ""),
            "hsk": (word.get("hsk") or {}).get("level"),
        }
        for character in set(traditional + simplified):
            examples[character].append(example)
    return exact, examples, utility, reading_counts


def load_cache() -> dict[str, str]:
    if not HINDI_CACHE.is_file():
        return {}
    return json.loads(HINDI_CACHE.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, str]) -> None:
    HINDI_CACHE.write_text(
        json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def translate_missing(items: list[tuple[str, str]], cache: dict[str, str]) -> None:
    pending = [(character, english) for character, english in items if not cache.get(character)]
    for offset in range(0, len(pending), 25):
        batch = pending[offset : offset + 25]
        query = "\n".join(english for _, english in batch)
        url = (
            "https://translate.googleapis.com/translate_a/single?client=gtx"
            "&sl=en&tl=hi&dt=t&q=" + urllib.parse.quote(query)
        )
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.load(response)
            translated = "".join(part[0] for part in data[0]).splitlines()
            if len(translated) != len(batch):
                raise ValueError(f"expected {len(batch)} translations, received {len(translated)}")
            for (character, _), hindi in zip(batch, translated):
                if hindi.strip():
                    cache[character] = hindi.strip()
            save_cache(cache)
            print(f"Translated Hindi {min(offset + len(batch), len(pending)):,}/{len(pending):,}")
            time.sleep(0.12)
        except Exception as error:
            print(f"Translation batch {offset // 25 + 1} failed: {error}")
            time.sleep(1)


def example_sort_key(word: dict) -> tuple:
    raw_hsk = word.get("hsk")
    try:
        hsk = int(raw_hsk)
    except (TypeError, ValueError):
        hsk = 99
    return (hsk, len(word["traditional"]), word["traditional"])


def teaching_sort_key(item: dict, utility: dict[str, dict], foundation: dict[str, int]) -> tuple:
    source_rank = item["rank"]
    character = item["traditional"]
    # The very highest-frequency characters remain first: they dominate every
    # basic sentence and should not be displaced by a pedagogical heuristic.
    if source_rank <= 100:
        return (0, source_rank, source_rank)
    if character in foundation:
        return (1, foundation[character], source_rank)
    info = utility.get(character, {"wordCount": 0, "earliestHsk": 99})
    hsk = info["earliestHsk"]
    multiplier = {1: 0.48, 2: 0.62, 3: 0.76, 4: 0.86, 5: 0.93, 6: 0.97}.get(hsk, 1.0)
    productivity_bonus = min(180, info["wordCount"] * 6)
    score = source_rank * multiplier - productivity_bonus
    return (2, round(score, 4), source_rank)


def audit_characters(characters: list[dict], source_rows: list[dict], t2s: OpenCC) -> dict:
    if len(characters) != 3000:
        raise ValueError(f"Expected 3,000 character records, found {len(characters):,}")
    traditional = [item["traditional"] for item in characters]
    if len(set(traditional)) != 3000 or any(len(value) != 1 for value in traditional):
        raise ValueError("Character output contains a duplicate or non-character entry")
    expected_source = {item["traditional"] for item in source_rows}
    if set(traditional) != expected_source:
        raise ValueError("Character output does not exactly match the MOE top 3,000")
    if [item["learningRank"] for item in characters] != list(range(1, 3001)):
        raise ValueError("Learning ranks are not unique and contiguous")
    if sorted(item["rank"] for item in characters) != list(range(1, 3001)):
        raise ValueError("MOE frequency ranks are not unique and contiguous")
    if len({item["id"] for item in characters}) != 3000:
        raise ValueError("Character IDs are not unique")
    for item in characters:
        character = item["traditional"]
        if len(item["simplified"]) != 1:
            raise ValueError(f"Invalid Simplified mapping for {character}")
        if not item["pinyin"] or re.search(r"\d", item["pinyin"]):
            raise ValueError(f"Invalid Pinyin for {character}: {item['pinyin']!r}")
        if not item["english"] or item["english"] == "Meaning unavailable":
            raise ValueError(f"Missing English meaning for {character}")
        if not re.search(r"[\u0900-\u097f]", item["hindi"]):
            raise ValueError(f"Missing Devanagari Hindi meaning for {character}")
        if not item["examples"]:
            raise ValueError(f"Missing example for {character}")
        if character in FALLBACK_DETAILS:
            expected_simplified, expected_pinyin, _ = FALLBACK_DETAILS[character]
        else:
            expected_simplified, expected_pinyin = t2s.convert(character), None
        if item["simplified"] != expected_simplified:
            raise ValueError(
                f"Mapping mismatch for {character}: {item['simplified']} != {expected_simplified}"
            )
        if expected_pinyin and plain_pinyin(item["pinyin"]) != plain_pinyin(expected_pinyin):
            raise ValueError(f"Preferred reading mismatch for {character}")
    level_sets = [set(traditional[:limit]) for limit in (1000, 2000, 3000)]
    if [len(values) for values in level_sets] != [1000, 2000, 3000]:
        raise ValueError("Cumulative learning-level counts are incorrect")
    if not level_sets[0] < level_sets[1] < level_sets[2]:
        raise ValueError("Character learning levels are not strictly cumulative")
    return {
        "uniqueCharacters": 3000,
        "sourceCharactersMatched": 3000,
        "duplicateCharacters": 0,
        "missingCharacters": 0,
        "levelUniqueCounts": [1000, 2000, 3000],
        "levelNewCharacterCounts": [1000, 1000, 1000],
        "mappingOverridesReviewed": sum(
            item["simplified"] != t2s.convert(item["traditional"]) for item in characters
        ),
        "missingPinyin": 0,
        "missingEnglish": 0,
        "missingHindi": 0,
        "missingExamples": 0,
    }


def build(translate: bool) -> dict:
    rows = parse_source()[:3000]
    master_exact, master_examples, utility, reading_counts = load_master()
    cedict_exact, cedict_examples = load_cedict(reading_counts)
    cache = load_cache()

    translation_inputs = []
    for row in rows:
        character = row["traditional"]
        dictionary = cedict_exact.get(character, {})
        if character in FALLBACK_DETAILS:
            simplified, pinyin, english = FALLBACK_DETAILS[character]
            dictionary = {"simplified": simplified, "pinyin": pinyin, "english": english}
        master = master_exact.get(character, {})
        english = dictionary.get("english") or master.get("english") or "Meaning unavailable"
        if character in FALLBACK_DETAILS and cache.get(character) == "मतलब अनुपलब्ध":
            cache.pop(character)
        if master.get("hindi"):
            cache.setdefault(character, master["hindi"])
        if character in PREFERRED_HINDI:
            cache[character] = PREFERRED_HINDI[character]
        if not cache.get(character):
            translation_inputs.append((character, english))
    if translate:
        translate_missing(translation_inputs, cache)

    t2s = OpenCC("t2s")
    characters = []
    missing_hindi = 0
    for row in rows:
        traditional = row["traditional"]
        dictionary = cedict_exact.get(traditional, {})
        if traditional in FALLBACK_DETAILS:
            simplified, pinyin, english = FALLBACK_DETAILS[traditional]
            dictionary = {"simplified": simplified, "pinyin": pinyin, "english": english}
        master = master_exact.get(traditional, {})
        simplified = (
            FALLBACK_DETAILS[traditional][0]
            if traditional in FALLBACK_DETAILS
            else t2s.convert(traditional)
        )
        english = dictionary.get("english") or master.get("english") or "Meaning unavailable"
        hindi = cache.get(traditional) or master.get("hindi") or "हिन्दी अर्थ उपलब्ध नहीं"
        if hindi == "हिन्दी अर्थ उपलब्ध नहीं":
            missing_hindi += 1
        candidates = list(master_examples.get(traditional, []))
        if simplified != traditional:
            candidates.extend(master_examples.get(simplified, []))
        seen = set()
        examples = []
        for example in sorted(candidates, key=example_sort_key):
            key = (example["traditional"], example["pinyin"])
            if key in seen:
                continue
            seen.add(key)
            examples.append(example)
            if len(examples) == 5:
                break
        if not examples:
            candidates = cedict_examples.get(traditional, []) + cedict_examples.get(simplified, [])
            for example in candidates:
                key = (example["traditional"], example["pinyin"])
                if key in seen:
                    continue
                seen.add(key)
                examples.append(example)
                if len(examples) == 5:
                    break
        if not examples and traditional in FALLBACK_EXAMPLES:
            trad, simp, pinyin, example_en, example_hi = FALLBACK_EXAMPLES[traditional]
            examples.append(
                {
                    "traditional": trad,
                    "simplified": simp,
                    "pinyin": pinyin,
                    "english": example_en,
                    "hindi": example_hi,
                }
            )
        characters.append(
            {
                **row,
                "id": f"char-{row['rank']:04d}",
                "simplified": simplified,
                "pinyin": dictionary.get("pinyin") or master.get("pinyin") or "",
                "english": english,
                "hindi": hindi,
                "examples": examples,
                "earliestHsk": (
                    utility.get(traditional, {}).get("earliestHsk")
                    if utility.get(traditional, {}).get("earliestHsk") not in (None, 99)
                    else None
                ),
                "commonWordCount": utility.get(traditional, {}).get("wordCount", 0),
            }
        )

    foundation = {character: index for index, character in enumerate(dict.fromkeys(FOUNDATION_ORDER))}
    characters.sort(key=lambda item: teaching_sort_key(item, utility, foundation))
    for index, item in enumerate(characters, 1):
        item["learningRank"] = index
        item["learningBand"] = (
            "Basic Reading"
            if index <= 1000
            else "Useful Everyday Reading"
            if index <= 2000
            else "Strong Everyday Reading"
        )
    audit = audit_characters(characters, rows, t2s)

    payload = {
        "meta": {
            "schemaVersion": 1,
            "title": "Chinese Character Frequency Learning Levels",
            "source": "Taiwan Ministry of Education — 常用國字標準字體表 frequency statistics",
            "sourceUrl": SOURCE_URL,
            "sourceEncoding": "CP950 (Big5)",
            "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "sourceRowCount": 4155,
            "characterCount": len(characters),
            "missingHindi": missing_hindi,
            "unit": "individual Unicode Chinese characters, never words",
            "ordering": (
                "MOE top 100 by frequency, then teacher-curated foundations, then a score "
                "combining MOE frequency, earliest HSK use, and common-word productivity"
            ),
            "levelsAreCumulative": True,
            "audit": audit,
        },
        "levels": LEVELS,
        "characters": characters,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_JS.write_text(
        "/* Auto-generated by scripts/build_characters.py. */\n"
        "window.__CHARACTERS__ = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(characters):,} characters; "
        f"missing Hindi: {missing_hindi:,}; JSON: {OUT_JSON.stat().st_size // 1024:,} KB"
    )
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--translate-missing",
        action="store_true",
        help="Fill and cache missing Hindi meanings using Google Translate.",
    )
    args = parser.parse_args()
    build(args.translate_missing)
