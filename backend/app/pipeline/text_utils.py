"""
Helpers for cleaning scraped job description text.

Job boards hand back descriptions as escaped HTML, so the raw string is markup
rather than prose. Anything that pattern-matches on the text — skill extraction,
salary parsing — has to clean it first or it matches the markup instead.
"""

import html
import re

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
