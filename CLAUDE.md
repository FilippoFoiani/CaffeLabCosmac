# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Caffè Lab: a small Flask + SQLite web app that replaces a paper tally sheet for a lab's coffee and water. People scan a QR code on the machine, tap +/− per product, and the app keeps one balance per person. The codebase is **in Italian**: identifiers, comments, commit messages, docs (`README.md`, `GUIDA.md`) and the UI source strings. Keep new code and text in Italian to match.

Deployed on PythonAnywhere's free plan (no scheduled tasks; WSGI imports `from app import app as application`). Updates are shipped as a zip that overwrites the code but never `dati/`. `GUIDA.md` is the user-facing install/upgrade guide; update it when behavior that admins or users see changes.

For every user-visible change, also add an entry at the **top** of `NOVITA` in `novita.py`, with a date id plus short `it` and `en` lines. Users see it once on the home page as "Novità dell'aggiornamento" until they tick "Ho letto". Build the deploy zip from the repo with `git -c core.autocrlf=false archive --format=zip --prefix=caffe-lab/ -o ../../caffe-lab_AAAA-MM-GG.zip HEAD`. The `caffe-lab/` prefix matters: the server's Bash steps unzip over `~/caffe-lab`. GitHub's "Download ZIP" uses the wrong folder name.

## Commands

```bash
pip install -r requirements.txt          # Flask, openpyxl, segno (QR), tzdata
python3 app.py                           # dev server on http://localhost:5000
python3 -m pytest -q                     # all tests (pytest is not in requirements.txt)
python3 -m pytest -q test_app.py::test_spesa   # a single test
python3 gestione.py                      # console admin commands: importa | elenco | admin <id> | reset-pin <id> | avvisi
```

No linter or build step is configured.

On Windows, run the tests with UTF-8 mode on (`PYTHONUTF8=1 python -m pytest -q` in Bash, `$env:PYTHONUTF8=1` in PowerShell). Otherwise `gestione.py` crashes printing "−" (U+2212) to the cp1252 console and every test fails in `setup_module`. The production server is Linux and doesn't need this.

## Architecture

Nearly everything is in **`app.py`**, a single module: config, schema, helpers, all routes, email, Excel export. `gestione.py` imports helpers from it for console use. `lingue.py` holds translations. `templates/` are Jinja pages that extend `base.html`.

**Ledger model.** Every operation is a row in `movimenti` with a signed `importo_cent` (integer cents: + is credit, − is debt). A balance is always `SUM(importo_cent) WHERE annullato=0`. No balance column exists anywhere. Undo sets `annullato=1` and never deletes. Rows from one action (a multi-product purchase, or both sides of a transfer) share a `gruppo` UUID. Write through `registra()`, and `registra_pagamento()` for the two-row transfer. `tipo` is one of `acquisto | trasferimento | spesa | rettifica | iniziale`.

**Shared accounts.** `persone.speciale=1` marks shared accounts (Cassa, Acqua, Macchinetta del caffè, formerly "Conto Caffè") that cannot log in. A product with `addebito_id` set charges that account instead of the buyer, and statistics count it on that account too, as the balances do.

**Approval flow.** Group expenses (`spesa`) and payments to someone else go into `richieste` with `stato='attesa'`. Ledger rows are written only when the request is approved (`decidi_richiesta`; `puo_decidere` decides who may approve). First logins and new registrations are also held (`persone.approvato=0`, which makes `g.in_attesa` and redirects to `/attesa`) until an admin approves. Decisions are logged in `registro_accessi`.

**Schema migrations are automatic and additive.** `inizializza_db()` runs at import time. It applies `SCHEMA` (`CREATE TABLE IF NOT EXISTS`), adds missing columns with `ALTER TABLE` after checking `PRAGMA table_info`, and seeds defaults with `INSERT OR IGNORE` into `impostazioni`. Production databases are upgraded this way just by reloading. Add new columns there instead of editing existing `CREATE TABLE` statements, and never rename or drop columns.

**Request lifecycle.**
- `before_request` resolves the language and enforces CSRF on every POST: forms must include `<input name="_csrf" value="{{ csrf_token() }}">`.
- `before_request` also loads `g.utente`. Sessions are invalidated by bumping `persone.versione_sessione`, as PIN reset does.
- Use the `@login_richiesto` and `@admin_richiesto` decorators.
- Purchase forms carry a `nonce` to block double submits.

**Monday jobs without cron.** `after_request` (`lavori_automatici`) checks whether this week's reminders or backup have already gone out. Weeks are tracked as ISO week strings in `impostazioni`, rolling over Monday at `ORA_AVVISO`. If they haven't, it sends emails in `response.call_on_close`, after the response. `/cron/avvisi?token=...` is an optional external trigger.

**i18n.** Source strings are Italian and wrapped in `_("...")`, in both Python and templates. `lingue.EN` maps Italian text to English. Text missing from `EN` falls back to Italian. **`test_traduzioni_complete` fails if any `_("...")` literal in `app.py` or `templates/*.html` lacks an `EN` entry**, so add the translation whenever you add or change a string. Ledger `nota` values are stored in Italian, and `descrizione()` translates them at render time by matching known prefixes ("presa da ", "Spesa per il gruppo: ", …). Keep those prefixes stable.

**Config** comes from environment variables: `CAFFE_DATA_DIR` (default `./dati`), `CAFFE_HTTPS`, `CAFFE_URL`, `CAFFE_SMTP_USER`/`CAFFE_SMTP_PASSWORD` (email is disabled when unset), `CAFFE_CRON_TOKEN`, `CAFFE_TZ`, `CAFFE_ORA_AVVISO`, `SECRET_KEY` (otherwise read from or generated into `dati/`). `dati/` holds `caffe.db`, the secret key and receipt photos (`scontrini/`). It is gitignored and must never be committed or deleted.

## Tests

`test_app.py` sets `CAFFE_DATA_DIR` to a temp dir **before** importing `app`, because the DB is initialized at import. `setup_module` runs `gestione.py importa saldi_iniziali.csv` as a subprocess and asserts `26 aggiunti`, so editing that CSV breaks the test. All tests share one database and some build on earlier state, so run single tests with that in mind. Helpers: `entra()` logs in (doing the first-login step and approval), `entra_come_admin()`, `csrf()`/`nonce()` scrape tokens from HTML, and `FintoSMTP` monkeypatches SMTP for email tests.

`static/stile.css` must keep `[hidden] { display: none !important; }`, which a test checks. The CSS cache-buster `VERSIONE_CSS` comes from the file's mtime.
