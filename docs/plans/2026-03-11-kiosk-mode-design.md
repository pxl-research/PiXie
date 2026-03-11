# Questioner UI Profiles Design

## Context

PiXie kiest vandaag een case via `CASE_ID` en leest case-specifieke configuratie uit:

- `cases/<CASE_ID>/client.env`
- `cases/<CASE_ID>/secrets.env`
- `cases/<CASE_ID>/branding/`

De standaard `chat-ui` sluit daar al goed op aan via runtime-config en de bestaande `ACTIVE_CLIENT_*` variabelen. De kiosk-flow moet dezelfde case-bundel blijven gebruiken als bron van waarheid. Omdat PiXie al met `COMPOSE_PROFILES` werkt, is dat ook de juiste plek om tussen standaard UI en kiosk UI te schakelen.

## Goals

- Gebruik Compose-native profielselectie in PiXie via `.env`.
- Houd `cases/<CASE_ID>/client.env` en `branding/` als one source of truth.
- Hergebruik bestaande `ACTIVE_CLIENT_*` en `PIXIE_QUESTIONER_CASE_ID` namen.
- Vermijd nieuwe env vars tenzij ze echt nodig zijn.

## Non-goals

- Geen runtime toggle binnen dezelfde frontend.
- Geen hernoeming van bestaande `client.env` sleutels.
- Geen aparte boolean zoals `KIOSK_MODE`.
- Geen uitbreiding van kiosk-only copy/timing-config in v1, tenzij meerdere kiosk-cases dat later nodig maken.

## Current State

Voor `cases/cretskens/client.env` bestaan al de velden die de kiosk grotendeels nodig heeft:

- `ACTIVE_CLIENT_DISPLAY_NAME`
- `ACTIVE_CLIENT_PRIMARY_COLOR`
- `ACTIVE_CLIENT_LOGO_URL`
- `ACTIVE_CLIENT_LOGO_NO_TEXT_URL`
- `ACTIVE_CLIENT_BACKGROUND_IMAGE_URL`
- `ACTIVE_CLIENT_WELCOME_MESSAGE`
- `ACTIVE_CLIENT_CHAT_HEADER_TITLE`
- `PIXIE_QUESTIONER_CASE_ID`

Dat betekent dat de naming al bruikbaar is. De echte mismatch zit in de delivery:

- PiXie is runtime-gedreven via case mounts.
- De huidige kiosk-app gebruikt nog build-time `VITE_*` config.

## Decision

### 1. `COMPOSE_PROFILES` kiest de actieve questioner UI

PiXie gebruikt voor questioner expliciet twee UI-profielen:

- `ui-standard`
- `ui-kiosk`

Typische `.env` waarden:

```env
COMPOSE_PROFILES=questioner,ui-standard
COMPOSE_PROFILES=questioner,ui-kiosk
```

Gedrag:

- `questioner,ui-standard`: start de bestaande standaard `chat-ui` samen met `chat-ui-proxy`
- `questioner,ui-kiosk`: start de kiosk-frontend zonder `chat-ui-proxy`

### 2. PiXie kiest exact één actieve questioner frontend

Per deployment staat slechts één frontend achter de gepubliceerde poort:

- standaard questioner-frontend, of
- kiosk questioner-frontend

De backend-stack blijft questioner-gedreven. Alleen de frontendrenderer wijzigt.

### 3. `client.env` blijft de branding- en copy-bron

Voor kiosk mode blijven de bestaande variabelen leidend:

- `ACTIVE_CLIENT_*` voor branding/copy
- `PIXIE_QUESTIONER_CASE_ID` voor de gekoppelde case

Er worden in v1 geen alternatieve kiosk-brandingnamen toegevoegd.

### 4. Alleen minimale nieuwe config in v1

Nieuw in PiXie:

- geen nieuwe boolean toggle
- alleen expliciet gebruik van bestaande `COMPOSE_PROFILES`

Niet nieuw in v1:

- geen kiosk-specifieke duplicaten van `ACTIVE_CLIENT_*`
- geen extra env vars voor `startLabel`, `helpText`, `idleTimeout`, `resetDelay`

Die kiosk-only waarden blijven voorlopig app-defaults. Pas bij een tweede kiosk-case met andere noden mogen optionele extra velden overwogen worden.

## Compose Selection

Docker Compose kan deze selectie al native aan via `COMPOSE_PROFILES`. Een aparte wrapperlaag is dus niet nodig.

Voor questioner zijn er twee frontendpaden:

- standaard: `chat-ui-questioner` + `chat-ui-proxy-questioner` + `chat-gateway`
- kiosk: `chat-kiosk-ui-questioner` + `chat-gateway-kiosk`

Gedeeld:

- `questioner-api`
- audit stack

De actieve gateway blijft naar alias `ui` routeren. Welke UI-service die alias levert, hangt af van het gekozen Compose-profiel.

## Gateway Model

De standaard questioner-UI blijft werken via:

- `chat-gateway`
- route `/api/*` -> `chat-ui-proxy`
- route `/` -> `chat-ui`

De kiosk-UI krijgt een aparte gatewayvariant:

- `chat-gateway-kiosk`
- route `/questioner/*` -> `questioner-api`
- route `/` -> `chat-kiosk-ui`

Zo vermijdt kiosk mode de extra `chat-ui-proxy` service.

## Important Constraint

Om de case-folder echt one source of truth te houden, moet de kiosk-image uiteindelijk runtime-config uit dezelfde case-env kunnen lezen als de standaard UI.

Dat vereist een upstream aanpassing in `pixie-chat-ui`:

- kiosk moet bestaande `ACTIVE_CLIENT_*` en `PIXIE_QUESTIONER_CASE_ID` kunnen consumeren op runtime of container-start
- niet alleen via build-time `VITE_*` args

Voor de huidige Cretskens rollout is een tijdelijke Cretskens-specifieke kiosk-build aanvaardbaar, maar dat is geen generieke eindtoestand.

## Acceptance Criteria

- In PiXie volstaat `COMPOSE_PROFILES=questioner,ui-standard` of `COMPOSE_PROFILES=questioner,ui-kiosk` in `.env`.
- Bestaande `cases/<CASE_ID>/client.env` naming blijft intact.
- `cases/<CASE_ID>/branding/` blijft de assetbron voor beide frontends.
- `questioner` deployments starten exact één actieve frontend.
- De README legt uit hoe de frontendselectie werkt.
