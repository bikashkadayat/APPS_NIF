"""
Server-side HTML sanitization for memo bodies.

The memo body is authored in a rich-text editor (TipTap) and stored as an HTML
string. Because any authenticated user can author a memo and that HTML is later
rendered to other users (checker/approver/admin) in the browser and into the
generated PDF, the raw HTML is an untrusted input and MUST be sanitized before
it is persisted (stored-XSS surface).

We sanitize on write (authoritative) with an allowlist that mirrors exactly what
the editor toolbar can produce; the frontend additionally sanitizes on render as
defense in depth. Scripts, event-handler attributes and dangerous URL schemes
(javascript:, data:) are stripped, and every link is forced to
rel="noopener noreferrer nofollow" target="_blank".
"""
import bleach

# Tags the TipTap StarterKit + Link toolbar can emit.
ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u",
    "h2", "h3",
    "ul", "ol", "li",
    "a", "blockquote",
]
ALLOWED_ATTRS = {"a": ["href", "title", "rel", "target"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def _safe_link(attrs, new=False):
    """linkify callback: force safe rel/target on every anchor."""
    attrs[(None, "rel")] = "noopener noreferrer nofollow"
    attrs[(None, "target")] = "_blank"
    return attrs


def sanitize_memo_html(raw):
    """
    Return a sanitized copy of ``raw`` HTML safe to store and render.

    Strips any tag/attribute outside the allowlist (``strip=True``), removes
    event-handler attributes and neutralizes non-http(s)/mailto URL schemes,
    then hardens every anchor's rel/target. Returns "" for falsy input.
    """
    if not raw:
        return ""
    cleaned = bleach.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return bleach.linkify(cleaned, callbacks=[_safe_link])
