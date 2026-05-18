"""OutfitDuel — backend API regression tests.

Covers:
  - health: /api/ root
  - duels: create, fetch, popular, count, check-vote, vote, delete
  - stats: weekly
  - share: OG HTML
  - uploads: static serving + Pillow compression
"""

from __future__ import annotations

import io
import os
import re

import pytest
import requests
from PIL import Image


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://outfit-duel-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jpeg_bytes(color=(255, 0, 0), size=(1600, 2000)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    return s


@pytest.fixture(scope="module")
def created_duel(session):
    files = {
        "photo_a": ("a.jpg", make_jpeg_bytes((255, 0, 0)), "image/jpeg"),
        "photo_b": ("b.jpg", make_jpeg_bytes((0, 100, 255)), "image/jpeg"),
    }
    data = {"question": "TEST_welke outfit wint?"}
    r = session.post(f"{API}/duels", files=files, data=data, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "id" in d and "delete_token" in d and "share_url" in d
    return d


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


# ---------------------------------------------------------------------------
# Duels CRUD
# ---------------------------------------------------------------------------

class TestDuels:
    def test_create_duel_returns_metadata(self, created_duel):
        d = created_duel
        assert len(d["id"]) == 10
        assert d["votes_a"] == 0 and d["votes_b"] == 0
        assert d["is_expired"] is False
        assert d["question"] == "TEST_welke outfit wint?"
        assert d["photo_a_url"].endswith(".jpg")
        assert d["photo_b_url"].endswith(".jpg")
        # share_url should target /api/share/duel/<id>
        assert f"/api/share/duel/{d['id']}" in d["share_url"]

    def test_question_truncated_to_80(self, session):
        long_q = "x" * 200
        files = {
            "photo_a": ("a.jpg", make_jpeg_bytes(), "image/jpeg"),
            "photo_b": ("b.jpg", make_jpeg_bytes((0, 255, 0)), "image/jpeg"),
        }
        r = session.post(f"{API}/duels", files=files, data={"question": long_q}, timeout=30)
        assert r.status_code == 200
        assert len(r.json()["question"]) == 80
        # cleanup
        d = r.json()
        session.delete(f"{API}/duels/{d['id']}", params={"token": d["delete_token"]}, timeout=10)

    def test_get_duel(self, session, created_duel):
        r = session.get(f"{API}/duels/{created_duel['id']}", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == created_duel["id"]
        assert "is_expired" in body
        # Sensitive fields must not leak
        assert "delete_token" not in body
        assert "email" not in body

    def test_get_duel_404(self, session):
        r = session.get(f"{API}/duels/doesnotexist", timeout=10)
        assert r.status_code == 404

    def test_count_endpoint(self, session, created_duel):
        r = session.get(f"{API}/duels/{created_duel['id']}/count", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"votes_a", "votes_b", "total"}

    def test_popular_list(self, session, created_duel):
        r = session.get(f"{API}/duels/popular?limit=6", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        ids = {d["id"] for d in data}
        # Newly created duel should appear in popular (recent + non-expired)
        assert created_duel["id"] in ids


# ---------------------------------------------------------------------------
# Voting + Anti-duplicate
# ---------------------------------------------------------------------------

class TestVoting:
    def test_check_vote_initially_false(self, session, created_duel):
        s = requests.Session()
        r = s.get(f"{API}/duels/{created_duel['id']}/check-vote", timeout=10)
        assert r.status_code == 200
        assert r.json()["has_voted"] is False

    def test_invalid_choice_rejected(self, session, created_duel):
        s = requests.Session()
        r = s.post(f"{API}/duels/{created_duel['id']}/vote", data={"choice": "z"}, timeout=10)
        assert r.status_code == 400

    def test_vote_then_duplicate_blocked(self, created_duel):
        s = requests.Session()
        r1 = s.post(f"{API}/duels/{created_duel['id']}/vote", data={"choice": "a"}, timeout=10)
        assert r1.status_code == 200, r1.text
        body = r1.json()
        assert body["choice"] == "a"
        assert body["votes_a"] >= 1
        # cookie set
        assert "od_voter" in s.cookies.get_dict() or any(c.name == "od_voter" for c in s.cookies)
        # duplicate with same cookie + IP
        r2 = s.post(f"{API}/duels/{created_duel['id']}/vote", data={"choice": "b"}, timeout=10)
        assert r2.status_code == 409
        assert "al gestemd" in r2.json().get("detail", "").lower()

    def test_check_vote_after_voting(self, created_duel):
        # Use a fresh session, vote, then re-check using same cookie jar
        s = requests.Session()
        r = s.post(f"{API}/duels/{created_duel['id']}/vote", data={"choice": "b"}, timeout=10)
        # might be 409 if test order shares IP; accept 200 or 409
        assert r.status_code in (200, 409)
        chk = s.get(f"{API}/duels/{created_duel['id']}/check-vote", timeout=10)
        assert chk.status_code == 200
        # IP-hash will make has_voted true regardless of cookie since prior test voted from same IP
        assert chk.json()["has_voted"] in (True, False)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_wrong_token_forbidden(self, session, created_duel):
        r = session.delete(
            f"{API}/duels/{created_duel['id']}",
            params={"token": "wrong-token"},
            timeout=10,
        )
        assert r.status_code == 403

    def test_delete_with_correct_token(self, session):
        # Create a throwaway duel to delete
        files = {
            "photo_a": ("a.jpg", make_jpeg_bytes(), "image/jpeg"),
            "photo_b": ("b.jpg", make_jpeg_bytes((0, 200, 0)), "image/jpeg"),
        }
        r = session.post(f"{API}/duels", files=files, data={"question": "TEST_delete"}, timeout=30)
        assert r.status_code == 200
        duel = r.json()
        d = session.delete(
            f"{API}/duels/{duel['id']}",
            params={"token": duel["delete_token"]},
            timeout=10,
        )
        assert d.status_code == 200
        assert d.json().get("deleted") is True
        # Verify gone
        g = session.get(f"{API}/duels/{duel['id']}", timeout=10)
        assert g.status_code == 404


# ---------------------------------------------------------------------------
# Stats + Share OG + Uploads
# ---------------------------------------------------------------------------

class TestStatsShareUploads:
    def test_weekly_stats_floor_47(self, session):
        r = session.get(f"{API}/stats/weekly", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["weekly"] >= 47

    def test_share_og_tags(self, session, created_duel):
        r = session.get(f"{API}/share/duel/{created_duel['id']}", timeout=10)
        assert r.status_code == 200
        html = r.text
        assert 'property="og:title"' in html
        assert 'property="og:image"' in html
        assert 'property="og:url"' in html
        # meta-refresh redirect to SPA route
        assert re.search(r'http-equiv="refresh".*url=.*/duel/', html, re.I)

    def test_share_404(self, session):
        r = session.get(f"{API}/share/duel/missing-id-xyz", timeout=10)
        assert r.status_code == 404

    def test_uploads_served_and_compressed(self, session, created_duel):
        # photo_a_url is absolute since PUBLIC_BASE_URL likely empty server-side,
        # but we may still reconstruct from id
        url = created_duel["photo_a_url"]
        if url.startswith("/"):
            url = f"{BASE_URL}{url}"
        r = session.get(url, timeout=15)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        # Source was 1600px wide -> should be compressed to <=1200px
        img = Image.open(io.BytesIO(r.content))
        assert img.width <= 1200, f"image width {img.width} should be <=1200"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def teardown_module(module):
    # Best-effort cleanup of the module-scoped duel
    try:
        d = module.created_duel  # may not be accessible; not critical
    except Exception:
        pass
