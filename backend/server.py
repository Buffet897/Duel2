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
  GET    /api/healthz               → health check for Plesk monitoring  [NIEUW]
  GET    /api/admin/reports         → token-gated moderation dashboard   [NIEUW]
  POST   /api/admin/duels/{id}/unhide → unhide reported duel             [NIEUW]
  POST   /api/admin/duels/{id}/delete → permanently delete duel          [NIEUW]

Photos stored locally in /app/backend/uploads, served at /uploads/<name>.
"""

from __future__ import annotations

import asyncio
import hashlib
import html as _html
import io
import json
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

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(ROOT_DIR / "uploads"))).expanduser()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_BUILD_DIR = Path(
    os.environ.get("FRONTEND_BUILD_DIR", str(ROOT_DIR / "frontend_build"))
).expanduser()

MAX_BYTES = 10 * 1024 * 1024
TARGET_MAX_WIDTH = 1200
JPEG_QUALITY = 80
DUEL_TTL_HOURS = 48
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
HIDE_AT_REPORTS = 3

RATE_BUCKETS: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_DISABLED = os.environ.get("RATE_LIMIT_DISABLED", "false").lower() == "true"

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

resend.api_key = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
ABUSE_EMAIL = os.environ.get("ABUSE_EMAIL", "abuse@outfitduel.com")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", ABUSE_EMAIL)
FROM_EMAIL = os.environ.get("FROM_EMAIL", SENDER_EMAIL)

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or 587)
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_TLS = os.environ.get("SMTP_TLS", "true").lower() != "false"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()


def _send_smtp_sync(to_email: str, subject: str, html: str) -> None:
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL or SMTP_USER
    msg["To"] = to_email
    msg.set_content("Open this email in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")

    if SMTP_TLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except smtplib.SMTPNotSupportedError:
                pass
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)


async def send_mail(to_email: str, subject: str, html: str) -> bool:
    if not to_email:
        return False
    if SMTP_HOST:
        try:
            await asyncio.to_thread(_send_smtp_sync, to_email, subject, html)
            return True
        except Exception as exc:
            logger.warning("SMTP send failed: %s", exc)
            return False
    if resend.api_key:
        try:
            await asyncio.to_thread(
                resend.Emails.send,
                {"from": FROM_EMAIL or SENDER_EMAIL, "to": [to_email], "subject": subject, "html": html},
            )
            return True
        except Exception as exc:
            logger.warning("Resend send failed: %s", exc)
            return False
    return False


LOCALES_DIR = ROOT_DIR / "locales"
LOCALES = {}
for _code in ("nl", "en"):
    try:
        with open(LOCALES_DIR / f"{_code}.json", encoding="utf-8") as _f:
            LOCALES[_code] = json.load(_f)
    except FileNotFoundError:
        LOCALES[_code] = {}


def pick_lang(value: Optional[str]) -> str:
    if not value:
        return "en"
    head = value.split(",")[0].split(";")[0].strip().lower()
    return "nl" if head.startswith("nl") else "en"


def request_lang(request: Request) -> str:
    cookie = request.cookies.get("od_lang")
    if cookie in ("nl", "en"):
        return cookie
    return pick_lang(request.headers.get("accept-language"))


def L(lang: str) -> dict:
    return LOCALES.get(lang) or LOCALES.get("en") or {}


app = FastAPI(title="OutfitDuel API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("outfitduel")


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


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def rate_limit(bucket_key: str, limit: int, window_sec: int, message: str) -> None:
    if RATE_LIMIT_DISABLED:
        return
    now = time.time()
    bucket = RATE_BUCKETS[bucket_key]
    cutoff = now - window_sec
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
    declared = (upload.content_type or "").lower()
    if declared and declared not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Bestandstype '{declared}' niet toegestaan.")

    raw = await upload.read()
    if not raw:
        raise HTTPException(status_code=400, detail=f"Leeg bestand voor {slot}")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"{slot} is groter dan {MAX_BYTES // (1024 * 1024)}MB")

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Geen geldige afbeelding: {exc}")

    if image.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Bestandstype '{image.format}' niet toegestaan.")

    image.info = {}
    if hasattr(image, "_getexif"):
        try:
            image._exif = None
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
        image = image.resize((TARGET_MAX_WIDTH, int(image.height * ratio)), Image.LANCZOS)

    filename = f"{duel_id}_{slot}_{uuid.uuid4().hex[:8]}.jpg"
    image.save(UPLOAD_DIR / filename, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return filename


async def send_result_email(duel: dict) -> None:
    if not duel.get("email") or (not SMTP_HOST and not resend.api_key):
        return
    votes_a = duel.get("votes_a", 0)
    votes_b = duel.get("votes_b", 0)
    total = votes_a + votes_b
    pct_a = round(votes_a / total * 100) if total else 50
    pct_b = 100 - pct_a
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    result_url = f"{base}/duel/{duel['id']}/resultaat"
    lang = duel.get("lang") or "nl"
    s = L(lang)
    html = f"""
    <div style="font-family:-apple-system,sans-serif;max-width:480px;margin:0 auto;padding:24px;">
        <h1 style="color:#050505;font-size:24px;">{_html.escape(s.get('title','OutfitDuel'))}</h1>
        <p style="color:#525252;">{_html.escape(duel.get('question') or '')}</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
            <tr>
                <td style="padding:12px;background:#F2F1FA;border-radius:12px;text-align:center;">
                    <div style="color:#7F77DD;font-size:32px;font-weight:700;">{pct_a}%</div>
                    <div style="color:#525252;font-size:13px;">Outfit A · {votes_a}</div>
                </td>
                <td width="12"></td>
                <td style="padding:12px;background:#F2F1FA;border-radius:12px;text-align:center;">
                    <div style="color:#7F77DD;font-size:32px;font-weight:700;">{pct_b}%</div>
                    <div style="color:#525252;font-size:13px;">Outfit B · {votes_b}</div>
                </td>
            </tr>
        </table>
        <p style="margin-top:24px;">
            <a href="{result_url}" style="background:#7F77DD;color:white;padding:12px 24px;border-radius:999px;text-decoration:none;">
                {_html.escape(s.get('cta','Bekijk resultaat'))}
            </a>
        </p>
        <p style="color:#A3A3A3;font-size:12px;margin-top:32px;">{_html.escape(s.get('footer',''))}</p>
    </div>"""
    try:
        await send_mail(duel["email"], s.get("subject", "OutfitDuel resultaat"), html)
    except Exception as exc:
        logger.warning("Failed to send result email: %s", exc)


async def expire_duels_loop() -> None:
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
        await asyncio.sleep(300)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@api_router.get("/")
async def root():
    return {"service": "outfitduel", "status": "ok"}


@api_router.get("/healthz")
async def healthz():
    """Health check voor Plesk monitoring: https://outfitduel.com/api/healthz"""
    try:
        await db.command("ping")
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": iso(now_utc()),
        "database": db_status,
        "version": "1.0.0",
    }


@api_router.post("/duels", response_model=CreateDuelResponse)
async def create_duel(
    request: Request,
    photo_a: UploadFile = File(...),
    photo_b: UploadFile = File(...),
    question: str = Form(""),
    email: Optional[str] = Form(None),
):
    ip = client_ip(request)
    rate_limit(f"create:{ip}", 3, 3600, "Je kunt maximaal 3 duels per uur aanmaken.")
    question = (question or "").strip()[:80]
    duel_id = uuid.uuid4().hex[:10]
    delete_token = secrets.token_urlsafe(24)
    lang = request_lang(request)
    file_a = await compress_and_save(photo_a, "a", duel_id)
    file_b = await compress_and_save(photo_b, "b", duel_id)
    created = now_utc()
    expires = created + timedelta(hours=DUEL_TTL_HOURS)
    doc = {
        "id": duel_id, "question": question, "photo_a": file_a, "photo_b": file_b,
        "votes_a": 0, "votes_b": 0, "email": email or None, "delete_token": delete_token,
        "created_at": iso(created), "expires_at": iso(expires), "result_email_sent": False,
        "is_hidden": False, "report_count": 0, "lang": lang,
    }
    await db.duels.insert_one(doc)
    await db.stats.update_one({"_id": "global"}, {"$inc": {"total_duels": 1}}, upsert=True)
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    share_url = f"{base}/api/share/duel/{duel_id}"
    response = to_duel_response(doc)
    response["delete_token"] = delete_token
    response["share_url"] = share_url
    return response


@api_router.get("/duels/popular")
async def popular_duels(limit: int = 6):
    now_iso = iso(now_utc())
    cursor = db.duels.find(
        {"expires_at": {"$gt": now_iso}, "$or": [{"is_hidden": {"$ne": True}}, {"is_hidden": {"$exists": False}}]},
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
    a, b = doc.get("votes_a", 0), doc.get("votes_b", 0)
    return {"votes_a": a, "votes_b": b, "total": a + b}


@api_router.get("/duels/{duel_id}/check-vote", response_model=CheckVoteResponse)
async def check_vote(duel_id: str, request: Request, od_voter: Optional[str] = Cookie(default=None)):
    voter_hash = hash_voter(client_ip(request), duel_id)
    record = await db.votes.find_one(
        {"duel_id": duel_id, "$or": [{"voter_hash": voter_hash}, {"cookie_id": od_voter}]},
        {"_id": 0, "choice": 1},
    )
    if record:
        return {"has_voted": True, "choice": record.get("choice")}
    return {"has_voted": False, "choice": None}


@api_router.post("/duels/{duel_id}/vote", response_model=VoteResponse)
async def cast_vote(
    duel_id: str, request: Request, response: Response,
    choice: str = Form(...), od_voter: Optional[str] = Cookie(default=None),
):
    if choice not in ("a", "b"):
        raise HTTPException(status_code=400, detail="Invalid choice")
    ip = client_ip(request)
    rate_limit(f"vote:{ip}", 10, 3600, "Je hebt het maximale aantal stemmen bereikt.")
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
    await db.votes.insert_one({"duel_id": duel_id, "voter_hash": voter_hash, "cookie_id": cookie_id, "choice": choice, "created_at": iso(now_utc())})
    field = "votes_a" if choice == "a" else "votes_b"
    updated = await db.duels.find_one_and_update(
        {"id": duel_id}, {"$inc": {field: 1}},
        projection={"_id": 0, "votes_a": 1, "votes_b": 1}, return_document=True,
    )
    response.set_cookie(key="od_voter", value=cookie_id, max_age=60*60*24*365, httponly=True, samesite="lax")
    return {"choice": choice, "votes_a": updated["votes_a"], "votes_b": updated["votes_b"]}


REPORT_REASONS = {
    "offensive": "Ongepaste of aanstootgevende inhoud",
    "no_consent": "Iemand staat zonder toestemming op de foto",
    "spam": "Spam of nep",
}


async def send_abuse_alert(duel_id: str, reason_code: str, report_count: int, request: Request) -> None:
    if not SMTP_HOST and not resend.api_key:
        return
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or f"{request.url.scheme}://{request.url.netloc}"
    duel_url = f"{base}/duel/{duel_id}"
    reason_label = REPORT_REASONS.get(reason_code, reason_code)
    html = f"""<div style="font-family:-apple-system,sans-serif;max-width:520px;">
      <h2>Nieuwe rapportage</h2>
      <p><strong>Duel:</strong> <a href="{duel_url}">{duel_url}</a></p>
      <p><strong>Reden:</strong> {_html.escape(reason_label)}</p>
      <p><strong>Totaal:</strong> {report_count}</p>
    </div>"""
    try:
        await send_mail(CONTACT_EMAIL or ABUSE_EMAIL, f"OutfitDuel rapportage: {reason_label}", html)
    except Exception as exc:
        logger.warning("Failed to send abuse alert: %s", exc)


@api_router.post("/duels/{duel_id}/report")
async def report_duel(duel_id: str, request: Request, reason: str = Form(...)):
    if reason not in REPORT_REASONS:
        raise HTTPException(status_code=400, detail="Ongeldige rapportagereden")
    ip = client_ip(request)
    rate_limit(f"report:{ip}", 10, 3600, "Te veel rapportages.")
    duel = await db.duels.find_one({"id": duel_id}, {"_id": 0, "id": 1})
    if not duel:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    ip_hash = hashlib.sha256(f"report::{ip}::{duel_id}".encode()).hexdigest()
    if await db.reports.find_one({"duel_id": duel_id, "ip_hash": ip_hash}):
        return {"ok": True, "deduped": True}
    await db.reports.insert_one({"duel_id": duel_id, "reason": reason, "ip_hash": ip_hash, "created_at": iso(now_utc())})
    updated = await db.duels.find_one_and_update(
        {"id": duel_id}, {"$inc": {"report_count": 1}},
        projection={"_id": 0, "report_count": 1}, return_document=True,
    )
    new_count = updated.get("report_count", 1) if updated else 1
    if new_count >= HIDE_AT_REPORTS:
        await db.duels.update_one({"id": duel_id}, {"$set": {"is_hidden": True}})
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
    return {"weekly": max(weekly, 47), "total": max(total, weekly)}


@api_router.get("/share/duel/{duel_id}", response_class=HTMLResponse)
async def share_preview(duel_id: str, request: Request):
    doc = await db.duels.find_one({"id": duel_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or f"{request.url.scheme}://{request.url.netloc}"
    image_url = f"{base}/api/uploads/{doc['photo_a']}"
    target = f"{base}/duel/{duel_id}"
    lang = request_lang(request)
    title = _html.escape(doc.get("question") or "Which outfit wins?", quote=True)
    description = L(lang).get("og_description", "Cast your vote! outfitduel.com")
    html = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"/>
<title>{title} - OutfitDuel</title>
<meta property="og:type" content="website"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description}"/>
<meta property="og:image" content="{image_url}"/>
<meta property="og:url" content="{target}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:image" content="{image_url}"/>
<meta http-equiv="refresh" content="0; url={target}"/>
</head><body><p><a href="{target}">{target}</a></p></body></html>"""
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Admin — moderatie dashboard
# ---------------------------------------------------------------------------

def _check_admin(request: Request) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Stel ADMIN_PASSWORD in als environment variable")
    token = request.headers.get("x-admin-token") or request.query_params.get("token", "")
    if not secrets.compare_digest(token.encode(), ADMIN_PASSWORD.encode()):
        raise HTTPException(status_code=401, detail="Niet geautoriseerd")


@api_router.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports(request: Request, token: str = Query(default="")):
    """Moderatie dashboard — gebruik: https://outfitduel.com/api/admin/reports?token=WACHTWOORD"""
    _check_admin(request)
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or f"{request.url.scheme}://{request.url.netloc}"
    cursor = db.duels.find(
        {"$or": [{"is_hidden": True}, {"report_count": {"$gte": 1}}]},
        {"_id": 0, "delete_token": 0, "email": 0},
    ).sort("report_count", -1).limit(100)
    hidden_count = await db.duels.count_documents({"is_hidden": True})
    rows_html = ""
    async for doc in cursor:
        duel_id = doc["id"]
        count = doc.get("report_count", 0)
        hidden = doc.get("is_hidden", False)
        question = _html.escape(doc.get("question", "(geen vraag)"))
        photo_a_url = f"{base}/api/uploads/{doc['photo_a']}"
        photo_b_url = f"{base}/api/uploads/{doc['photo_b']}"
        duel_url = f"{base}/duel/{duel_id}"
        status_badge = (
            '<span style="background:#FCEBEB;color:#791F1F;padding:2px 8px;border-radius:10px;font-size:11px;">Verborgen</span>'
            if hidden else
            '<span style="background:#FAEEDA;color:#633806;padding:2px 8px;border-radius:10px;font-size:11px;">Zichtbaar</span>'
        )
        unhide_btn = (
            f'<form method="post" action="{base}/api/admin/duels/{duel_id}/unhide?token={token}" style="display:inline">'
            '<button type="submit" style="background:#E1F5EE;color:#085041;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;margin-right:6px;">Toon weer</button></form>'
        ) if hidden else ""
        delete_btn = (
            f'<form method="post" action="{base}/api/admin/duels/{duel_id}/delete?token={token}" style="display:inline"'
            " onsubmit=\"return confirm('Definitief verwijderen?')\">"
            '<button type="submit" style="background:#FCEBEB;color:#791F1F;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;">Verwijder</button></form>'
        )
        rows_html += f"""<tr style="border-bottom:1px solid #F1EFE8;">
            <td style="padding:12px 8px;vertical-align:top;">
                <img src="{photo_a_url}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;margin-right:4px;">
                <img src="{photo_b_url}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;">
            </td>
            <td style="padding:12px 8px;vertical-align:top;">
                <a href="{duel_url}" target="_blank" style="color:#7F77DD;text-decoration:none;font-size:13px;font-weight:500;">{question}</a>
                <div style="font-size:11px;color:#A3A3A3;margin-top:4px;">{duel_id}</div>
            </td>
            <td style="padding:12px 8px;text-align:center;vertical-align:top;">
                <strong style="font-size:20px;color:#E24B4A;">{count}</strong>
                <div style="font-size:10px;color:#A3A3A3;">rapportages</div>
            </td>
            <td style="padding:12px 8px;vertical-align:top;">{status_badge}</td>
            <td style="padding:12px 8px;vertical-align:top;white-space:nowrap;">{unhide_btn}{delete_btn}</td>
        </tr>"""
    if not rows_html:
        rows_html = '<tr><td colspan="5" style="padding:32px;text-align:center;color:#A3A3A3;">Geen gerapporteerde duels.</td></tr>'
    page_html = f"""<!doctype html><html lang="nl"><head><meta charset="utf-8">
<title>OutfitDuel - Moderatie</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:-apple-system,sans-serif;margin:0;padding:24px;background:#FAFAF9;color:#050505}}
h1{{font-size:20px;font-weight:600;margin:0 0 4px}}.meta{{font-size:13px;color:#5F5E5A;margin:0 0 20px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
th{{background:#F1EFE8;padding:10px 8px;text-align:left;font-size:12px;color:#5F5E5A;font-weight:500}}
tr:hover td{{background:#FAFAF9}}footer{{font-size:11px;color:#A3A3A3;margin-top:24px}}</style>
</head><body>
<h1>OutfitDuel - Moderatie</h1>
<p class="meta"><strong>{hidden_count}</strong> verborgen duel(s)</p>
<table><thead><tr>
<th>Foto's</th><th>Vraag / ID</th><th style="text-align:center">Rapportages</th><th>Status</th><th>Acties</th>
</tr></thead><tbody>{rows_html}</tbody></table>
<footer>OutfitDuel &nbsp;·&nbsp; <a href="mailto:info@omniastore.nl" style="color:#7F77DD;">info@omniastore.nl</a></footer>
</body></html>"""
    return HTMLResponse(content=page_html)


@api_router.post("/admin/duels/{duel_id}/unhide")
async def admin_unhide(duel_id: str, request: Request, token: str = Query(default="")):
    _check_admin(request)
    result = await db.duels.update_one({"id": duel_id}, {"$set": {"is_hidden": False, "report_count": 0}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return Response(status_code=302, headers={"location": f"{base}/api/admin/reports?token={token}"})


@api_router.post("/admin/duels/{duel_id}/delete")
async def admin_delete(duel_id: str, request: Request, token: str = Query(default="")):
    _check_admin(request)
    doc = await db.duels.find_one({"id": duel_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Duel niet gevonden")
    for slot in ("photo_a", "photo_b"):
        path = UPLOAD_DIR / doc[slot]
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
    await db.duels.delete_one({"id": duel_id})
    await db.votes.delete_many({"duel_id": duel_id})
    await db.reports.delete_many({"duel_id": duel_id})
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return Response(status_code=302, headers={"location": f"{base}/api/admin/reports?token={token}"})


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

_CSP = (
    "default-src 'self'; img-src 'self' data: blob: https:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
    "font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' https:"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", _CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


if FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "index.html").exists():
    from fastapi.responses import FileResponse

    static_dir = FRONTEND_BUILD_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="frontend-static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404)
        if full_path:
            candidate = FRONTEND_BUILD_DIR / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_BUILD_DIR / "index.html"))


@app.on_event("startup")
async def _on_startup():
    asyncio.create_task(expire_duels_loop())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
