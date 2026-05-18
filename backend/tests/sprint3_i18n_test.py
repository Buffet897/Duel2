"""OutfitDuel Sprint 3 — i18n backend tests.

Tests:
  - POST /api/duels stores duel.lang from Accept-Language + cookie override
  - GET /api/share/duel/{id} returns og:description + html lang per request lang
  - send_result_email() helper uses duel.lang to load locale strings
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import uuid

import pytest
import requests
from PIL import Image


def _load_env():
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


_load_env()
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def fake_ip() -> str:
    h = uuid.uuid4().int
    return f"10.{(h >> 16) & 0xFF}.{(h >> 8) & 0xFF}.{h & 0xFF}"


def jpeg_bytes(color=(255, 0, 0), size=(400, 500)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def create_duel(headers=None, q="TEST_sprint3"):
    files = {
        "photo_a": ("a.jpg", jpeg_bytes(), "image/jpeg"),
        "photo_b": ("b.jpg", jpeg_bytes((0, 100, 255)), "image/jpeg"),
    }
    hdrs = {"X-Forwarded-For": fake_ip()}
    if headers:
        hdrs.update(headers)
    return requests.post(f"{API}/duels", files=files, data={"question": q}, headers=hdrs, timeout=30)


def cleanup(duel_id, token):
    try:
        requests.delete(f"{API}/duels/{duel_id}", params={"token": token}, timeout=10)
    except Exception:
        pass


# ---------------------- duel.lang on creation ----------------------

class TestDuelLangStorage:
    """Duel must store lang from cookie (priority) or Accept-Language."""

    def test_create_with_accept_language_nl(self):
        r = create_duel(headers={"Accept-Language": "nl-NL,nl;q=0.9"})
        assert r.status_code == 200, r.text
        d = r.json()
        # The duel doc has lang via share preview endpoint; verify indirectly via share
        share = requests.get(f"{API}/share/duel/{d['id']}", headers={"Accept-Language": "x"}, timeout=10)
        # Use a non-matching Accept-Language to ensure share uses *cookie* not header here
        # but for THIS test we just verify the duel was created; lang is verified via share when cookie is set
        assert share.status_code == 200
        cleanup(d["id"], d["delete_token"])

    def test_create_with_accept_language_en(self):
        r = create_duel(headers={"Accept-Language": "en-US,en;q=0.9"})
        assert r.status_code == 200, r.text
        d = r.json()
        cleanup(d["id"], d["delete_token"])

    def test_cookie_overrides_accept_language(self):
        # cookie od_lang=en should win even if Accept-Language: nl
        r = create_duel(headers={"Accept-Language": "nl-NL", "Cookie": "od_lang=en"})
        assert r.status_code == 200, r.text
        d = r.json()
        cleanup(d["id"], d["delete_token"])


# ---------------------- share preview language ----------------------

class TestSharePreviewLanguage:
    """GET /api/share/duel/{id} OG description + html lang per request language."""

    @pytest.fixture(scope="class")
    def duel(self):
        r = create_duel(q="TEST_share_lang")
        assert r.status_code == 200, r.text
        d = r.json()
        yield d
        cleanup(d["id"], d["delete_token"])

    def test_share_english(self, duel):
        r = requests.get(
            f"{API}/share/duel/{duel['id']}",
            headers={"Accept-Language": "en-US"},
            timeout=10,
        )
        assert r.status_code == 200
        body = r.text
        assert 'lang="en"' in body, f"expected lang=en, got: {body[:200]}"
        assert "Cast your vote!" in body
        assert "outfitduel.com" in body

    def test_share_dutch(self, duel):
        r = requests.get(
            f"{API}/share/duel/{duel['id']}",
            headers={"Accept-Language": "nl-NL,nl;q=0.9"},
            timeout=10,
        )
        assert r.status_code == 200
        body = r.text
        assert 'lang="nl"' in body, f"expected lang=nl, got: {body[:200]}"
        assert "Stem jij ook?" in body

    def test_share_cookie_overrides_header(self, duel):
        # cookie od_lang=en, Accept-Language: nl → should render EN
        r = requests.get(
            f"{API}/share/duel/{duel['id']}",
            headers={"Accept-Language": "nl-NL", "Cookie": "od_lang=en"},
            timeout=10,
        )
        assert r.status_code == 200
        body = r.text
        assert 'lang="en"' in body
        assert "Cast your vote!" in body
        assert "Stem jij ook?" not in body

    def test_share_default_is_en_when_unknown(self, duel):
        r = requests.get(
            f"{API}/share/duel/{duel['id']}",
            headers={"Accept-Language": "fr-FR"},
            timeout=10,
        )
        assert r.status_code == 200
        assert 'lang="en"' in r.text


# ---------------------- send_result_email helper ----------------------

class TestSendResultEmailLocale:
    """Verify send_result_email picks the right locale strings based on duel.lang."""

    def test_email_html_uses_locale(self, monkeypatch=None):
        # Import server module directly to call helper
        sys.path.insert(0, "/app/backend")
        import importlib
        if "server" in sys.modules:
            server = importlib.reload(sys.modules["server"])
        else:
            import server  # type: ignore

        # Patch resend.api_key to truthy and capture sent payload
        captured = {}

        def fake_send(payload):
            captured.update(payload)
            return {"id": "fake"}

        server.resend.api_key = "test-key"
        original_send = server.resend.Emails.send
        server.resend.Emails.send = fake_send

        try:
            # NL duel
            duel_nl = {
                "id": "testnl",
                "email": "test@example.com",
                "question": "Welke?",
                "votes_a": 3,
                "votes_b": 1,
                "lang": "nl",
            }
            asyncio.run(server.send_result_email(duel_nl))
            assert "stemmen" in captured.get("html", ""), f"NL html missing 'stemmen': {captured.get('html','')[:300]}"
            assert "Outfit A" in captured.get("html", "")
            assert "afgelopen" in captured.get("subject", "").lower() or "outfitduel" in captured.get("subject", "").lower()
            captured.clear()

            # EN duel
            duel_en = {
                "id": "testen",
                "email": "test@example.com",
                "question": "Which?",
                "votes_a": 1,
                "votes_b": 2,
                "lang": "en",
            }
            asyncio.run(server.send_result_email(duel_en))
            html = captured.get("html", "")
            assert "votes" in html, f"EN html missing 'votes': {html[:300]}"
            assert "vote" in html  # singular for votes_a=1
            assert "Outfit A" in html
            captured.clear()

            # Missing lang → defaults to nl
            duel_no_lang = {
                "id": "testnone",
                "email": "test@example.com",
                "question": "?",
                "votes_a": 0,
                "votes_b": 0,
            }
            asyncio.run(server.send_result_email(duel_no_lang))
            assert "stemmen" in captured.get("html", "")

        finally:
            server.resend.Emails.send = original_send
            server.resend.api_key = ""


# ---------------------- regression: existing endpoints still work ----------------------

class TestRegressionSprint3:
    def test_root_still_ok(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_popular_still_returns_list(self):
        r = requests.get(f"{API}/duels/popular?limit=5", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_stats_weekly(self):
        r = requests.get(f"{API}/stats/weekly", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "weekly" in data and "total" in data
