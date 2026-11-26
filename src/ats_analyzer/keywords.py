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
    "skills", "knowledge", "understanding", "ability", "need", "needs", "help", "new",
    "like", "well", "within", "across", "into", "make", "based", "one", "get", "per",
    "company", "opportunity", "opportunities", "apply", "position", "salary", "benefits",
    "equal", "employer", "applicants", "hiring", "location", "remote", "hybrid", "office",
    "full", "time", "part", "day", "days", "week", "weeks", "month", "months", "is",
    "are", "were", "was", "been", "being", "do", "does", "did", "not", "no", "nice",
    "bonus", "required", "require", "requires", "minimum", "least", "preferably",
    "qualification", "qualifications", "degree", "bachelor", "master", "bachelors",
    "masters", "field", "related", "similar", "etc.", "e.g", "i.e", "you'll", "we're",
    "have", "having", "both", "each", "how", "if", "when", "where", "while", "than",
    "then", "these", "those", "out", "up", "over", "very", "just", "only", "own",
    "same", "so", "too", "most", "some", "few", "here", "there", "why", "us",
}

# Keeps tech names like "c++", "c#", "node.js", "ci/cd".
TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./-]*[a-zA-Z0-9+#]|[a-zA-Z]")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_PATTERN.findall(text)]


def stem(word: str) -> str:
    """Very small stemmer so 'deploy', 'deployed', 'deploying', 'deployment' match."""
    for suffix in ("ments", "ment", "ations", "ation", "ing", "ers", "er", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    """Return the most frequent non-stopword terms (single words + two-word phrases)."""
    words = [w for w in tokenize(text) if w not in STOPWORDS and len(w) > 1]
    bigrams = [f"{a} {b}" for a, b in zip(words, words[1:])]

    counts = Counter(words)
    # Only keep phrases that appear more than once - they are likely real terms.
    counts.update({b: c for b, c in Counter(bigrams).items() if c > 1})
    return [term for term, _ in counts.most_common(top_n)]
