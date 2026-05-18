"""OutfitDuel — FastAPI backend.

Endpoints (all prefixed with /api except /uploads static):
  POST   /api/duels                 → create duel with two images
  GET    /api/duels/{duel_id}       → fetch duel + vote counts
  POST   /api/duels/{duel_id}/vote  → cast vote (anti-dup via IP-hash + cookie)
  GET    /api/duels/{duel_id}/check-vote
  GET    /api/duels/{duel_id}/count
  DELETE /api/duels/{duel_id}       → delete duel via secret token
  GET    /api/duels/popular
  GET    /api/stats/weekly
  GET    /api/share/duel/{duel_id}  → HTML with OpenGraph tags + meta-refresh

Photos stored locally in /app/backend/uploads, served at /uploads/<name>.
"""

from __future__ import annotations

import asyncio
import hashlib
import html as _html
import io
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import aiofiles
import resend
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Cookie,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image
from pydantic import BaseModel, EmailStr
from starlette.middleware.cors import CORSMiddleware


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 10 * 1024 * 1024  # hard 10MB cap, server-enforced
TARGET_MAX_WIDTH = 1200
JPEG_QUALITY = 80
DUEL_TTL_HOURS = 48
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
HIDE_AT_REPORTS = 3

# In-memory rate limit buckets: key → list[timestamps]
RATE_BUCKETS: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_DISABLED = os.environ.get("RATE_LIMIT_DISABLED", "false").lower() == "true"

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

resend.api_key = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
ABUSE_EMAIL = os.environ.get("ABUSE_EMAIL", "abuse@outfitduel.com")

app = FastAPI(title="OutfitDuel API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("outfitduel")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DuelResponse(BaseModel):
    id: str
    question: str
    photo_a_url: str
    photo_b_url: str
    votes_a: int
    votes_b: int
    created_at: str
    expires_at: str
    is_expired: bool
    is_hidden: bool = False
    has_email: bool


class CreateDuelResponse(DuelResponse):
    delete_token: str
    share_url: str


class VoteResponse(BaseModel):
    choice: str
    votes_a: int
    votes_b: int


class CheckVoteResponse(BaseModel):
    has_voted: bool
    choice: Optional[str] = None


class CountResponse(BaseModel):
    votes_a: int
    votes_b: int
    total: int


class StatsResponse(BaseModel):
    weekly: int
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def client_ip(request: Request) -> str:
    """Return the best-effort client IP, honoring X-Forwarded-For (first hop)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def rate_limit(bucket_key: str, limit: int, window_sec: int, message: str) -> None:
    """In-memory IP-based rate limiter. Raises 429 on overflow."""
    if RATE_LIMIT_DISABLED:
        return
    now = time.time()
    bucket = RATE_BUCKETS[bucket_key]
    cutoff = now - window_sec
    # prune in-place
    fresh = [t for t in bucket if t >= cutoff]
    RATE_BUCKETS[bucket_key] = fresh
    if len(fresh) >= limit:
        raise HTTPException(status_code=429, detail=message)
    fresh.append(now)


def hash_voter(ip: str, duel_id: str) -> str:
    return hashlib.sha256(f"{ip}::{duel_id}".encode()).hexdigest()


def public_photo_url(filename: str) -> str:
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/api/uploads/{filename}" if base else f"/api/uploads/{filename}"


def to_duel_response(doc: dict) -> dict:
    created_at = doc["created_at"]
    expires_at = doc["expires_at"]
    if isinstance(created_at, datetime):
        created_at = iso(created_at)
    if isinstance(expires_at, datetime):
        expires_at = iso(expires_at)
    expired = parse_iso(expires_at) <= now_utc()
    return {
        "id": doc["id"],
        "question": doc.get("question", ""),
        "photo_a_url": public_photo_url(doc["photo_a"]),
        "photo_b_url": public_photo_url(doc["photo_b"]),
        "votes_a": doc.get("votes_a", 0),
        "votes_b": doc.get("votes_b", 0),
        "created_at": created_at,
        "expires_at": expires_at,
        "is_expired": expired,
        "is_hidden": bool(doc.get("is_hidden", False)),
        "has_email": bool(doc.get("email")),
    }


async def compress_and_save(upload: UploadFile, slot: str, duel_id: str) -> str:
    # Validate declared MIME (best-effort; magic-byte check below is authoritative)
    declared = (upload.content_type or "").lower()
    if declared and declared not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Bestandstype '{declared}' niet toegestaan. Alleen JPEG, PNG of WebP.",
        )

    raw = await upload.read()
    if not raw:
        raise HTTPException(status_code=400, detail=f"Leeg bestand voor {slot}")
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"{slot} is groter dan {MAX_BYTES // (1024 * 1024)}MB",
        )

    # Magic-byte validation: Pillow refuses to identify non-image data
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Bestand voor {slot} is geen geldige afbeelding: {exc}"
        )

    if image.format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Bestandstype '{image.format}' niet toegestaan. Alleen JPEG, PNG of WebP.",
        )

    # Explicit EXIF / metadata strip — clear image.info dict so PIL doesn't carry
    # over EXIF/GPS/device-info on save. We also re-encode through a fresh canvas.
    image.info = {}
    if hasattr(image, "_getexif"):
        try:
            image._exif = None  # type: ignore[attr-defined]
        except Exception:
            pass

    if image.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    if image.width > TARGET_MAX_WIDTH:
        ratio = TARGET_MAX_WIDTH / image.width
        new_size = (TARGET_MAX_WIDTH, int(image.height * ratio))
        image = image.resize(new_size, Image.LANCZOS)

    # Always store as JPEG with a server-generated UUID-style name (never trust
    # the uploader's filename). The slot suffix keeps A vs B obvious in logs.
    filename = f"{duel_id}_{slot}_{uuid.uuid4().hex[:8]}.jpg"
    out_path = UPLOAD_DIR / filename
    # Save WITHOUT exif kwarg → PIL does not write EXIF
    image.save(out_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return filename


async def send_result_email(duel: dict) -> None:
    if not duel.get("email") or not resend.api_key:
        return
    votes_a = duel.get("votes_a", 0)
    votes_b = duel.get("votes_b", 0)
    total = votes_a + votes_b
    if total == 0:
        pct_a = pct_b = 50
    else:
        pct_a = round(votes_a / total * 100)
        pct_b = 100 - pct_a
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    result_url = f"{base}/duel/{duel['id']}/resultaat" if base else f"/duel/{duel['id']}/resultaat"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h1 style="color:#050505; font-size:24px;">Je OutfitDuel is afgelopen ⏱️</h1>
        <p style="color:#525252; font-size:16px;">{duel.get('question') or 'Welke outfit wint?'}</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
            <tr>
                <td style="padding:12px; background:#F2F1FA; border-radius:12px; text-align:center;">
                    <div style="color:#7F77DD; font-size:32px; font-weight:700;">{pct_a}%</div>
                    <div style="color:#525252; font-size:13px;">Outfit A · {votes_a} stemmen</div>
                </td>
                <td width="12"></td>
                <td style="padding:12px; background:#F2F1FA; border-radius:12px; text-align:center;">
                    <div style="color:#7F77DD; font-size:32px; font-weight:700;">{pct_b}%</div>
                    <div style="color:#525252; font-size:13px;">Outfit B · {votes_b} stemmen</div>
                </td>
            </tr>
        </table>
        <p style="margin-top:24px;">
            <a href="{result_url}" style="background:#7F77DD; color:white; padding:12px 24px; border-radius:999px; text-decoration:none; font-weight:500;">Bekijk eindresultaat</a>
        </p>
        <p style="color:#A3A3A3; font-size:12px; margin-top:32px;">outfitduel.com · Jouw outfit-dilemma's beslecht</p>
    </div>
    """
    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": SENDER_EMAIL,
                "to": [duel["email"]],
                "subject": "Je OutfitDuel is afgelopen — bekijk het resultaat",
                "html": html,
            },
        )
    except Exception as exc:
        logger.warning("Failed to send result email: %s", exc)


async def expire_duels_loop() -> None:
    """Background task: send result emails to makers when duels expire."""
    while True:
        try:
            cutoff = iso(now_utc())
            cursor = db.duels.find(
                {"expires_at": {"$lte": cutoff}, "result_email_sent": {"$ne": True}, "email": {"$ne": None}},
                {"_id": 0},
            )
            async for duel in cursor:
                await send_result_email(duel)
                await db.duels.update_one({"id": duel["id"]}, {"$set": {"result_email_sent": True}})
        except Exception as exc:
            logger.warning("expire loop error: %s", exc)
        await asyncio.sleep(300)  # every 5 minutes


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@api_router.get("/")
async def root():
    return {"service": "outfitduel", "status": "ok"}


@api_router.post("/duels", response_model=CreateDuelResponse)
async def create_duel(
    request: Request,
    photo_a: UploadFile = File(...),
    photo_b: UploadFile = File(...),
    question: str = Form(""),
    email: Optional[str] = Form(None),
):
    ip = client_ip(request)
    rate_limit(
        f"create:{ip}",
        limit=3,
        window_sec=3600,
        message="Je kunt maximaal 3 duels per uur aanmaken. Probeer het later opnieuw.",
    )

    question = (question or "").strip()[:80]
    duel_id = uuid.uuid4().hex[:10]
    delete_token = secrets.token_urlsafe(24)

    file_a = await compress_and_save(photo_a, "a", duel_id)
    file_b = await compress_and_save(photo_b, "b", duel_id)

    created = now_utc()
    expires = created + timedelta(hours=DUEL_TTL_HOURS)

    doc = {
        "id": duel_id,
        "question": question,
        "photo_a": file_a,
        "photo_b": file_b,
        "votes_a": 0,
        "votes_b": 0,
        "email": email or None,
        "delete_token": delete_token,
        "created_at": iso(created),
        "expires_at": iso(expires),
        "result_email_sent": False,
        "is_hidden": False,
        "report_count": 0,
    }
    await db.duels.insert_one(doc)
    await db.stats.update_one({"_id": "global"}, {"$inc": {"total_duels": 1}}, upsert=True)

    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    share_url = f"{base}/api/share/duel/{duel_id}" if base else f"/api/share/duel/{duel_id}"

    response = to_duel_response(doc)
    response["delete_token"] = delete_token
    response["share_url"] = share_url
    return response


@api_router.get("/duels/popular")
async def popular_duels(limit: int = 6):
    now_iso = iso(now_utc())
    cursor = db.duels.find(
        {
            "expires_at": {"$gt": now_iso},
            "$or": [{"is_hidden": {"$ne": True}}, {"is_hidden": {"$exists": False}}],
        },
        {"_id": 0, "delete_token": 0, "email": 0},
    ).sort("created_at", -1).limit(limit * 3)
    items = []
    async for doc in cursor:
        item = to_duel_response(doc)
        item["total"] = item["votes_a"] + item["votes_b"]
        items.append(item)
    items.sort(key=lambda x: x["total"], reverse=True)
    return items[:limit]


@api_router.get("/duels/{duel_id}", response_model=DuelResponse)
async def get_duel(duel_id: str):
    doc = await db.duels.find_one({"id": duel_id}, {"_id": 0, "delete_token": 0, "email": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    return to_duel_response(doc)


@api_router.get("/duels/{duel_id}/count", response_model=CountResponse)
async def get_count(duel_id: str):
    doc = await db.duels.find_one({"id": duel_id}, {"_id": 0, "votes_a": 1, "votes_b": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    a = doc.get("votes_a", 0)
    b = doc.get("votes_b", 0)
    return {"votes_a": a, "votes_b": b, "total": a + b}


@api_router.get("/duels/{duel_id}/check-vote", response_model=CheckVoteResponse)
async def check_vote(
    duel_id: str,
    request: Request,
    od_voter: Optional[str] = Cookie(default=None),
):
    ip = client_ip(request)
    voter_hash = hash_voter(ip, duel_id)
    record = await db.votes.find_one(
        {"duel_id": duel_id, "$or": [{"voter_hash": voter_hash}, {"cookie_id": od_voter}]},
        {"_id": 0, "choice": 1},
    )
    if record:
        return {"has_voted": True, "choice": record.get("choice")}
    return {"has_voted": False, "choice": None}


@api_router.post("/duels/{duel_id}/vote", response_model=VoteResponse)
async def cast_vote(
    duel_id: str,
    request: Request,
    response: Response,
    choice: str = Form(...),
    od_voter: Optional[str] = Cookie(default=None),
):
    if choice not in ("a", "b"):
        raise HTTPException(status_code=400, detail="Invalid choice")

    ip = client_ip(request)
    rate_limit(
        f"vote:{ip}",
        limit=10,
        window_sec=3600,
        message="Je hebt het maximale aantal stemmen bereikt. Kom later terug.",
    )

    duel = await db.duels.find_one({"id": duel_id}, {"_id": 0})
    if not duel:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    if duel.get("is_hidden"):
        raise HTTPException(status_code=410, detail="Dit duel is tijdelijk verborgen")
    if parse_iso(duel["expires_at"]) <= now_utc():
        raise HTTPException(status_code=410, detail="Duel is verlopen")

    voter_hash = hash_voter(ip, duel_id)
    cookie_id = od_voter or secrets.token_urlsafe(16)

    existing = await db.votes.find_one(
        {"duel_id": duel_id, "$or": [{"voter_hash": voter_hash}, {"cookie_id": cookie_id}]},
        {"_id": 0, "choice": 1},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Je hebt al gestemd")

    await db.votes.insert_one(
        {
            "duel_id": duel_id,
            "voter_hash": voter_hash,
            "cookie_id": cookie_id,
            "choice": choice,
            "created_at": iso(now_utc()),
        }
    )
    field = "votes_a" if choice == "a" else "votes_b"
    updated = await db.duels.find_one_and_update(
        {"id": duel_id},
        {"$inc": {field: 1}},
        projection={"_id": 0, "votes_a": 1, "votes_b": 1},
        return_document=True,
    )

    # set anonymous voter cookie for cross-duel anti-dup hint
    response.set_cookie(
        key="od_voter",
        value=cookie_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
    )
    return {"choice": choice, "votes_a": updated["votes_a"], "votes_b": updated["votes_b"]}


REPORT_REASONS = {
    "offensive": "Ongepaste of aanstootgevende inhoud",
    "no_consent": "Iemand staat zonder toestemming op de foto",
    "spam": "Spam of nep",
}


async def send_abuse_alert(duel_id: str, reason_code: str, report_count: int, request: Request) -> None:
    if not resend.api_key:
        return
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        base = f"{request.url.scheme}://{request.url.netloc}"
    duel_url = f"{base}/duel/{duel_id}"
    reason_label = REPORT_REASONS.get(reason_code, reason_code)
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 520px;">
      <h2 style="color:#050505;">🚨 Nieuwe rapportage</h2>
      <p><strong>Duel:</strong> <a href="{duel_url}">{duel_url}</a></p>
      <p><strong>Reden:</strong> {_html.escape(reason_label)}</p>
      <p><strong>Totaal rapportages:</strong> {report_count}</p>
      <p style="color:#525252; font-size:12px;">Bij ≥ {HIDE_AT_REPORTS} rapportages is dit duel automatisch verborgen.</p>
    </div>
    """
    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": SENDER_EMAIL,
                "to": [ABUSE_EMAIL],
                "subject": f"OutfitDuel rapportage · {reason_label}",
                "html": html,
            },
        )
    except Exception as exc:
        logger.warning("Failed to send abuse alert: %s", exc)


@api_router.post("/duels/{duel_id}/report")
async def report_duel(
    duel_id: str,
    request: Request,
    reason: str = Form(...),
):
    if reason not in REPORT_REASONS:
        raise HTTPException(status_code=400, detail="Ongeldige rapportagereden")

    ip = client_ip(request)
    rate_limit(
        f"report:{ip}",
        limit=10,
        window_sec=3600,
        message="Te veel rapportages. Wacht even en probeer opnieuw.",
    )

    duel = await db.duels.find_one({"id": duel_id}, {"_id": 0, "id": 1, "report_count": 1})
    if not duel:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")

    ip_hash = hashlib.sha256(f"report::{ip}::{duel_id}".encode()).hexdigest()
    # one report per IP per duel
    duplicate = await db.reports.find_one({"duel_id": duel_id, "ip_hash": ip_hash}, {"_id": 0, "duel_id": 1})
    if duplicate:
        return {"ok": True, "deduped": True}

    await db.reports.insert_one(
        {
            "duel_id": duel_id,
            "reason": reason,
            "ip_hash": ip_hash,
            "created_at": iso(now_utc()),
        }
    )
    updated = await db.duels.find_one_and_update(
        {"id": duel_id},
        {"$inc": {"report_count": 1}},
        projection={"_id": 0, "report_count": 1},
        return_document=True,
    )
    new_count = updated.get("report_count", 1) if updated else 1
    if new_count >= HIDE_AT_REPORTS:
        await db.duels.update_one({"id": duel_id}, {"$set": {"is_hidden": True}})

    # fire-and-forget email; never block the user on email delivery
    asyncio.create_task(send_abuse_alert(duel_id, reason, new_count, request))
    return {"ok": True, "report_count": new_count, "is_hidden": new_count >= HIDE_AT_REPORTS}


@api_router.delete("/duels/{duel_id}")
async def delete_duel(duel_id: str, token: str = Query(...)):
    doc = await db.duels.find_one({"id": duel_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    if doc.get("delete_token") != token:
        raise HTTPException(status_code=403, detail="Ongeldig token")

    for slot in ("photo_a", "photo_b"):
        path = UPLOAD_DIR / doc[slot]
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
    await db.duels.delete_one({"id": duel_id})
    await db.votes.delete_many({"duel_id": duel_id})
    return {"deleted": True}


@api_router.get("/stats/weekly", response_model=StatsResponse)
async def weekly_stats():
    week_ago = iso(now_utc() - timedelta(days=7))
    weekly = await db.duels.count_documents({"created_at": {"$gte": week_ago}})
    total_doc = await db.stats.find_one({"_id": "global"}) or {}
    total = total_doc.get("total_duels", weekly)
    # bootstrap baseline so empty platform still looks alive
    return {"weekly": max(weekly, 47), "total": max(total, weekly)}


@api_router.get("/share/duel/{duel_id}", response_class=HTMLResponse)
async def share_preview(duel_id: str, request: Request):
    """OpenGraph-rich landing page used for shareable links (WhatsApp/iMessage crawlers).

    For human users we fall back to a meta-refresh redirect to the SPA route.
    """
    doc = await db.duels.find_one({"id": duel_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        # Derive from request when env var is missing
        base = f"{request.url.scheme}://{request.url.netloc}"
    image_url = f"{base}/api/uploads/{doc['photo_a']}"
    target = f"{base}/duel/{duel_id}"
    raw_title = doc.get("question") or "Welke outfit wint?"
    title = _html.escape(raw_title, quote=True)
    description = "Stem jij ook? → outfitduel.com"
    html = f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8" />
<title>{title} · OutfitDuel</title>
<meta property="og:type" content="website" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{description}" />
<meta property="og:image" content="{image_url}" />
<meta property="og:url" content="{target}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{description}" />
<meta name="twitter:image" content="{image_url}" />
<meta http-equiv="refresh" content="0; url={target}" />
</head>
<body>
<p>Doorsturen naar <a href="{target}">{target}</a>…</p>
</body>
</html>"""
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Wire up app
# ---------------------------------------------------------------------------

app.include_router(api_router)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers — applied to every backend response (API, uploads, share)
_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: blob: https:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "connect-src 'self' https:"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", _CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.on_event("startup")
async def _on_startup():
    asyncio.create_task(expire_duels_loop())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
