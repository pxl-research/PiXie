# Questioner UI Profiles Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Compose-native questioner UI selection in PiXie so Jetson deployments can choose the standard UI or kiosk UI via `COMPOSE_PROFILES` while keeping the case folder as the configuration source of truth.

**Architecture:** Keep the questioner backend stack shared, split the frontend into standard and kiosk variants, and let Docker Compose select the active questioner UI through `COMPOSE_PROFILES`. Reuse existing `ACTIVE_CLIENT_*` and `PIXIE_QUESTIONER_CASE_ID` values instead of introducing a second kiosk-specific config vocabulary.

**Tech Stack:** Docker Compose, Caddy, env-file based case config, existing PiXie questioner stack.

---

### Task 1: Document and validate the Compose profile contract

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-11-kiosk-mode-design.md`
- Modify: `.env`

**Step 1: Write the failing test**

Add a short manual acceptance checklist to the plan/README draft that states:

- `COMPOSE_PROFILES=questioner,ui-standard` must select the standard questioner frontend
- `COMPOSE_PROFILES=questioner,ui-kiosk` must select the kiosk frontend
- operators should enable exactly one questioner UI profile at a time

**Step 2: Run test to verify it fails**

Run: `rg -n "ui-standard|ui-kiosk|COMPOSE_PROFILES" README.md docs/plans/2026-03-11-kiosk-mode-design.md .env`

Expected: the README and `.env` do not yet explain the new questioner UI profile split.

**Step 3: Write minimal implementation**

Update `README.md` and `.env` with:

- the `ui-standard` and `ui-kiosk` profiles
- the meaning of each combination with `questioner`
- the fact that plain `docker compose up -d` still works when `.env` sets `COMPOSE_PROFILES`
- the fact that the case folder remains the source of truth

**Step 4: Run test to verify it passes**

Run: `rg -n "ui-standard|ui-kiosk|case folder|source of truth|COMPOSE_PROFILES" README.md .env`

Expected: all operator-facing instructions are present.

**Step 5: Commit**

```bash
git add README.md .env docs/plans/2026-03-11-kiosk-mode-design.md
git commit -m "docs: document questioner ui profiles"
```

### Task 2: Split questioner frontend selection into explicit Compose profiles

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Write the failing test**

Define the expected topology in comments or scratch notes before editing:

- shared service: `questioner-api`
- standard path: `chat-ui-questioner`, `chat-ui-proxy-questioner`, `chat-gateway`
- kiosk path: `chat-kiosk-ui-questioner`, `chat-gateway-kiosk`

The failure is conceptual: current `docker-compose.yml` only has the standard questioner frontend path.

**Step 2: Run test to verify it fails**

Run: `rg -n "chat-kiosk-ui|chat-ui-questioner|chat-ui-proxy-questioner|profiles:" docker-compose.yml`

Expected: kiosk frontend service is absent and questioner frontend selection is not split cleanly.

**Step 3: Write minimal implementation**

Refactor `docker-compose.yml` so that:

- shared questioner services stay available without frontend ambiguity
- standard questioner UI services live behind `ui-standard`
- kiosk questioner UI services live behind `ui-kiosk`
- both frontend variants can satisfy the `ui` alias expected by the active gateway
- only the standard path uses the `proxy` alias
- the kiosk path does not start `chat-ui-proxy`

Do not rename existing `ACTIVE_CLIENT_*` env vars.

**Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml config >/tmp/pixie-compose.out && rg -n "chat-kiosk-ui-questioner|ui-standard|ui-kiosk|alias" /tmp/pixie-compose.out`

Expected: both frontend paths exist in config, and aliases/profile wiring are explicit.

**Step 5: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: split questioner ui profiles"
```

### Task 3: Add a kiosk-specific gateway path

**Files:**
- Create: `Caddyfile.kiosk`
- Modify: `docker-compose.yml`
- Modify: `README.md`

**Step 1: Write the failing test**

Create an acceptance checklist for:

- kiosk mode must bypass `chat-ui-proxy`
- kiosk mode must expose the kiosk frontend on the usual port `3000`
- kiosk mode must route `/questioner/*` directly to `questioner-api`

**Step 2: Run test to verify it fails**

Run: `test -f Caddyfile.kiosk`

Expected: exit code `1` because the kiosk gateway config does not exist yet.

**Step 3: Write minimal implementation**

Create `Caddyfile.kiosk` and wire it into a `chat-gateway-kiosk` service so that:

- kiosk mode serves the frontend from `ui:8080`
- kiosk mode proxies `/questioner/*` directly to `questioner-api:8000`
- kiosk mode can keep the QR/location redirect behavior if configured

**Step 4: Run test to verify it passes**

Run:

```bash
COMPOSE_PROFILES=questioner,ui-kiosk docker compose config >/tmp/pixie-kiosk.out
rg -n "Caddyfile.kiosk|questioner-api|ui:8080" /tmp/pixie-kiosk.out
```

Expected:

- rendered config includes the kiosk gateway and kiosk UI wiring

**Step 5: Commit**

```bash
git add Caddyfile.kiosk docker-compose.yml README.md
git commit -m "feat: add kiosk gateway profile"
```

### Task 4: Wire the kiosk frontend image into PiXie

**Files:**
- Modify: `docker-compose.yml`
- Modify: `README.md`

**Step 1: Write the failing test**

Define the operator expectation:

- when `ui-kiosk` is active, PiXie must start a kiosk frontend service instead of the standard questioner UI

**Step 2: Run test to verify it fails**

Run: `rg -n "pixie-chat-kiosk-ui|chat-kiosk-ui-questioner|ui-kiosk" docker-compose.yml README.md`

Expected: no PiXie-side kiosk image wiring yet.

**Step 3: Write minimal implementation**

Add a kiosk UI service to `docker-compose.yml` using an explicit image reference:

```yaml
image: ghcr.io/pxl-research/pixie-chat-kiosk-ui:main
```

Mount the active case branding folder in the same way the standard UI does, and ensure it joins the `pixie` network with alias `ui`.

Note in `README.md` that:

- kiosk mode is questioner-only in v1
- the kiosk image must support runtime case config for full generic behavior

**Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml config >/tmp/pixie-compose.out && rg -n "ghcr.io/pxl-research/pixie-chat-kiosk-ui|branding" /tmp/pixie-compose.out`

Expected: kiosk image and case branding mount are present in rendered config.

**Step 5: Commit**

```bash
git add docker-compose.yml README.md
git commit -m "feat: add kiosk frontend service"
```

### Task 5: Verify end-to-end mode selection

**Files:**
- Test: `docker-compose.yml`
- Test: `Caddyfile.kiosk`
- Test: `README.md`

**Step 1: Write the failing test**

Define the final checks:

- standard mode resolves a standard frontend path
- kiosk mode resolves a kiosk frontend path
- case branding remains mounted from `cases/${CASE_ID}/branding`
- no existing `ACTIVE_CLIENT_*` names were renamed

**Step 2: Run test to verify it fails**

Run the compose render before all prior tasks are complete:

```bash
COMPOSE_PROFILES=questioner,ui-kiosk docker compose config
```

Expected: one or more of the checks above are still missing.

**Step 3: Write minimal implementation**

Finish any missing compose, alias, README, or gateway adjustments until both modes render cleanly.

**Step 4: Run test to verify it passes**

Run:

```bash
CASE_ID=cretskens COMPOSE_PROFILES=questioner,ui-standard docker compose config >/tmp/pixie-standard.out
CASE_ID=cretskens COMPOSE_PROFILES=questioner,ui-kiosk docker compose config >/tmp/pixie-kiosk.out
rg -n "ACTIVE_CLIENT_DISPLAY_NAME|ACTIVE_CLIENT_PRIMARY_COLOR|ACTIVE_CLIENT_WELCOME_MESSAGE" cases/cretskens/client.env
```

Expected:

- both config renders succeed
- standard output includes the standard questioner frontend path and proxy
- kiosk output includes the kiosk frontend path without the standard proxy
- the case env still exposes the original variable names unchanged

**Step 5: Commit**

```bash
git add docker-compose.yml Caddyfile.kiosk README.md
git commit -m "test: verify questioner ui profile selection"
```

## External Dependency

For full compliance with the approved design, the kiosk frontend image in the `pixie-chat-ui` repo must consume runtime case config derived from the existing `ACTIVE_CLIENT_*` and `PIXIE_QUESTIONER_CASE_ID` values. If the published kiosk image still relies on build-time `VITE_*` values, complete that upstream change before treating the PiXie `ui-kiosk` profile as generically reusable across cases.
