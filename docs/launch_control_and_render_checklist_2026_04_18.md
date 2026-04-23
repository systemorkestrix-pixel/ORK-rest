# Launch Control And Render Checklist

## 1. Render Review

### Current deployment scripts
- `build.sh`
  - upgrades `pip`
  - installs `backend/requirements.txt`
- `start.sh`
  - ensures the SQLite parent directory exists when a sqlite `DATABASE_URL` is used
  - runs `alembic upgrade head` from `backend/`
  - starts `uvicorn main:app --host 0.0.0.0 --port "${PORT:-8122}" --app-dir backend`
- `render.yaml`
  - API service uses `healthCheckPath: /health`
  - API service expects external `DATABASE_URL`
  - static site points to `VITE_API_BASE_URL=https://restaurants-api.onrender.com/api`

### Launch judgment
- The Render boot path is now structurally valid for first deployment.
- The previous `GET / -> 404` issue is closed because the API root now returns a valid JSON health-style response.
- The `/api/public/*` 404 lines seen in older logs are not a Render boot failure by themselves. They indicate public requests without a tenant-scoped entry.

## 2. Final Render Checklist

### API service
- Confirm `DATABASE_URL` points to the target Supabase/Postgres database
- Confirm `JWT_SECRET` is set
- Confirm `SECRET_KEY` is set
- Confirm `MASTER_ADMIN_USERNAME` is set
- Confirm `MASTER_ADMIN_PASSWORD` is set
- Confirm `ADMIN_USERNAME` is set
- Confirm `ADMIN_PASSWORD` is set
- Confirm `APP_ENV=production`
- Confirm `DEBUG=false`
- Confirm `EXPOSE_DIAGNOSTIC_ENDPOINTS=true`
- Confirm `CORS_ALLOW_ORIGINS=https://restaurants-console.onrender.com`
- Keep `ALLOW_LEGACY_PASSWORD_LOGIN=false`

### Static site
- Confirm `VITE_API_BASE_URL=https://restaurants-api.onrender.com/api`
- Confirm rewrite rule `/* -> /index.html`

### First boot validation
- Open `/health`
- Open `/`
- Open `/manager/login`
- Open `/master/login`
- Confirm Alembic reaches head without retry loops
- Confirm the first manager login works against the external database

### Field validation after deploy
- Create one manual order
- Confirm order listing and ticket print work
- Confirm public scoped path works only through `/t/<tenant_code>/order`
- Confirm `/console/plans` redirects to `/console`
- Confirm no base-release screen exposes unfinished addon purchase UI

### Automated live smoke
- Run `python scripts/render_live_smoke.py`
- Required pass conditions:
  - API root -> `200`
  - API health -> `200`
  - tenant-entry -> `200`
  - unscoped public products -> `404`
  - console root -> `200`
  - manager login -> `200`

### Current live blocker as of `2026-04-22`
- `restaurants-api.onrender.com` returns `404`
- `restaurants-console.onrender.com` returns `404`
- This is now treated as a deployment-state blocker, not a local code-contract blocker

## 3. Addon Control Study

### What exists now
- `locked`
- `passive`
- `active`
- `paused`

### Real gap
- The system can pause and resume tools manually.
- It does not yet own the commercial lifecycle of a paid addon.
- There is no durable subscription window such as:
  - `paid_from`
  - `paid_until`
  - `grace_until`
  - `auto_pause_reason`
  - `last_billing_state`

### Correct business model
- A tool should be purchasable for a bounded duration.
- When the paid duration ends and there is no renewal, the tool must stop automatically.
- Historical data must remain preserved.
- The user should be blocked from operational use, not from reading the fact that the tool existed.

### Recommended status model
- `locked`: never purchased yet
- `passive`: back-office data collection only, no visible workspace
- `active`: paid and usable now
- `paused`: manually paused by admin
- `expired`: paid window ended and tool auto-stopped

### Required backend additions before exposing customer purchase UI
- addon subscription table or tenant-addon state table
- `paid_until` per addon per tenant
- automatic expiry evaluation during tenant context resolution
- `pause_reason` enum:
  - `manual`
  - `payment_expired`
  - `admin_hold`
- guardrails per tool:
  - `Kitchen`: cannot expire while kitchen orders are still open unless a grace policy exists
  - `Delivery`: cannot expire while dispatches are still active
  - `Warehouse`: cannot expire while stock procedures are incomplete

### Release rule
- Do not expose end-user addon purchase/activation UI until expiry control is implemented.
- Keep restaurant-side addon surface hidden in the base release.

## 4. Printing Study

### Current printing path
- Printing is currently initiated from `OrdersPage.tsx`
- It is a browser print flow around the order ticket view
- This is suitable for manual ticketing in the base workflow

### Current limitation
- There is no print queue
- There is no printer binding
- There is no backend print job lifecycle
- There is no kitchen auto-print trigger yet

### Correct future direction for Kitchen
- keep manual browser print for the base release
- add kitchen print policy settings later:
  - auto-print when entering kitchen queue
  - auto-print when marked ready
  - copies count
  - printer label/profile
- create backend print job records before integrating physical printer tooling

### Release rule
- No automatic kitchen printing should be exposed before a print job model exists.

## 5. Oversized Files

The oversized file scan has already been completed and recorded in:
- `docs/release_readiness_recovery_2026_04_18.md`

Priority files for split planning:
- `src/modules/operations/orders/OrdersPage.tsx`
- `backend/app/routers/manager.py`
- `src/modules/system/catalog/products/ProductsPage.tsx`
- `backend/app/schemas.py`
- `src/shared/api/client.ts`

## 6. Immediate Launch Decision

### Ready now
- Render deployment path
- base release login flow
- hidden restaurant-side addon page
- master-side tenant control cleanup
- scoped public routing

### Not ready for customer-facing release
- live Render deployment is still failing the smoke contract
- paid addon purchase automation
- automatic addon expiry
- kitchen printer automation
- end-user addon purchase page
