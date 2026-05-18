# OutfitDuel — Product Requirements Document

## Original problem statement
Build OutfitDuel: a Dutch-language web app where users upload two outfit photos and let their network vote. Sprint 1 (build now): create duel with 2 photos + optional question/email, swipe-based voting, shareable URL with OG previews, downloadable result card (Stories 1080x1920 + Feed 1080x1080) with photo/clean toggle, post-vote CTA after 3s, 48h expiry with Resend email, GDPR privacy page, anti-double-voting, no account required. Mobile-first, white bg, accent #7F77DD, Inter+Outfit fonts.

## Architecture
- Frontend: React 19 + react-router-dom 7 + framer-motion (swipe) + html-to-image (PNG export) + Tailwind + shadcn (sonner toaster)
- Backend: FastAPI + Motor (MongoDB async) + Pillow (image compression) + Resend SDK (email, non-blocking via asyncio.to_thread)
- Storage: Photos stored in /app/backend/uploads served at /api/uploads/{file}
- Anti-dup vote: SHA256 hash of (IP + duel_id) AND HTTP-only cookie `od_voter`
- OG previews: /api/share/duel/{id} returns HTML with og:title/og:image/og:url + meta-refresh redirect for human users
- Background task: every 5 min checks expired duels and emails maker (if RESEND_API_KEY set)

## User persona
Gen-Z/Millennial fashion-conscious user who needs quick crowd-sourced opinion on outfit choice for date/job/festival. Wants viral, no-account, mobile-first experience. Shares duel via WhatsApp/iMessage.

## Implemented (2026-02)
- POST /api/duels (multipart, server-side Pillow compress to 1200px @ JPEG q80)
- GET /api/duels/{id}, /count, /check-vote, POST /vote with 409 on dup
- DELETE /api/duels/{id}?token= (token-gated maker delete)
- GET /api/duels/popular, /api/stats/weekly (with 47 baseline)
- GET /api/share/duel/{id} (OG-enriched HTML w/ HTML-escaped title)
- StaticFiles mount /api/uploads
- Pages: / (hero + popular feed), /nieuw (upload w/ client-side compression), /duel/:id (swipe vote + 3s delayed CTA + weekly counter), /duel/:id/resultaat (4 off-screen canvases for instant toggle, with-photos/clean × Stories/Feed; download via html-to-image with iOS Safari fallback; WhatsApp share; delete button for maker), /privacy (GDPR), 404
- Localstorage stores delete tokens for makers so the verwijder-knop is visible only to the duel creator's browser

## Backlog
- P1: Email delivery integration test once RESEND_API_KEY is provided
- P1: Trust X-Forwarded-For for vote anti-dup (k8s ingress collapses egress IPs)
- P2: Privé-modus (sprint 2)
- P2: Gezicht-blur feature (sprint 2)
- P2: Categorie-tags, TikTok-integratie, betaalde features

## Test credentials
N/A — app requires no accounts.

## Sprint 2 — Security & Juridisch (2026-02)
- Upload security: strict MIME + magic-byte validation (JPEG/PNG/WebP only), 10MB cap, UUID filenames, EXIF strip
- Rate limiting (in-memory IP buckets, honors RATE_LIMIT_DISABLED env):
  - POST /api/duels: 3/IP/hour
  - POST /api/duels/{id}/vote: 10/IP/hour
  - POST /api/duels/{id}/report: 10/IP/hour
- Security headers middleware: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Report system: POST /api/duels/{id}/report, 3 reasons (offensive/no_consent/spam), IP-hash dedup per duel, auto-hide at 3 reports, async Resend abuse alert
- Hidden state: `is_hidden` flag in GET response, filtered from popular feed, blocks voting
- Pages: /privacy ✓, /voorwaarden ✓ (added Sprint 1.5 with full legal text)
- Cookie banner: bottom strip, 365-day consent cookie via od_cookie_consent
- Trust X-Forwarded-For for client IP (k8s ingress fix)

## Sprint 3 — i18n NL + EN (2026-02)
- Frontend: locales/{nl,en}.json + i18n.jsx (LanguageProvider, useT, votesLabel) + axios Accept-Language interceptor
- Language detection: od_lang cookie (365d) wins → falls back to navigator.language.startsWith('nl')
- Language switch in HEADER (moved from footer to stay clickable even when cookie banner is shown)
- Backend: locales/{nl,en}.json (email + og_description), request_lang() helper, doc.lang stored on create, send_result_email reads duel.lang, /api/share/duel returns lang-aware og:description + html attribute
- Privacy + Terms intentionally remain Dutch legal text (translating would alter meaning); chrome around them is translated
- 11/11 i18n backend tests pass on top of existing 32/32 Sprint 1+2 suite

## Sprint 4 — Plesk-ready deployment package (2026-02)
- `/app/ecosystem.config.js` — PM2 + uvicorn (port 3000, --proxy-headers, 2 workers)
- `/app/migrate.py` — MongoDB index bootstrap (duels, votes, reports, stats)
- `/app/.env.example` — full env template (Mongo, SMTP, Resend, paths)
- `/app/README-deploy.md` — 11-step Plesk walkthrough + troubleshooting table
- `/app/build-frontend.sh` — yarn build → copies to backend/frontend_build
- `/app/.gitignore` — extended with uploads, frontend_build, logs, .env
- server.py: UPLOAD_DIR + FRONTEND_BUILD_DIR env-configurable; SPA catch-all route serves React build alongside API; flexible mailer (SMTP → Resend → no-op)
- deployment_agent static analysis: PASS, zero findings
