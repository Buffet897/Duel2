# OutfitDuel — Plesk Deployment Instructies

Doel: OutfitDuel draaiend krijgen op een VPS met Plesk. Stack: **FastAPI + MongoDB + React**. Eén `uvicorn`-proces serveert zowel `/api/*` als de gebouwde React-frontend.

---

## Vereisten op de VPS

- Plesk Obsidian (of nieuwer) met de **Node.js** én **Python** Plesk extensies
- Python ≥ 3.10 op de VPS (Plesk → Tools & Settings → Python)
- Node.js ≥ 18 (alleen nodig om de frontend te builden — kan ook lokaal en uploaden)
- MongoDB: óf lokaal geïnstalleerd, óf een managed cluster (MongoDB Atlas)
- Plesk-mailbox `noreply@outfitduel.com` (voor SMTP-uitgaande e-mail)

---

## Stap 1 — Bestanden uploaden

Pak het Emergent-export-zip uit en upload de mappen naar de VPS, bijv. via SSH:

```bash
scp -r outfitduel/ user@vps:/var/www/vhosts/outfitduel.com/httpdocs/
```

De resulterende layout op de server:

```
/var/www/vhosts/outfitduel.com/httpdocs/
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   ├── locales/
│   └── .env                ← maak je in stap 3
├── frontend/               ← React source (alleen nodig voor build)
├── ecosystem.config.js     ← PM2 config
├── migrate.py              ← MongoDB index bootstrap
├── build-frontend.sh
├── .env.example
└── README-deploy.md        ← dit bestand
```

---

## Stap 2 — MongoDB voorbereiden

**Optie A — lokaal op de VPS:**
```bash
sudo apt install mongodb-org
sudo systemctl enable --now mongod
```
Je `MONGO_URL` wordt dan `mongodb://localhost:27017`.

**Optie B — managed (aanbevolen):**
Maak een gratis cluster aan op [MongoDB Atlas](https://www.mongodb.com/atlas), voeg de VPS-IP toe aan de IP-whitelist en kopieer de connection string.

---

## Stap 3 — `.env` aanmaken

Kopieer en bewerk:

```bash
cd /var/www/vhosts/outfitduel.com/httpdocs
cp .env.example backend/.env
nano backend/.env
```

Vul minstens in:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=outfitduel
PUBLIC_BASE_URL=https://outfitduel.com
UPLOAD_DIR=/var/www/vhosts/outfitduel.com/httpdocs/uploads
FRONTEND_BUILD_DIR=/var/www/vhosts/outfitduel.com/httpdocs/backend/frontend_build
CORS_ORIGINS=https://outfitduel.com

SMTP_HOST=mail.outfitduel.com
SMTP_PORT=587
SMTP_USER=noreply@outfitduel.com
SMTP_PASS=jouw_mailbox_wachtwoord
FROM_EMAIL=noreply@outfitduel.com
CONTACT_EMAIL=info@outfitduel.com
ABUSE_EMAIL=abuse@outfitduel.com
```

> `RESEND_API_KEY` mag leeg blijven zolang SMTP is geconfigureerd — de mailer kiest automatisch SMTP → Resend → no-op.

---

## Stap 4 — Python dependencies installeren

```bash
cd /var/www/vhosts/outfitduel.com/httpdocs/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Stap 5 — MongoDB indexes aanmaken

```bash
cd /var/www/vhosts/outfitduel.com/httpdocs
python3 migrate.py
```

Verwachte output: `✓ duels indexes`, `✓ votes indexes`, `✓ reports indexes`. Idempotent — kan zonder zorgen herhaald worden.

---

## Stap 6 — Frontend builden

Optie A — lokaal builden en uploaden (sneller):
```bash
# Op je laptop:
./build-frontend.sh
scp -r backend/frontend_build user@vps:/var/www/vhosts/outfitduel.com/httpdocs/backend/
```

Optie B — direct op de VPS (vereist Node ≥ 18):
```bash
cd /var/www/vhosts/outfitduel.com/httpdocs
./build-frontend.sh
```

> De `FRONTEND_BUILD_DIR` uit `.env` moet wijzen naar de map met `index.html` + `static/`.

---

## Stap 7 — Upload-map klaarzetten

```bash
mkdir -p /var/www/vhosts/outfitduel.com/httpdocs/uploads
chmod 755 /var/www/vhosts/outfitduel.com/httpdocs/uploads
# Geef de Plesk app-user (vaak de domain-user) eigenaarschap:
chown -R outfitduel.com_user:psacln /var/www/vhosts/outfitduel.com/httpdocs/uploads
```

---

## Stap 8 — App starten

### Optie A (aanbevolen): PM2

```bash
sudo npm install -g pm2
cd /var/www/vhosts/outfitduel.com/httpdocs
mkdir -p logs
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u $(whoami) --hp $HOME   # follow de printed instructie
```

Status checken:
```bash
pm2 status
pm2 logs outfitduel --lines 50
```

### Optie B: Plesk Python extension

- Plesk → outfitduel.com → **Python**
- **Application Mode:** `production`
- **Application Root:** `/var/www/vhosts/outfitduel.com/httpdocs/backend`
- **Application Startup File:** `server.py`
- **Application Entry Point:** `app`
- Klik **Enable Python**, dan **Restart App**

---

## Stap 9 — Nginx reverse proxy

Plesk → outfitduel.com → **Apache & nginx Settings** → "Additional nginx directives":

```nginx
location / {
    proxy_pass         http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
    client_max_body_size 12M;          # foto-upload past zo binnen
}
```

> De FastAPI-app draait nu met `--proxy-headers --forwarded-allow-ips=*` waardoor `X-Forwarded-For` correct gerespecteerd wordt voor rate-limiting en anti-double-vote.

---

## Stap 10 — SSL (Let's Encrypt)

- Plesk → outfitduel.com → **SSL/TLS Certificates** → **Install** → **Let's Encrypt**
- Vink **Include www subdomain** aan (en eventueel een wildcard als je subdomeinen wilt)
- Vink **Redirect from HTTP to HTTPS** aan
- Klik **Get it Free**

---

## Stap 11 — Smoke test

Open `https://outfitduel.com` en doorloop:

- [ ] Home laadt; NL | EN switcher in de header werkt
- [ ] `/nieuw` accepteert 2 foto's → duel wordt aangemaakt → redirect naar `/duel/:id?created=1`
- [ ] Stemmen werkt; bars animeren; CTA verschijnt na 3 sec
- [ ] `/duel/:id/resultaat` toont kaartje-preview, download werkt (Stories + Feed)
- [ ] `/privacy` en `/voorwaarden` laden
- [ ] Rapporteer-popover werkt (3 redenen)
- [ ] Cookiebanner verschijnt op eerste bezoek
- [ ] WhatsApp-share link → opent met OG preview
- [ ] E-mail komt aan op `noreply@outfitduel.com` als verzender (test via maak-duel + `email=jij@…`, sluit het duel handmatig in MongoDB door `expires_at` 1 min in het verleden te zetten — de background loop pikt dat binnen 5 min op)

---

## Troubleshooting

| Symptoom | Vermoedelijke oorzaak | Oplossing |
|---|---|---|
| 502 Bad Gateway | Uvicorn draait niet op poort 3000 | `pm2 logs outfitduel` of `journalctl -u plesk-python-…` |
| Foto's geven 404 | `UPLOAD_DIR` mismatch | Controleer dat het pad in `.env` overeenkomt met de werkelijke map én dat hij schrijfbaar is |
| Foto's niet zichtbaar in OG-preview | `PUBLIC_BASE_URL` niet (HTTPS-)gezet | Zet `PUBLIC_BASE_URL=https://outfitduel.com` en restart |
| Rate-limit te streng tijdens testen | In-memory dict telt jouw IP mee | Zet `RATE_LIMIT_DISABLED=true` tijdelijk → restart |
| E-mail komt niet aan | SMTP-creds fout, of poort 587 dicht | Test SMTP los: `python3 -c "import smtplib; s=smtplib.SMTP('mail.outfitduel.com',587); s.starttls(); s.login('noreply@outfitduel.com','pw'); print('ok')"` |
| WhatsApp toont geen preview | Deel-URL is `/duel/:id` i.p.v. `/api/share/duel/:id` | Het frontend kopieer-link gebruikt automatisch de share-URL. Forceer een fresh crawl in [WhatsApp Sticker Maker](https://developers.facebook.com/tools/debug/) na DNS-wijziging |

---

## Updates uitrollen

```bash
cd /var/www/vhosts/outfitduel.com/httpdocs
git pull   # of nieuwe upload
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python3 migrate.py
./build-frontend.sh
pm2 restart outfitduel
```

Klaar.
