import re
from collections import Counter

STOPWORDS = {
    "about","after","again","against","among","because","before","being","between",
    "could","during","each","from","have","into","more","most","other","should",
    "such","than","that","their","there","these","they","this","through","under",
    "using","were","which","while","with","would","your","shall","will","also",
    "where","when","what","whose","whose","then","them","some","many","only",
    "very","does","not","and","for","the","are","was","you","our","can","has",
    "had","but","all","any","its","how","why","who","use","may","per","one","two"
}

def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()

def extract_topics(text: str, max_topics: int = 8):
    lines = [clean_line(x) for x in text.splitlines() if clean_line(x)]
    candidates = []

    # Prefer likely headings.
    for line in lines:
        words = line.split()
        if len(words) <= 10 and len(line) <= 90:
            if (
                re.match(r"^(unit|chapter|module|topic|section)\s*[\dIVX.-]*", line, re.I)
                or line.isupper()
                or (len(words) <= 6 and not line.endswith("."))
            ):
                candidates.append(line)

    # Keyword fallback.
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text.lower())
    freq = Counter(t for t in tokens if t not in STOPWORDS and not t.isdigit())
    keywords = [w for w, _ in freq.most_common(30)]

    normalized = []
    seen = set()
    for item in candidates + keywords:
        item = clean_line(item)
        key = item.lower()
        if len(item) < 3 or key in seen:
            continue
        seen.add(key)
        normalized.append(item)
        if len(normalized) >= max_topics:
            break

    if not normalized:
        normalized = ["General Concepts"]

    return normalized[:max_topics]

def keywords_for_topic(topic: str, text: str):
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", topic.lower())
    return ", ".join(dict.fromkeys(words))
