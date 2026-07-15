"""Signed, expiring URLs for ALL user-uploaded media (memo attachments/vouchers,
profile photos, generated report files).

Why signed URLs: the SPA authenticates with a Bearer JWT header, which a browser
cannot attach to a native <img>/<a> file request. The old design left an
unauthenticated ``/media/`` catch-all open to work around that — exposing every
upload. Instead, the server issues short-lived HMAC-signed URLs (only to
already-authenticated/authorized requests, e.g. inside a memo serializer that ran
CanViewMemo), and this view validates the signature — no header needed, nothing
public.
"""
import hashlib
import hmac
import time
from urllib.parse import urlencode

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponseForbidden
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


def _sign(name, exp):
    msg = f"{name}|{exp}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def signed_media_url(name, *, ttl=None, download=False):
    """Return a header-free, expiring URL for the stored file `name` (its storage
    path, e.g. 'profiles/2026/07/x.png'). None if there is no file. Callers must
    already have authorized the requester (this only proves the server issued it)."""
    if not name:
        return None
    ttl = int(ttl if ttl is not None else getattr(settings, "MEDIA_SIGNED_URL_TTL", 3600))
    exp = int(time.time()) + ttl
    q = {"p": name, "e": exp, "s": _sign(name, exp)}
    if download:
        q["dl"] = "1"
    return f"/api/v1/media/?{urlencode(q)}"


class ProtectedMediaView(APIView):
    """Streams a stored file ONLY when the HMAC signature + expiry validate.
    Auth is the signature (header-free), so this replaces the public /media/ route."""
    permission_classes = [AllowAny]     # signature is the credential
    authentication_classes = []

    def get(self, request):
        name = request.query_params.get("p", "")
        exp = request.query_params.get("e", "")
        sig = request.query_params.get("s", "")
        if not (name and exp and sig):
            return HttpResponseForbidden("Missing media signature.")
        try:
            expired = int(exp) < int(time.time())
        except (TypeError, ValueError):
            return HttpResponseForbidden("Invalid media signature.")
        if expired:
            return HttpResponseForbidden("Media link has expired.")
        if not hmac.compare_digest(sig, _sign(name, exp)):
            return HttpResponseForbidden("Invalid media signature.")
        # Defense in depth against path traversal / absolute paths.
        if ".." in name or name.startswith("/") or name.startswith("\\"):
            return HttpResponseForbidden("Invalid media path.")
        if not default_storage.exists(name):
            raise Http404("File not found.")

        download = request.query_params.get("dl") == "1"
        resp = FileResponse(
            default_storage.open(name, "rb"),
            as_attachment=download,
            filename=name.rsplit("/", 1)[-1],
        )
        # Never let an uploaded HTML/SVG execute in the app origin.
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Content-Security-Policy"] = "default-src 'none'; sandbox"
        resp["Referrer-Policy"] = "no-referrer"
        return resp
