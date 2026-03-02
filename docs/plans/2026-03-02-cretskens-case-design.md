# Cretskens Case Folder Design

## Context
We need a new `cases/cretskens` bundle for the `questioner` profile, while avoiding duplicate prompt sources between PiXie case config and `pixie-questioner` domain profiles.

## Decisions
1. Use `questioner` as backend target.
2. Keep identifiers aligned:
- `ACTIVE_CLIENT_ID=cretskens`
- `ACTIVE_CLIENT_DISPLAY_NAME=CRETSKENS`
- `ACTIVE_CLIENT_COLLECTION_ID=cretskens`
3. Temporary branding: copy Brooklyn assets into Cretskens branding paths.
4. Welcome and header copy should be Cretskens-specific (wine pairing context).
5. No location context for now:
- no `ACTIVE_CLIENT_ALLOWED_LOCATIONS`
- `locations.caddy` stays default-empty mapping
6. Use profile-driven questioner configuration only:
- `DOMAIN_PROFILE_PATH=profiles/cretskens/domain_profile.yml`
- do **not** define case-level prompt env vars (`SYSTEM_PROMPT_PATH`, `SUMMARIZER_PROMPT_PATH`, `QUESTIONNAIRE_TEMPLATE_PATH`, `QUESTIONNAIRE_NOTULIST_PROMPT_PATH`).

## Proposed Case Structure
- `cases/cretskens/client.env`
- `cases/cretskens/secrets.env` (local, not committed)
- `cases/cretskens/locations.caddy`
- `cases/cretskens/notes.md`
- `cases/cretskens/branding/logo.png`
- `cases/cretskens/branding/logo_no_text.png`
- `cases/cretskens/branding/background.png`

No `cases/cretskens/prompts/` directory is required for this setup.

## Draft Runtime Values
- `ACTIVE_CLIENT_PRIMARY_COLOR=#6A1E2C`
- `ACTIVE_CLIENT_WELCOME_MESSAGE="Hallo, ik ben je Cretskens AI-assistent. Ik help je graag om de juiste wijn bij je gerecht te vinden. Vertel me wat je gaat eten, dan maak ik een duidelijke samenvatting voor gericht advies in de winkel."`
- `ACTIVE_CLIENT_CHAT_HEADER_TITLE=Cretskens Wijnassistent`
- `PIXIE_BACKEND_TARGET=questioner`
- `ENABLED_BACKENDS=rag`
- `AUDIT_PROFILE=cretskens`
- `DOMAIN_PROFILE_PATH=profiles/cretskens/domain_profile.yml`

## Risks and Mitigations
- Risk: accidental reintroduction of case-level prompt env vars causes dual configuration paths.
- Mitigation: keep one source of truth (`DOMAIN_PROFILE_PATH`) and verify no prompt env vars are present in `cases/cretskens/client.env`.

## Success Criteria
1. `cases/cretskens` exists with working case files and branding assets.
2. Case is immediately runnable with `CASE_ID=cretskens`.
3. No prompt duplication remains at case level for questioner.
