"""
Helpers for cleaning scraped job description text.

Job boards hand back descriptions as escaped HTML, so the raw string is markup
rather than prose. Anything that pattern-matches on the text — skill extraction,
salary parsing — has to clean it first or it matches the markup instead.
"""

import html
import re
from collections import Counter

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_html(text: str | None) -> str:
    """
    Turn escaped job-board HTML into plain text.

    Unescapes twice on purpose: the payload arrives escaped once at the tag
    level (`&lt;div&gt;`), but entities *inside* those tags were already escaped
    before that, so they come through as `&amp;mdash;` and need a second pass.
    One unescape leaves literal `&mdash;` sitting in the prose; the missing
    second pass is also why salary ranges were unparseable, since the separator
    between the two figures never resolved to a dash.
    """
    if not text:
        return ""
    unescaped = html.unescape(html.unescape(text))
    without_tags = _TAG_RE.sub(" ", unescaped)
    return _WHITESPACE_RE.sub(" ", without_tags).strip()


# Sentences that name customers rather than requirements, e.g. Brex's
# "Tens of thousands of the world's best companies run on Brex, including
# DoorDash, Coinbase, Robinhood, Zoom, Plaid, Reddit, and SeatGeek."
_CUSTOMER_CUE = re.compile(
    r"\b("
    r"customers? include|clients? include|including|trusted by|used by|powers?|"
    r"run on|companies like|brands like|such as|partners? include|"
    r"backing from|backed by|investors? include"
    r")\b",
    re.IGNORECASE,
)

# A run of Proper-Noun items separated by commas — the shape of a brand list.
_PROPER_NOUN_LIST = re.compile(
    r"(?:[A-Z][\w&.\-]*(?:\s[A-Z][\w&.\-]*)?)"      # a capitalised name
    r"(?:\s*,\s*(?:and\s+)?"                          # , or , and
    r"(?:[A-Z][\w&.\-]*(?:\s[A-Z][\w&.\-]*)?)){2,}"  # at least 3 names total
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

MIN_LIST_NAMES = 3


def strip_customer_lists(text: str, protected: set[str] | None = None) -> str:
    """
    Drop sentences that exist only to name-drop customers, investors or partners.

    These are boilerplate repeated across every posting at a company, and they
    poison skill extraction: Brex's blurb names Zoom and Plaid, so all 302 Brex
    postings looked like they wanted Zoom experience. Blocklisting "Zoom" would
    be endless whack-a-mole and would also drop genuine mentions, so this
    targets the *shape* of the sentence instead — a name-drop cue plus a run of
    at least three comma-separated proper nouns.

    `protected` names are never sacrificed: "tooling including Python, Docker,
    and Kubernetes" trips the same shape as a customer list, so a sentence that
    mentions a real tracked skill is always kept.
    """
    if not text:
        return ""

    protected = protected or set()
    kept = []

    for sentence in _SENTENCE_SPLIT.split(text):
        if _CUSTOMER_CUE.search(sentence):
            match = _PROPER_NOUN_LIST.search(sentence)
            if match and len(match.group(0).split(",")) >= MIN_LIST_NAMES:
                lowered = sentence.lower()
                mentions_real_skill = any(
                    re.search(r"\b" + re.escape(name.lower()) + r"\b", lowered)
                    for name in protected
                )
                if not mentions_real_skill:
                    continue  # boilerplate name-drop — drop the whole sentence
        kept.append(sentence)

    return " ".join(kept).strip()


# A sentence has to repeat across most of a company's postings before it counts
# as boilerplate. Genuine requirements vary by role — even a very technical
# company posts sales, finance and legal roles — so a sentence reproduced
# *verbatim* across most of them is company copy, not a job requirement.
# 0.6 rather than 0.9: Coinbase's AI-usage policy paragraph sits in 68% of its
# postings and was single-handedly supplying 159 "Generative AI" matches.
BOILERPLATE_THRESHOLD = 0.6
BOILERPLATE_MIN_DOCS = 8
_MIN_BOILERPLATE_CHARS = 40


def _normalise_sentence(sentence: str) -> str:
    return _WHITESPACE_RE.sub(" ", sentence).strip().lower()


def build_boilerplate_index(texts: list[str]) -> set[str]:
    """
    Find sentences repeated across nearly all of one company's postings.

    Customer-name lists are only one flavour of boilerplate. Verkada's "Who We
    Are" blurb mentions "our agentic AI" in all 275 of its postings, which was
    enough to rank Agentic AI the third most in-demand skill in the entire
    dataset. Figma's blurb names Figma. These are marketing copy, not
    requirements, and no per-term blocklist would catch them all.
    """
    if len(texts) < BOILERPLATE_MIN_DOCS:
        return set()

    counts: Counter[str] = Counter()
    for text in texts:
        seen = {
            _normalise_sentence(s)
            for s in _SENTENCE_SPLIT.split(text)
            if len(s.strip()) >= _MIN_BOILERPLATE_CHARS
        }
        counts.update(seen)

    cutoff = BOILERPLATE_THRESHOLD * len(texts)
    return {sentence for sentence, n in counts.items() if n >= cutoff}


def strip_boilerplate(text: str, boilerplate: set[str]) -> str:
    """Remove sentences flagged by build_boilerplate_index."""
    if not text or not boilerplate:
        return text
    kept = [
        s
        for s in _SENTENCE_SPLIT.split(text)
        if _normalise_sentence(s) not in boilerplate
    ]
    return " ".join(kept).strip()


def clean_for_extraction(text: str | None, boilerplate: set[str] | None = None) -> str:
    """
    Full pre-extraction pipeline: unescape, strip tags, drop name-drop lists,
    then drop any company-wide boilerplate the caller has identified.
    """
    # Imported here to keep this module free of a hard dependency on the
    # taxonomy at import time.
    from app.pipeline.skill_extractor import TRACKED_SKILL_NAMES

    cleaned = strip_customer_lists(clean_html(text), protected=TRACKED_SKILL_NAMES)
    if boilerplate:
        cleaned = strip_boilerplate(cleaned, boilerplate)
    return cleaned
