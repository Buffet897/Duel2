"""OutfitDuel Sprint 2 — security, reports, rate limiting tests.

Each test uses a unique X-Forwarded-For IP to avoid cross-test rate-limit
interference (server reads first hop). Rate-limit tests use a stable IP
on purpose.
"""

from __future__ import annotations

import io
import os
import uuid

import pytest
import requests
from PIL import Image
from PIL.ExifTags import TAGS

def _load_frontend_env():
    """Load REACT_APP_BACKEND_URL from /app/frontend/.env if not in env."""
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("REACT_APP_BACKEND_URL="):
                    os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
                    return


_load_frontend_env()
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---------------------- helpers ----------------------

def fake_ip() -> str:
    h = uuid.uuid4().int
    return f"10.{(h >> 16) & 0xFF}.{(h >> 8) & 0xFF}.{h & 0xFF}"


def hdr(ip: str | None = None) -> dict:
    return {"X-Forwarded-For": ip or fake_ip()}


def jpeg_bytes(color=(255, 0, 0), size=(800, 1000), with_exif=False) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    if with_exif:
        # Minimal valid EXIF block (PIL writes via exif kwarg)
        exif = img.getexif()
        exif[0x010F] = "TestCameraMakerXYZ"  # Make
        exif[0x0110] = "TestModelABC"  # Model
        img.save(buf, format="JPEG", quality=85, exif=exif.tobytes())
    else:
        img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def png_bytes(color=(0, 200, 100), size=(800, 1000)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def webp_bytes(color=(50, 60, 200), size=(800, 1000)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    return buf.getvalue()


def create_duel(ip: str | None = None, photo_a=None, photo_b=None, q="TEST_sprint2") -> dict:
    files = {
        "photo_a": ("a.jpg", photo_a or jpeg_bytes(), "image/jpeg"),
        "photo_b": ("b.jpg", photo_b or jpeg_bytes((0, 100, 255)), "image/jpeg"),
    }
    r = requests.post(
        f"{API}/duels", files=files, data={"question": q}, headers=hdr(ip), timeout=30
    )
    return r


# ---------------------- security headers ----------------------

class TestSecurityHeaders:
    @pytest.mark.parametrize("path", ["/api/", "/api/duels/popular", "/api/stats/weekly"])
    def test_security_headers_present(self, path):
        r = requests.get(f"{BASE_URL}{path}", headers=hdr(), timeout=10)
        assert r.status_code == 200
        h = {k.lower(): v for k, v in r.headers.items()}
        assert "content-security-policy" in h
        assert h.get("x-content-type-options", "").lower() == "nosniff"
        assert h.get("x-frame-options", "").upper() == "DENY"
        assert h.get("referrer-policy") == "strict-origin-when-cross-origin"


# ---------------------- upload validation ----------------------

class TestUploadValidation:
    def test_reject_non_image_mime(self):
        files = {
            "photo_a": ("a.txt", b"hello world this is text", "text/plain"),
            "photo_b": ("b.jpg", jpeg_bytes(), "image/jpeg"),
        }
        r = requests.post(f"{API}/duels", files=files, data={"question": "x"}, headers=hdr(), timeout=30)
        assert r.status_code == 400
        assert "niet toegestaan" in r.json().get("detail", "").lower()

    def test_reject_oversized_file(self):
        # 11 MB random-ish bytes (not a real image but size check happens before pillow)
        big = b"\xff" * (11 * 1024 * 1024)
        files = {
            "photo_a": ("a.jpg", big, "image/jpeg"),
            "photo_b": ("b.jpg", jpeg_bytes(), "image/jpeg"),
        }
        r = requests.post(f"{API}/duels", files=files, data={"question": "x"}, headers=hdr(), timeout=60)
        assert r.status_code == 400
        assert "10mb" in r.json().get("detail", "").lower() or "groter" in r.json().get("detail", "").lower()

    def test_accept_png(self):
        r = create_duel(photo_a=png_bytes(), photo_b=png_bytes((0, 0, 255)))
        assert r.status_code == 200, r.text
        d = r.json()
        # cleanup
        requests.delete(f"{API}/duels/{d['id']}", params={"token": d["delete_token"]}, timeout=10)

    def test_accept_webp(self):
        r = create_duel(photo_a=webp_bytes(), photo_b=webp_bytes((200, 50, 50)))
        assert r.status_code == 200, r.text
        d = r.json()
        requests.delete(f"{API}/duels/{d['id']}", params={"token": d["delete_token"]}, timeout=10)

    def test_exif_stripped(self):
        src = jpeg_bytes(with_exif=True)
        # Sanity: source HAS exif
        src_img = Image.open(io.BytesIO(src))
        src_exif = src_img.getexif()
        assert any(TAGS.get(k) in ("Make", "Model") for k in src_exif.keys()), "source JPEG should have EXIF"

        r = create_duel(photo_a=src, photo_b=jpeg_bytes((0, 255, 0)))
        assert r.status_code == 200, r.text
        d = r.json()
        url = d["photo_a_url"]
        if url.startswith("/"):
            url = f"{BASE_URL}{url}"
        img_resp = requests.get(url, timeout=15)
        assert img_resp.status_code == 200
        saved = Image.open(io.BytesIO(img_resp.content))
        saved_exif = saved.getexif()
        # Verify Make/Model NOT in saved EXIF
        saved_tags = {TAGS.get(k) for k in saved_exif.keys()}
        assert "Make" not in saved_tags and "Model" not in saved_tags
        requests.delete(f"{API}/duels/{d['id']}", params={"token": d["delete_token"]}, timeout=10)


# ---------------------- report system ----------------------

class TestReportSystem:
    def test_invalid_reason_400(self):
        # need a duel
        r = create_duel()
        assert r.status_code == 200
        duel_id = r.json()["id"]
        rep = requests.post(
            f"{API}/duels/{duel_id}/report",
            data={"reason": "bogus"},
            headers=hdr(),
            timeout=10,
        )
        assert rep.status_code == 400
        # cleanup
        requests.delete(f"{API}/duels/{duel_id}", params={"token": r.json()["delete_token"]}, timeout=10)

    def test_report_dedup_same_ip(self):
        r = create_duel()
        duel_id = r.json()["id"]
        ip = fake_ip()
        r1 = requests.post(f"{API}/duels/{duel_id}/report", data={"reason": "spam"}, headers=hdr(ip), timeout=10)
        assert r1.status_code == 200
        assert r1.json().get("report_count") == 1
        # Same IP again → deduped
        r2 = requests.post(f"{API}/duels/{duel_id}/report", data={"reason": "spam"}, headers=hdr(ip), timeout=10)
        assert r2.status_code == 200
        assert r2.json().get("deduped") is True
        # confirm count unchanged
        g = requests.get(f"{API}/duels/{duel_id}", headers=hdr(), timeout=10)
        assert g.status_code == 200
        # is_hidden still false
        assert g.json().get("is_hidden") is False
        requests.delete(f"{API}/duels/{duel_id}", params={"token": r.json()["delete_token"]}, timeout=10)

    def test_3_reports_auto_hide_and_excluded_from_popular(self):
        r = create_duel(q="TEST_to_hide")
        duel_id = r.json()["id"]
        token = r.json()["delete_token"]

        for i, reason in enumerate(["offensive", "no_consent", "spam"]):
            rep = requests.post(
                f"{API}/duels/{duel_id}/report",
                data={"reason": reason},
                headers=hdr(),  # unique IP each time
                timeout=10,
            )
            assert rep.status_code == 200, f"report {i}: {rep.text}"

        # Verify is_hidden=true on GET
        g = requests.get(f"{API}/duels/{duel_id}", headers=hdr(), timeout=10)
        assert g.status_code == 200
        assert g.json().get("is_hidden") is True

        # Verify vote returns 410
        v = requests.post(
            f"{API}/duels/{duel_id}/vote", data={"choice": "a"}, headers=hdr(), timeout=10
        )
        assert v.status_code == 410
        assert "verborgen" in v.json().get("detail", "").lower()

        # Verify excluded from popular
        pop = requests.get(f"{API}/duels/popular?limit=50", headers=hdr(), timeout=10)
        assert pop.status_code == 200
        ids = {d["id"] for d in pop.json()}
        assert duel_id not in ids

        requests.delete(f"{API}/duels/{duel_id}", params={"token": token}, timeout=10)

    def test_get_duel_has_is_hidden_field(self):
        r = create_duel()
        duel_id = r.json()["id"]
        g = requests.get(f"{API}/duels/{duel_id}", headers=hdr(), timeout=10)
        assert "is_hidden" in g.json()
        assert g.json()["is_hidden"] is False
        requests.delete(f"{API}/duels/{duel_id}", params={"token": r.json()["delete_token"]}, timeout=10)


# ---------------------- rate limiting ----------------------

class TestRateLimits:
    def test_duel_create_rate_limit(self):
        ip = fake_ip()
        ids = []
        for i in range(3):
            r = create_duel(ip=ip, q=f"TEST_rl_{i}")
            assert r.status_code == 200, f"create {i}: {r.status_code} {r.text}"
            ids.append((r.json()["id"], r.json()["delete_token"]))
        # 4th should be 429
        r4 = create_duel(ip=ip, q="TEST_rl_4")
        assert r4.status_code == 429
        assert "3 duels per uur" in r4.json().get("detail", "")
        # cleanup
        for did, tok in ids:
            requests.delete(f"{API}/duels/{did}", params={"token": tok}, timeout=10)

    def test_vote_rate_limit(self):
        # Need a duel to vote on
        r = create_duel()
        duel_id = r.json()["id"]
        token = r.json()["delete_token"]
        ip = fake_ip()
        # First vote ok, subsequent 9 votes return 409 (dup voter) but still consume rate-limit
        statuses = []
        for i in range(10):
            v = requests.post(
                f"{API}/duels/{duel_id}/vote",
                data={"choice": "a"},
                headers=hdr(ip),
                timeout=10,
            )
            statuses.append(v.status_code)
        # 11th vote with same IP → 429
        v11 = requests.post(
            f"{API}/duels/{duel_id}/vote",
            data={"choice": "a"},
            headers=hdr(ip),
            timeout=10,
        )
        assert v11.status_code == 429, f"expected 429 got {v11.status_code}, prev={statuses}"
        assert "maximale aantal stemmen" in v11.json().get("detail", "").lower()
        requests.delete(f"{API}/duels/{duel_id}", params={"token": token}, timeout=10)

    def test_report_rate_limit(self):
        r = create_duel()
        duel_id = r.json()["id"]
        token = r.json()["delete_token"]
        ip = fake_ip()
        # 10 reports from same IP — first succeeds, rest are deduped, but each consumes rate-limit
        for i in range(10):
            requests.post(
                f"{API}/duels/{duel_id}/report",
                data={"reason": "spam"},
                headers=hdr(ip),
                timeout=10,
            )
        r11 = requests.post(
            f"{API}/duels/{duel_id}/report",
            data={"reason": "spam"},
            headers=hdr(ip),
            timeout=10,
        )
        assert r11.status_code == 429, f"expected 429 got {r11.status_code} body={r11.text}"
        requests.delete(f"{API}/duels/{duel_id}", params={"token": token}, timeout=10)
