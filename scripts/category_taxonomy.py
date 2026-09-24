# -*- coding: utf-8 -*-
"""Topic taxonomy for TOCFL 8,000 and CCCC rows."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

TAXONOMY: list[dict[str, Any]] = [
    {"label": "Greetings & Basics", "icon": "👋", "slug": "greetings-basics"},
    {"label": "Colors", "icon": "🎨", "slug": "colors"},
    {"label": "Family & People", "icon": "👨‍👩‍👧", "slug": "family-people"},
    {"label": "Body Parts", "icon": "🧍", "slug": "body-parts"},
    {"label": "Health & Feelings", "icon": "🏥", "slug": "health-feelings"},
    {"label": "Food", "icon": "🍎", "slug": "food"},
    {"label": "Drinks", "icon": "🥤", "slug": "drinks"},
    {"label": "House & Furniture", "icon": "🏠", "slug": "house-furniture"},
    {"label": "Kitchen Items", "icon": "🍽️", "slug": "kitchen-items"},
    {"label": "Clothing", "icon": "👕", "slug": "clothing"},
    {"label": "Travel & Transport", "icon": "🚗", "slug": "travel-transport"},
    {"label": "Places & City", "icon": "🏙️", "slug": "places-city"},
    {"label": "Nature & Weather", "icon": "🌳", "slug": "nature-weather"},
    {"label": "Time", "icon": "⏰", "slug": "time"},
    {"label": "School & Learning", "icon": "📚", "slug": "school-learning"},
    {"label": "Work & Career", "icon": "💼", "slug": "work-career"},
    {"label": "Shopping & Money", "icon": "🛒", "slug": "shopping-money"},
    {"label": "Communication & Technology", "icon": "📱", "slug": "communication-technology"},
    {"label": "Animals", "icon": "🐾", "slug": "animals"},
    {"label": "Celebrations & Events", "icon": "🎉", "slug": "celebrations-events"},
    {"label": "Personal Items", "icon": "🎒", "slug": "personal-items"},
    {"label": "Questions & Interrogatives", "icon": "❓", "slug": "questions-interrogatives"},
    {"label": "Pronouns & Quantifiers", "icon": "👤", "slug": "pronouns-quantifiers"},
    {"label": "Banking & Finance", "icon": "🏦", "slug": "banking-finance"},
    {"label": "Media & Entertainment", "icon": "📺", "slug": "media-entertainment"},
    {"label": "Society & Politics", "icon": "🌍", "slug": "society-politics"},
    {"label": "Music & Arts", "icon": "🎵", "slug": "music-arts"},
    {"label": "Sports & Activities", "icon": "⚽", "slug": "sports-activities"},
    {"label": "Feelings & Emotions", "icon": "💭", "slug": "feelings-emotions"},
    {"label": "Prepositions & Particles", "icon": "📍", "slug": "prepositions-particles"},
    {"label": "Negation & Particles", "icon": "🚫", "slug": "negation-particles"},
    {"label": "Location & Direction", "icon": "🧭", "slug": "location-direction"},
    {"label": "Quantity & Degree", "icon": "📊", "slug": "quantity-degree"},
    {"label": "Reflexive & Self", "icon": "🔄", "slug": "reflexive-self"},
    {"label": "Manner & Style", "icon": "🎭", "slug": "manner-style"},
    {"label": "Places & Structures", "icon": "🏛️", "slug": "places-structures"},
    {"label": "Emergency & Safety", "icon": "🆘", "slug": "emergency-safety"},
    {"label": "Reason & Proof", "icon": "📋", "slug": "reason-proof"},
    {"label": "Tools & Materials", "icon": "🔧", "slug": "tools-materials"},
    {"label": "Start & Conclusion", "icon": "▶️", "slug": "start-conclusion"},
    {"label": "Writing & Recording", "icon": "✍️", "slug": "writing-recording"},
    {"label": "Legal & Crime", "icon": "⚖️", "slug": "legal-crime"},
    {"label": "People & Roles", "icon": "👥", "slug": "people-roles"},
    {"label": "Plans & Suggestions", "icon": "📝", "slug": "plans-suggestions"},
]

# The old catch-alls (about 1,000–2,000 words each) are split by part of speech
# and Pinyin initial. Noun, action-verb, and adjective bands stay at least 300
# words on the TOCFL 8000 list. Adverbs are one band because the whole set is
# under 300. Nouns are named Nouns, not Abstract.
NOUN_GROUPS = (
    ("A-D", "abcd"),
    ("E-J", "efghij"),
    ("K-Q", "klmnopq"),
    ("R-W", "rstuvw"),
    ("X-Z", "xyz"),
)
VERB_GROUPS = (
    ("A-F", "abcdef"),
    ("G-L", "ghijkl"),
    ("M-T", "mnopqrst"),
    ("U-Z", "uvwxyz"),
)
ADJECTIVE_GROUPS = (
    ("A-L", "abcdefghijkl"),
    ("M-Z", "mnopqrstuvwxyz"),
)
ADVERB_GROUPS = (
    ("A-Z", "abcdefghijklmnopqrstuvwxyz"),
)


def _band_categories(prefix: str, icon: str, slug: str, groups: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [
        {
            "label": f"{prefix} · {suffix}",
            "icon": icon,
            "slug": f"{slug}-{suffix.lower()}",
        }
        for suffix, _letters in groups
    ]


TAXONOMY.extend(_band_categories("Nouns", "📦", "nouns", NOUN_GROUPS))
TAXONOMY.extend(_band_categories("Action Verbs", "🏃", "action-verbs", VERB_GROUPS))
TAXONOMY.extend(_band_categories("Adjectives", "✨", "adjectives", ADJECTIVE_GROUPS))
TAXONOMY.extend(_band_categories("Adverbs", "🔗", "adverbs", ADVERB_GROUPS))
TAXONOMY.extend([
    {"label": "Connectors", "icon": "🔀", "slug": "connectors"},
    {"label": "Mental Verbs", "icon": "🧠", "slug": "mental-verbs"},
    {"label": "Separable Verbs", "icon": "🧩", "slug": "separable-verbs"},
    {"label": "Auxiliary Verbs", "icon": "🔧", "slug": "auxiliary-verbs"},
    {"label": "States & Conditions", "icon": "🌡️", "slug": "states-conditions"},
])

LABELS = [item["label"] for item in TAXONOMY]
LABEL_SET = set(LABELS)
LABEL_INDEX = {label: index for index, label in enumerate(LABELS)}
BY_SLUG = {item["slug"]: item for item in TAXONOMY}
GENERIC_LABELS = {
    "Prepositions & Particles",
}
RETIRED_CATCHALLS = {
    "Common Verbs",
    "Adjectives & Descriptors",
    "Adverbs & Connectors",
    "Abstract & Concepts",
}
CORE_FIELDS = (
    "id",
    "level",
    "levelCode",
    "traditional",
    "simplified",
    "pinyin",
    "english",
    "hindi",
    "partOfSpeech",
    "sourceSheet",
    "sourceRow",
    "categoryCode",
)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
SPACE_RE = re.compile(r"\s+")

# Official workbook labels and the previous semantic taxonomy.
SOURCE_MAP: dict[str, str | None] = {
    "Greetings & Introductions": "Greetings & Basics",
    "Basic Expressions": "Greetings & Basics",
    "Polite Expressions": "Greetings & Basics",
    "Greetings & Basic Expressions": "Greetings & Basics",
    "Questions & Answers": "Questions & Interrogatives",
    "Question Words": "Questions & Interrogatives",
    "Conversation": "Communication & Technology",
    "Pronouns": "Pronouns & Quantifiers",
    "Family": "Family & People",
    "People & Family": "Family & People",
    "People & Occupations": "People & Roles",
    "Friends & Social Life": "Family & People",
    "Dating & Relationships": "Family & People",
    "Daily Activities": "Common Verbs",
    "Home & Household": "House & Furniture",
    "Personal Items": "Personal Items",
    "Clothing": "Clothing",
    "Clothing & Personal Items": "Clothing",
    "Personal Care": "Health & Feelings",
    "Food": "Food",
    "Food & Drinks": "Food",
    "Drinks": "Drinks",
    "Cooking": "Kitchen Items",
    "Restaurants & Ordering Food": "Food",
    "Restaurants & Eating": "Food",
    "Shopping": "Shopping & Money",
    "Money & Prices": "Shopping & Money",
    "Money & Banking": "Banking & Finance",
    "Banking & Payments": "Banking & Finance",
    "Work & Office": "Work & Career",
    "Business": "Work & Career",
    "School & Education": "School & Learning",
    "Computers & Technology": "Communication & Technology",
    "Communication & Conversation": "Communication & Technology",
    "Technology & Internet": "Communication & Technology",
    "Transportation": "Travel & Transport",
    "Taiwan Transportation": "Travel & Transport",
    "Travel": "Travel & Transport",
    "Travel & Hotels": "Travel & Transport",
    "Airports & Flights": "Travel & Transport",
    "Directions & Locations": "Location & Direction",
    "Body": "Body Parts",
    "Health": "Health & Feelings",
    "Health & Body": "Health & Feelings",
    "Hospital & Medicine": "Health & Feelings",
    "Emergency & Safety": "Emergency & Safety",
    "Weather": "Nature & Weather",
    "Nature": "Nature & Weather",
    "Weather, Nature & Animals": "Nature & Weather",
    "Environment": "Nature & Weather",
    "Animals": "Animals",
    "Places & Buildings": "Places & Structures",
    "City & Community": "Places & City",
    "Taiwan Daily Life": "Places & City",
    "Government & Public Services": "Society & Politics",
    "Society & Culture": "Society & Politics",
    "Politics & Government": "Society & Politics",
    "Numbers": "Quantity & Degree",
    "Numbers & Counting": "Quantity & Degree",
    "Measure Words": "Quantity & Degree",
    "Time": "Time",
    "Time & Dates": "Time",
    "Dates & Calendar": "Time",
    "Frequency": "Quantity & Degree",
    "Common Verbs": "Common Verbs",
    "Adjectives": "Adjectives & Descriptors",
    "Adverbs": "Adverbs & Connectors",
    "Common Adverbs": "Adverbs & Connectors",
    "Conjunctions & Connectors": "Adverbs & Connectors",
    "Connectors & Grammar Words": "Adverbs & Connectors",
    "Prepositions": "Prepositions & Particles",
    "Grammar & Function Words": "Prepositions & Particles",
    "Abstract Concepts": "Abstract & Concepts",
    "Emotions & Personality": "Feelings & Emotions",
    "Feelings & Emotions": "Feelings & Emotions",
    "Economy & Finance": "Banking & Finance",
    "Science": "Abstract & Concepts",
    "Media & News": "Media & Entertainment",
    "Academic Vocabulary": "School & Learning",
    "Professional Vocabulary": "Work & Career",
    "Leisure, Sports & Hobbies": "Sports & Activities",
    "Relationships & Dating": "Family & People",
    "Taiwan Food": "Food",
    "Taiwan Shopping": "Shopping & Money",
    "Taiwan Work & Office": "Work & Career",
    "Taiwan Services & Government": "Society & Politics",
    "Other / Miscellaneous": None,
    "其他 · Other": None,
    "名詞 · Nouns": None,
    "常用動詞 · Common Verbs": "Common Verbs",
    "狀態與形容 · States & Adjectives": "Adjectives & Descriptors",
    "功能詞 · Function Words": "Prepositions & Particles",
    "功能詞": "Prepositions & Particles",
    "數量與量詞 · Numbers & Measure Words": "Quantity & Degree",
    "常用副詞 · Common Adverbs": "Adverbs & Connectors",
    "個人資料": "Family & People",
    "個人資料 · Personal Information": "Family & People",
    "與他人的關係": "Family & People",
    "與他人的關係 · Relationships": "Family & People",
    "房屋與家庭、環境": "House & Furniture",
    "房屋與家庭、環境 · Home & Environment": "House & Furniture",
    "日常生活": None,
    "日常生活 · Daily Life": None,
    "閒暇時間、娛樂": "Sports & Activities",
    "閒暇時間、娛樂 · Leisure & Entertainment": "Sports & Activities",
    "旅行": "Travel & Transport",
    "旅行 · Travel": "Travel & Transport",
    "健康及身體照護": "Health & Feelings",
    "健康及身體照護 · Health & Body Care": "Health & Feelings",
    "教育": "School & Learning",
    "教育 · Education": "School & Learning",
    "購物": "Shopping & Money",
    "購物 · Shopping": "Shopping & Money",
    "飲食": "Food",
    "飲食 · Food & Drink": "Food",
    "工作": "Work & Career",
    "工作 · Work": "Work & Career",
    "其他": None,
    "人物": "Family & People",
    "人物 · People": "Family & People",
    "形色": "Colors",
    "形色 · Shapes & Colors": "Colors",
    "數量": "Quantity & Degree",
    "數量 · Numbers": "Quantity & Degree",
    "時間": "Time",
    "時間 · Time": "Time",
    "生活": None,
    "生活 · Daily Life": None,
    "地方": "Places & City",
    "地方 · Places": "Places & City",
    "交通": "Travel & Transport",
    "交通 · Transportation": "Travel & Transport",
    "自然": "Nature & Weather",
    "自然 · Nature": "Nature & Weather",
    "程度": "Quantity & Degree",
    "程度 · Degree": "Quantity & Degree",
    "常用語": "Greetings & Basics",
    "常用語 · Common Expressions": "Greetings & Basics",
    "學校": "School & Learning",
    "居家用品": "House & Furniture",
    "休閒活動": "Sports & Activities",
    "處所": "Places & City",
    "心理活動": "Feelings & Emotions",
    "動物": "Animals",
    "家庭": "Family & People",
    "方位": "Location & Direction",
    "數字": "Quantity & Degree",
    "衣物飾品": "Clothing",
    "交通工具": "Travel & Transport",
    "職業": "People & Roles",
    "身體部位": "Body Parts",
    "人格特質": "Adjectives & Descriptors",
    "現象": "Nature & Weather",
    "手部動作": "Common Verbs",
    "健康": "Health & Feelings",
    "年月日星期": "Time",
    "自然環境": "Nature & Weather",
    "口部動作": "Common Verbs",
    "天氣": "Nature & Weather",
    "金錢": "Shopping & Money",
    "顏色": "Colors",
    "一般": None,
    "身體動作": "Common Verbs",
    "尺寸": "Quantity & Degree",
    "居家活動": "House & Furniture",
    "國家": "Places & City",
    "形狀": "Adjectives & Descriptors",
    "植物": "Nature & Weather",
    "語言": "School & Learning",
    "季節": "Time",
    "腳部動作": "Common Verbs",
    "祝福": "Greetings & Basics",
    "眼部動作": "Common Verbs",
    "鼻子動作": "Common Verbs",
}
SOURCE_MAP = {
    key: None if value in RETIRED_CATCHALLS else value
    for key, value in SOURCE_MAP.items()
}

RELATED_SECONDARIES = {
    "Food": ["Kitchen Items"],
    "Drinks": ["Food"],
    "Kitchen Items": ["Food", "House & Furniture"],
    "Body Parts": ["Health & Feelings"],
    "Health & Feelings": ["Body Parts"],
    "Feelings & Emotions": ["Health & Feelings"],
    "Travel & Transport": ["Places & City"],
    "Places & Structures": ["Places & City"],
    "Places & City": ["Places & Structures"],
    "Banking & Finance": ["Shopping & Money"],
    "Shopping & Money": ["Banking & Finance"],
    "Colors": [],
    "Family & People": ["People & Roles"],
    "People & Roles": ["Family & People", "Work & Career"],
    "Music & Arts": ["Media & Entertainment"],
    "Sports & Activities": ["Media & Entertainment"],
    "Clothing": ["Personal Items"],
    "Communication & Technology": ["Media & Entertainment"],
    "Legal & Crime": ["Society & Politics"],
    "Emergency & Safety": ["Health & Feelings"],
    "Writing & Recording": ["School & Learning"],
}

KEYWORD_RULES: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    ("Negation & Particles", ("不是", "沒有", "不要", "不必", "不用", "未能", "並非"), ("not", "never", "do not", "cannot")),
    ("Reflexive & Self", ("自己", "自我", "自身", "本人", "親自"), ("oneself", "myself", "yourself", "itself", "himself", "herself")),
    ("Questions & Interrogatives", ("什麼", "甚麼", "為什麼", "怎麼", "怎麼樣", "怎麼辦", "哪裡", "哪裏", "哪兒", "誰"), ("what", "which", "who", "where", "why", "how")),
    ("Greetings & Basics", ("你好", "您好", "再見", "早安", "晚安", "謝謝", "對不起", "沒關係", "不客氣", "不好意思", "請問", "歡迎"), ("hello", "goodbye", "thank you", "sorry", "excuse me", "welcome")),
    ("Colors", ("顏色", "紅色", "黃色", "白色", "黑色", "藍色", "綠色", "紫色", "粉色", "灰色", "彩色"), ("color", "colour", "yellow", "purple", "pink")),
    ("Family & People", ("爸爸", "媽媽", "父母", "父親", "母親", "哥哥", "弟弟", "姊姊", "姐姐", "妹妹", "兒子", "女兒", "孩子", "家人", "家庭", "爺爺", "奶奶", "叔叔", "阿姨", "姑姑", "丈夫", "妻子", "太太", "親戚", "兄弟", "姐妹", "孫子", "孫女"), ("father", "mother", "parent", "brother", "sister", "husband", "wife", "son", "daughter", "family", "uncle", "aunt", "grandfather", "grandmother")),
    ("Body Parts", ("身體", "頭髮", "眼睛", "耳朵", "鼻子", "嘴巴", "牙齒", "舌頭", "脖子", "肩膀", "手指", "肚子", "心臟", "皮膚"), ("body part", "head", "hand", "eye", "ear", "nose", "mouth", "leg", "foot", "arm", "hair", "face")),
    ("Health & Feelings", ("生病", "看病", "感冒", "醫院", "醫生", "醫師", "護士", "健康", "疾病", "疼痛", "發燒", "咳嗽", "診所"), ("health", "hospital", "medicine", "doctor", "nurse", "illness", "disease", "fever", "clinic", "patient")),
    ("Drinks", ("飲料", "喝茶", "咖啡", "果汁", "牛奶", "啤酒", "紅酒", "汽水", "可樂", "豆漿", "奶茶"), ("beverage", "coffee", "juice", "beer", "wine", "soda")),
    ("Kitchen Items", ("筷子", "叉子", "盤子", "杯子", "烤箱", "微波爐", "餐桌", "菜單", "湯匙"), ("chopstick", "fork", "plate", "fridge", "refrigerator", "oven", "spoon", "menu")),
    ("Food", ("吃飯", "早餐", "午餐", "晚餐", "米飯", "麵包", "水果", "蔬菜", "青菜", "餃子", "漢堡", "蛋糕", "點心", "甜點", "餐廳", "食堂"), ("food", "rice", "bread", "fruit", "vegetable", "noodle", "breakfast", "lunch", "dinner", "restaurant")),
    ("House & Furniture", ("房子", "房間", "客廳", "臥室", "浴室", "廁所", "廚房", "家具", "桌子", "椅子", "沙發", "窗戶", "樓梯", "電梯", "鄰居"), ("house", "home", "kitchen", "bedroom", "bathroom", "furniture", "table", "chair", "sofa", "apartment")),
    ("Clothing", ("衣服", "褲子", "裙子", "鞋子", "襪子", "帽子", "外套", "大衣", "襯衫", "西裝"), ("clothes", "clothing", "shirt", "pants", "dress", "shoe", "hat", "coat", "jacket", "sock")),
    ("Travel & Transport", ("飛機", "火車", "公車", "汽車", "捷運", "地鐵", "計程車", "高鐵", "腳踏車", "自行車", "機車", "摩托車", "車站", "機場", "旅行", "護照", "行李", "機票"), ("travel", "train", "taxi", "airplane", "airport", "flight", "subway", "metro", "bicycle", "passport", "luggage", "hotel")),
    ("Places & City", ("城市", "鄉下", "台灣", "臺灣", "中國", "美國", "日本", "公園", "夜市", "馬路", "十字路口"), ("city", "country", "taiwan", "village", "downtown")),
    ("Places & Structures", ("大樓", "建築", "教堂", "博物館", "圖書館", "體育館", "電影院", "旅館"), ("building", "bridge", "temple", "church", "museum", "library", "stadium", "cinema", "tower")),
    ("Nature & Weather", ("天氣", "下雨", "下雪", "太陽", "月亮", "星星", "森林", "春天", "夏天", "秋天", "冬天"), ("weather", "rain", "snow", "mountain", "river", "forest", "nature")),
    ("Animals", ("動物", "蚊子", "蝴蝶", "老虎", "獅子"), ("animal", "dog", "cat", "bird", "horse", "mosquito", "tiger", "lion", "insect")),
    ("Time", ("今天", "明天", "昨天", "今年", "明年", "去年", "現在", "以前", "以後", "早上", "下午", "晚上", "中午", "星期", "禮拜", "小時", "分鐘", "秒鐘", "日曆", "時候", "時間"), ("today", "tomorrow", "yesterday", "morning", "evening", "calendar", "o'clock")),
    ("School & Learning", ("學校", "學生", "老師", "教室", "考試", "功課", "作業", "課本", "大學", "小學", "中學", "上課", "下課", "學習", "教育", "漢字", "華語", "文法", "數學", "歷史", "學期"), ("school", "student", "teacher", "exam", "homework", "university", "college", "education", "grammar")),
    ("Work & Career", ("工作", "上班", "下班", "公司", "辦公室", "老闆", "老板", "同事", "職業", "薪水", "會議"), ("office", "company", "career", "salary", "profession", "occupation")),
    ("Shopping & Money", ("購物", "商店", "超市", "價錢", "價格", "便宜", "折扣", "商品"), ("shop", "store", "price", "cheap", "expensive", "discount", "supermarket")),
    ("Banking & Finance", ("銀行", "帳戶", "賬戶", "存款", "貸款", "利息", "匯率", "股票", "保險", "信用卡", "提款", "金融"), ("bank", "loan", "credit card", "finance", "atm")),
    ("Communication & Technology", ("電話", "手機", "電腦", "網路", "網絡", "上網", "網站", "郵件", "電子郵件", "簡訊", "軟體", "軟件"), ("phone", "computer", "internet", "email", "e-mail", "website", "software", "online")),
    ("Celebrations & Events", ("過年", "新年", "生日", "結婚", "婚禮", "節日", "慶祝", "派對", "宴會", "禮物", "春節"), ("birthday", "wedding", "festival", "celebrate", "holiday", "new year")),
    ("Personal Items", ("背包", "皮包", "錢包", "雨傘", "鑰匙", "手錶", "手表", "眼鏡"), ("wallet", "umbrella", "backpack")),
    ("Pronouns & Quantifiers", ("我們", "你們", "他們", "她們", "它們", "大家", "別人", "這個", "那個", "這些", "那些"), ("pronoun")),
    ("Media & Entertainment", ("電視", "電影", "報紙", "雜誌", "新聞", "廣播", "節目", "影片"), ("television", "movie", "newspaper", "magazine", "broadcast", "entertainment")),
    ("Society & Politics", ("政府", "政治", "社會", "總統", "選舉", "民主", "公民", "政策"), ("government", "politics", "society", "president", "election", "democracy", "citizen")),
    ("Music & Arts", ("音樂", "歌曲", "唱歌", "樂器", "鋼琴", "吉他", "美術", "藝術", "畫畫", "書法", "舞蹈"), ("music", "piano", "guitar", "calligraphy")),
    ("Sports & Activities", ("運動", "體育", "比賽", "足球", "籃球", "棒球", "網球", "游泳", "跑步", "慢跑", "興趣", "休閒"), ("sport", "soccer", "basketball", "baseball", "tennis", "hobby", "exercise")),
    ("Feelings & Emotions", ("喜歡", "快樂", "高興", "開心", "難過", "傷心", "生氣", "害怕", "緊張", "擔心", "愛情", "心情"), ("happy", "angry", "afraid", "emotion", "mood", "nervous")),
    ("Location & Direction", ("左邊", "右邊", "前面", "後面", "上面", "下面", "裡面", "裏面", "外面", "中間", "旁邊", "對面", "附近", "東方", "西方", "南方", "北方"), ("left", "right", "inside", "outside", "north", "south", "east", "west", "direction")),
    ("Quantity & Degree", ("多少", "一些", "一點", "全部", "所有", "一半", "非常", "極其", "幾乎", "大約"), ("measure word", "quantity", "amount")),
    ("Emergency & Safety", ("危險", "安全", "救命", "緊急", "事故", "火災", "報警"), ("emergency", "danger", "safety", "accident")),
    ("Reason & Proof", ("因為", "所以", "因此", "原因", "理由", "證據", "證明", "根據", "由於"), ("because", "therefore", "evidence")),
    ("Tools & Materials", ("工具", "材料", "木頭", "石頭", "金屬", "塑膠", "剪刀", "鎚子", "錘子", "釘子"), ("tool", "material", "plastic", "scissors", "hammer")),
    ("Start & Conclusion", ("開始", "結束", "完成", "首先", "最後", "總之", "起初", "終於"), ("begin", "finish", "finally", "conclusion")),
    ("Writing & Recording", ("寫字", "寫作", "作文", "記錄", "紀錄", "日記", "筆記", "抄寫", "書寫"), ("writing", "diary", "notebook")),
    ("Legal & Crime", ("法律", "法院", "律師", "犯罪", "罪犯", "小偷", "監獄", "審判", "合約", "合同"), ("legal", "court", "crime", "criminal", "prison", "contract")),
    ("People & Roles", ("司機", "服務員", "經理", "職業"), ("driver", "manager", "waiter", "occupation")),
    ("Plans & Suggestions", ("計畫", "計劃", "打算", "建議", "提議", "準備", "安排", "目標"), ("suggest", "prepare", "arrange")),
    ("Manner & Style", ("方式", "方法", "樣子", "態度", "風格", "仔細", "慢慢", "輕輕"), ("manner", "attitude", "carefully", "slowly")),
    ("Connectors", ("但是", "可是", "然後", "而且", "或者", "還是", "雖然", "如果", "要是"), ("however", "although", "therefore")),
    ("Prepositions & Particles", ("對於", "關於", "除了", "為了", "按照", "通過"), ("particle")),
]


def taxonomy_meta() -> dict[str, Any]:
    validate_taxonomy_definitions()
    return {
        "version": 1,
        "count": len(TAXONOMY),
        "categories": [
            {**item, "order": index + 1}
            for index, item in enumerate(TAXONOMY)
        ],
    }


def validate_taxonomy_definitions() -> None:
    labels = [item["label"] for item in TAXONOMY]
    slugs = [item["slug"] for item in TAXONOMY]
    icons = [item["icon"] for item in TAXONOMY]
    expected = len(TAXONOMY)
    alphabet = set("abcdefghijklmnopqrstuvwxyz")
    for name, groups in (
        ("noun", NOUN_GROUPS),
        ("action-verb", VERB_GROUPS),
        ("adjective", ADJECTIVE_GROUPS),
        ("adverb", ADVERB_GROUPS),
    ):
        covered = set("".join(letters for _suffix, letters in groups))
        if covered != alphabet:
            raise ValueError(f"{name} Pinyin bands must cover a–z")
    if len(TAXONOMY) != expected:
        raise ValueError(f"taxonomy must contain {expected} categories, found {len(TAXONOMY)}")
    if len(set(labels)) != expected:
        raise ValueError("taxonomy labels are not unique")
    if len(set(slugs)) != expected:
        raise ValueError("taxonomy slugs are not unique")
    if len(icons) != expected or any(not icon for icon in icons):
        raise ValueError("every taxonomy category needs an icon")
    if "Other / Miscellaneous" in labels or RETIRED_CATCHALLS & set(labels):
        raise ValueError("retired catch-all categories are not part of the taxonomy")
    for label, mapped in SOURCE_MAP.items():
        if mapped is not None and mapped not in LABEL_SET:
            raise ValueError(f"SOURCE_MAP target {mapped!r} for {label!r} is not in the taxonomy")
    for category, _zh, _en in KEYWORD_RULES:
        if category not in LABEL_SET:
            raise ValueError(f"keyword rule category {category!r} is not in the taxonomy")


def clean(value: object) -> str:
    return SPACE_RE.sub(" ", str(value or "").replace("\u00a0", " ")).strip()


def form_candidates(*values: str) -> list[str]:
    found: list[str] = []
    for value in values:
        parts = [value, *re.split(r"[/／]", value)]
        parts += [re.sub(r"[()（）]", "", item) for item in list(parts)]
        parts += [re.sub(r"[(（][^)）]*[)）]", "", item) for item in list(parts)]
        for item in parts:
            item = item.strip()
            if item and item not in found:
                found.append(item)
    return found


def map_source_label(label: str) -> str | None:
    text = clean(label)
    if not text:
        return None
    if text in LABEL_SET:
        return text
    if text in SOURCE_MAP:
        return SOURCE_MAP[text]
    if " · " in text:
        english = text.split(" · ", 1)[1].strip()
        if english in SOURCE_MAP:
            return SOURCE_MAP[english]
        if english in LABEL_SET:
            return english
        chinese = text.split(" · ", 1)[0].strip()
        if chinese in SOURCE_MAP:
            return SOURCE_MAP[chinese]
    return None


def source_evidence(word: dict[str, Any]) -> list[str]:
    labels = [
        word.get("category"),
        word.get("subcategory"),
        word.get("sourceCategory"),
        word.get("categoryCode"),
        *list(word.get("secondaryCategories") or []),
    ]
    mapped: list[str] = []
    for label in labels:
        category = map_source_label(clean(label))
        if category and category not in mapped:
            mapped.append(category)
    return mapped


def english_hit(term: str, haystack: str) -> bool:
    needle = term.strip().lower()
    if not needle:
        return False
    if needle.endswith(" "):
        return needle in f" {haystack} "
    return re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", haystack) is not None


def chinese_hit(term: str, forms: list[str], haystack: str) -> bool:
    if len(term) == 1:
        return term in forms
    return term in haystack or any(term in form for form in forms)


def keyword_matches(word: dict[str, Any]) -> list[str]:
    traditional = clean(word.get("traditional"))
    simplified = clean(word.get("simplified"))
    english = clean(word.get("english")).lower()
    forms = form_candidates(traditional, simplified)
    haystack = f"{traditional} {simplified}"
    hits: list[str] = []
    for category, chinese_terms, english_terms in KEYWORD_RULES:
        matched = False
        for term in chinese_terms:
            if chinese_hit(term, forms, haystack):
                matched = True
                break
        if not matched:
            for term in english_terms:
                if english_hit(term, english):
                    matched = True
                    break
        if matched and category not in hits:
            hits.append(category)
    return hits


def pinyin_initial(word: dict[str, Any]) -> str:
    raw = clean(word.get("pinyin")).split("/")[0]
    folded = unicodedata.normalize("NFD", raw).lower()
    letters = "".join(ch for ch in folded if "a" <= ch <= "z")
    return letters[:1] or "z"


def band_label(prefix: str, initial: str, groups: tuple[tuple[str, str], ...]) -> str:
    for suffix, letters in groups:
        if initial in letters:
            return f"{prefix} · {suffix}"
    return f"{prefix} · {groups[-1][0]}"


def pos_fallback(word: dict[str, Any]) -> str:
    pos = clean(word.get("partOfSpeech")).upper().replace("；", "/").replace(";", "/")
    tokens = [item.strip() for item in re.split(r"[/, ]+", pos) if item.strip()]
    joined = " ".join(tokens)
    initial = pinyin_initial(word)

    def starts(prefix: str) -> bool:
        return any(token.startswith(prefix) for token in tokens)

    if any(token in {"PRON", "PRONOUN"} for token in tokens):
        return "Pronouns & Quantifiers"
    if "DET" in tokens:
        return "Pronouns & Quantifiers"
    if any(token in {"CONJ"} for token in tokens):
        return "Connectors"
    if any(token in {"ADV"} for token in tokens):
        return band_label("Adverbs", initial, ADVERB_GROUPS)
    if any(token in {"PREP", "PTC", "PARTICLE", "ASP", "BA", "BEI", "AFFIX"} for token in tokens):
        return "Prepositions & Particles"
    if any(token in {"M", "NUM"} for token in tokens):
        return "Quantity & Degree"
    if starts("VST"):
        return "States & Conditions"
    if any("SEP" in token for token in tokens):
        return "Separable Verbs"
    if starts("VS") or any(token in {"ADJ", "A"} for token in tokens):
        return band_label("Adjectives", initial, ADJECTIVE_GROUPS)
    if starts("VAUX"):
        return "Auxiliary Verbs"
    if starts("VP"):
        return "Mental Verbs"
    if starts("V"):
        return band_label("Action Verbs", initial, VERB_GROUPS)
    if "INT" in joined or "INTERJ" in joined:
        return "Greetings & Basics"
    return band_label("Nouns", initial, NOUN_GROUPS)


def pick_primary(mapped: list[str], keywords: list[str], pos_category: str) -> tuple[str, str]:
    mapped_specific = [item for item in mapped if item not in GENERIC_LABELS]
    keyword_specific = [item for item in keywords if item not in GENERIC_LABELS]

    if keyword_specific and mapped_specific:
        overlap = [item for item in keyword_specific if item in mapped_specific]
        if overlap:
            return overlap[0], "mapped source category refined by row fields"
        return keyword_specific[0], "refined source category by row fields"
    if keyword_specific:
        return keyword_specific[0], "row field keyword"
    if mapped_specific:
        return mapped_specific[0], "mapped existing/source category"
    if mapped:
        if keywords:
            return keywords[0], "refined generic category by row fields"
        return mapped[0], "mapped existing/source category"
    if keywords:
        return keywords[0], "row field keyword"
    return pos_category, "part-of-speech fallback"


def collect_secondaries(primary: str, mapped: list[str], keywords: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in [*keywords, *mapped, *RELATED_SECONDARIES.get(primary, [])]:
        if item != primary and item in LABEL_SET and item not in ordered:
            ordered.append(item)
    return ordered[:3]


def workbook_label(word: dict[str, Any]) -> bool:
    for field in ("subcategory", "sourceCategory", "categoryCode"):
        value = clean(word.get(field))
        if value and (CJK_RE.search(value) or value in SOURCE_MAP):
            chinese_only = bool(CJK_RE.search(value)) and value not in LABEL_SET
            if chinese_only or value in SOURCE_MAP:
                return True
    return False


def preserve_source_metadata(word: dict[str, Any]) -> None:
    subcategory = clean(word.get("subcategory"))
    source_category = clean(word.get("sourceCategory"))
    if not source_category and subcategory:
        mapped_label = None
        for key, bilingual in {
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
        }.items():
            if subcategory == key:
                mapped_label = bilingual
                break
        if mapped_label:
            word["sourceCategory"] = mapped_label


def classify_row(word: dict[str, Any]) -> tuple[str, list[str], str]:
    mapped = source_evidence(word)
    keywords = keyword_matches(word)
    pos_category = pos_fallback(word)
    primary, basis = pick_primary(mapped, keywords, pos_category)
    if primary not in LABEL_SET:
        primary = pos_category
        basis = "part-of-speech fallback"
    secondary = collect_secondaries(primary, mapped, keywords)
    return primary, secondary, basis


def apply_taxonomy(word: dict[str, Any]) -> dict[str, Any]:
    preserve_source_metadata(word)
    keep_subcategory = bool(CJK_RE.search(clean(word.get("subcategory"))))
    primary, secondary, basis = classify_row(word)
    word["category"] = primary
    word["secondaryCategories"] = secondary
    word["categoryBasis"] = basis
    if not keep_subcategory:
        word["subcategory"] = primary
    return word


def snapshot_core(word: dict[str, Any]) -> tuple:
    return tuple(word.get(field) for field in CORE_FIELDS)


def validate_assignments(words: list[dict[str, Any]], expected_count: int | None = None) -> None:
    validate_taxonomy_definitions()
    if expected_count is not None and len(words) != expected_count:
        raise ValueError(f"expected {expected_count} rows, found {len(words)}")
    invalid = [
        word.get("id")
        for word in words
        if word.get("category") not in LABEL_SET
        or any(item not in LABEL_SET for item in word.get("secondaryCategories") or [])
        or not clean(word.get("categoryBasis"))
    ]
    if invalid:
        raise ValueError(f"{len(invalid)} rows have invalid taxonomy assignments, e.g. {invalid[:5]}")
    leftover = [word.get("id") for word in words if word.get("category") == "Other / Miscellaneous"]
    if leftover:
        raise ValueError("Other / Miscellaneous remains after taxonomy assignment")


def apply_taxonomy_to_payload(payload: dict[str, Any], expected_count: int | None = None) -> dict[str, Any]:
    words = payload["words"]
    before = [snapshot_core(word) for word in words]
    workbook_subcats = [clean(word.get("subcategory")) for word in words]
    source_categories = [word.get("sourceCategory") for word in words]
    category_codes = [word.get("categoryCode") for word in words]
    for word in words:
        apply_taxonomy(word)
    after = [snapshot_core(word) for word in words]
    if before != after:
        raise ValueError("core word/level/source fields changed during taxonomy assignment")
    for word, original in zip(words, workbook_subcats):
        if CJK_RE.search(original) and clean(word.get("subcategory")) != original:
            raise ValueError(f"workbook subcategory changed for {word.get('id')}")
    for word, original in zip(words, source_categories):
        if original and word.get("sourceCategory") != original:
            raise ValueError(f"sourceCategory changed for {word.get('id')}")
    for word, original in zip(words, category_codes):
        if original and word.get("categoryCode") != original:
            raise ValueError(f"categoryCode changed for {word.get('id')}")
    expected = expected_count if expected_count is not None else payload.get("meta", {}).get("wordCount")
    validate_assignments(words, expected)
    payload.setdefault("meta", {})
    payload["meta"]["taxonomy"] = taxonomy_meta()
    payload["meta"]["taxonomyAssignmentCount"] = len(words)
    return payload


def write_dataset(payload: dict[str, Any], json_path: Path, js_path: Path, global_name: str) -> None:
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    js_path.write_text(
        f"window.{global_name} = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


def write_taxonomy_js(path: Path) -> None:
    payload = taxonomy_meta()
    path.write_text(
        "window.__CATEGORY_TAXONOMY__ = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


def remap_existing_datasets() -> None:
    validate_taxonomy_definitions()
    datasets = [
        (ROOT / "data" / "tocfl-8000.json", ROOT / "data" / "tocfl-8000.js", "__TOCFL_8000__", 7517),
        (ROOT / "data" / "tocfl-cccc.json", ROOT / "data" / "tocfl-cccc.js", "__TOCFL_CCCC__", 1197),
    ]
    for json_path, js_path, global_name, expected in datasets:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        apply_taxonomy_to_payload(payload, expected)
        write_dataset(payload, json_path, js_path, global_name)
        print(f"Remapped {json_path.name}: {expected} rows, {len(TAXONOMY)} categories")
    write_taxonomy_js(ROOT / "js" / "category-taxonomy.js")
    print("Wrote js/category-taxonomy.js")


if __name__ == "__main__":
    remap_existing_datasets()
