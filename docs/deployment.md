# Deployment

This is the production runbook. AdVanta AI is shaped to run on **Render** out of the box (see [`infra/render/render.yaml`](../infra/render/render.yaml)) and on any **Docker** host via the production compose file.

---

## 1. Components

| Service | Purpose | Port | Image |
|---|---|---|---|
| `api` | FastAPI app + admin + Stripe webhook | 8000 | [`infra/docker/Dockerfile.api`](../infra/docker/Dockerfile.api) |
| `web` | React SPA (nginx) | 80 | [`infra/docker/Dockerfile.web`](../infra/docker/Dockerfile.web) |
| `postgres` | Primary database | 5432 | `postgres:16-alpine` |
| `redis` | Rate limiter + Celery broker (M13+) | 6379 | `redis:7-alpine` |

---

## 2. Quickstart — production-shaped local run

```bash
export APP_SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Visit `http://localhost:8080` (web) and `http://localhost:8000/api/v1/docs` (API).

---

## 3. Render

The blueprint provisions everything: Postgres, Redis, the API web service, the
Celery worker (with beat), and the nginx-served SPA. Domain wiring for
**getadvanta.app** is baked into [`render.yaml`](../infra/render/render.yaml) —
only secrets are entered by hand.

1. Push the repo to GitHub.
2. Render → **New** → **Blueprint**, point at the repo. It auto-discovers
   [`infra/render/render.yaml`](../infra/render/render.yaml).
3. Set the secret (`sync: false`) env vars in the dashboard:
   - `ENCRYPTION_KEY` — `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Must be byte-identical on `advanta-api` and `advanta-worker`** (tokens encrypted by one are decrypted by the other).
   - `APP_SECRET_KEY` — auto-generated on `advanta-api`; copy that exact value onto `advanta-worker`.
   - `OPENAI_API_KEY` — your OpenAI key. The default provider/model is `openai` / `gpt-5.4-mini` (set as plain values in the blueprint).
   - Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_STARTER` / `_PRO` / `_AGENCY`.
   - Provider OAuth (Google / Meta / LinkedIn) per [`integrations.md`](integrations.md).
   - Optional: `SENTRY_DSN`, `PAGESPEED_API_KEY`, SMTP (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`), inbound email (`INBOUND_EMAIL_DOMAIN`/`INBOUND_EMAIL_SECRET`).

   `FRONTEND_URL`, `BACKEND_URL`, `CORS_ORIGINS`, and `VITE_API_BASE_URL` are
   **already set** to the getadvanta.app values in the blueprint — no manual entry.
4. `alembic upgrade head` runs as a `preDeployCommand` on both the API and the
   worker, so every release applies pending migrations before traffic shifts.

### 3.1 Domains & DNS (getadvanta.app)

| Host | Render service | Serves |
|---|---|---|
| `getadvanta.app` (apex) | `advanta-web` | SPA — marketing + app |
| `www.getadvanta.app` | `advanta-web` | SPA |
| `api.getadvanta.app` | `advanta-api` | FastAPI |

These are declared under each service's `domains:` in the blueprint. After the
first deploy, open each service → **Settings → Custom Domains** to read the
**exact** DNS target Render assigns, then add these records at your registrar
for `getadvanta.app`:

| Type | Name | Value |
|---|---|---|
| CNAME | `www` | the `*.onrender.com` target Render shows for `advanta-web` |
| CNAME | `api` | the `*.onrender.com` target Render shows for `advanta-api` |
| A / ALIAS | `@` (apex) | the apex target Render shows — use ALIAS/ANAME if your registrar supports it, otherwise Render's A record IP |

Render provisions and auto-renews TLS once DNS verifies. The apex can't use a
CNAME, so use your registrar's ALIAS/ANAME flattening or Render's A record. If
you make `www` (or the apex) canonical with a redirect, keep `FRONTEND_URL` and
`CORS_ORIGINS` consistent with the canonical host.

### 3.2 Uploaded images are not persistent by default

Blog cover/inline images upload to `/app/uploads` on the API container, which is
**ephemeral** on Render — they're lost on every deploy/restart. For production,
use object storage (S3 / Cloudflare R2), or uncomment the `disk:` block in the
blueprint (mind the single-instance + non-root caveats noted there). Everything
else is stored in Postgres and is unaffected.

---

## 4. OAuth callbacks

Each provider's OAuth app must whitelist exactly (`BACKEND_URL` = `https://api.getadvanta.app`):

```
https://api.getadvanta.app/api/v1/integrations/{provider}/callback
```

Where `{provider}` is one of `google_ads`, `google_analytics`, `google_search_console`, `meta_ads`, `linkedin_ads`. For Google **sign-in** (login), also authorize the redirect used by the auth flow and the frontend finish page `https://getadvanta.app/auth/google/finish` — see [`integrations.md`](integrations.md).

---

## 5. Stripe webhook

In the Stripe dashboard add a webhook endpoint at:

```
https://api.getadvanta.app/api/v1/billing/webhook
```

Events to enable:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.

For local development:

```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
```

---

## 6. CORS

`CORS_ORIGINS` is a JSON array of the production frontend origins, already set in
the blueprint:

```env
CORS_ORIGINS=["https://getadvanta.app","https://www.getadvanta.app"]
```

Add/remove origins here if you change the canonical host. Cookies
(`advanta_refresh`) require `credentials: include` from the browser; CORS allows
credentials, which it already does in [`main.py`](../apps/api/main.py). Origins
must be exact (scheme + host, no trailing slash).

---

## 7. Migrations

Migrations live in [`apps/api/alembic/versions/`](../apps/api/alembic/versions/) and run with:

```bash
alembic upgrade head    # apply pending
alembic current         # show current revision
alembic downgrade -1    # roll back the most recent migration
```

In production, this is the `preDeployCommand` on Render and the manual step in the Docker quickstart.

---

## 8. Promoting a superuser

The first superuser must be created out-of-band. On Render, open the
`advanta-api` service → **Shell** and run the snippet below (drop the
`docker compose … run --rm api` prefix — you're already inside the container).
On a Docker host, run it as a one-off:

```bash
docker compose -f docker-compose.prod.yml run --rm api python -c "
from sqlalchemy import update
from app.db.session import SessionLocal
from app.models.user import User

with SessionLocal() as db:
    db.execute(update(User).where(User.email=='you@example.com').values(is_superuser=True))
    db.commit()
"
```

After that, the **Admin** page becomes visible in the sidebar for that user.
