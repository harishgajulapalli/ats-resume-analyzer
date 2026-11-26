"""Step 2: Pull meaningful keywords out of text."""

import re
from collections import Counter

# Common words that carry no meaning for matching.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "its", "of", "on", "or", "our", "that", "the", "their", "this",
    "to", "we", "will", "with", "you", "your", "they", "who", "what", "which", "can",
    "able", "work", "working", "experience", "years", "year", "strong", "good",
    "team", "role", "job", "candidate", "including", "using", "use", "etc", "plus",
    "must", "should", "would", "also", "all", "any", "more", "other", "such", "about",
    "looking", "requirements", "responsibilities", "preferred", "ideal", "join",
}

# Keeps tech names like "c++", "c#", "node.js", "ci/cd".
TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./-]*[a-zA-Z0-9+#]|[a-zA-Z]")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_PATTERN.findall(text)]


def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    """Return the most frequent non-stopword terms (single words + two-word phrases)."""
    words = [w for w in tokenize(text) if w not in STOPWORDS and len(w) > 1]
    bigrams = [f"{a} {b}" for a, b in zip(words, words[1:])]

    counts = Counter(words)
    # Only keep phrases that appear more than once - they are likely real terms.
    counts.update({b: c for b, c in Counter(bigrams).items() if c > 1})
    return [term for term, _ in counts.most_common(top_n)]
