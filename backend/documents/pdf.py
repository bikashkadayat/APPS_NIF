"""PDF rendering + QR helpers shared by the memo/leave document endpoints."""
import base64
import io

from django.conf import settings
from django.template.loader import render_to_string


def qr_data_uri(url):
    """Return a base64 PNG data-URI QR code for `url` (embeddable in HTML)."""
    import qrcode

    img = qrcode.make(url, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def verify_url(document_number):
    base = getattr(settings, "SITE_URL", "http://localhost:8001").rstrip("/")
    return f"{base}/api/v1/verify/{document_number}/"


def logo_data_uri():
    """Base64 data-URI of the NIF logo so it embeds in the PDF (never a broken
    link). Cached at module level after first read."""
    global _LOGO_CACHE
    try:
        return _LOGO_CACHE
    except NameError:
        pass
    from pathlib import Path

    candidates = [
        Path(settings.BASE_DIR) / "documents" / "assets" / "nif-logo.png",
        Path(settings.BASE_DIR) / "static" / "branding" / "nif-logo.png",
    ]
    uri = None
    for p in candidates:
        if p.exists():
            uri = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
            break
    _LOGO_CACHE = uri
    return uri


def common_context(document_number):
    """Letterhead + QR verification context shared by every PDF template."""
    from django.utils import timezone

    from config.nepali_dates import to_bs

    now = timezone.now()
    url = verify_url(document_number)
    return {
        "org": getattr(settings, "ORG_INFO", {}),
        "logo": logo_data_uri(),
        "document_number": document_number,
        "verify_url": url,
        "verify_qr": qr_data_uri(url),
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "issue_date": now.strftime("%Y-%m-%d"),
        "issue_date_bs": to_bs(now.date()),
    }


def render_pdf(template_name, context):
    """Render a template to PDF bytes via weasyprint."""
    import weasyprint

    html = render_to_string(template_name, context)
    # base_url lets weasyprint resolve any relative static asset references.
    return weasyprint.HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()
