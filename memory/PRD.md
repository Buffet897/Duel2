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
