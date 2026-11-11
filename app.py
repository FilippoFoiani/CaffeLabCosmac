"""
Caffè Lab – web app per segnare caffè e acqua e gestire i saldi del gruppo.

Principio: ogni operazione (acquisto, pagamento, spesa, rettifica) è una riga
nel registro "movimenti". Il saldo di una persona è la somma dei suoi
movimenti non annullati. Saldo positivo = credito, negativo = debito.
"""
import io
import json
import os
import re
import secrets
import smtplib
import sqlite3
import tempfile
import uuid
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (Flask, abort, flash, g, has_app_context, redirect, render_template,
                   request, send_file, session, url_for)

from lingue import LINGUE, traduci
from novita import NOVITA
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

# --------------------------------------------------------------------------
# Configurazione
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CAFFE_DATA_DIR", os.path.join(BASE_DIR, "dati"))
DB_PATH = os.path.join(DATA_DIR, "caffe.db")
TZ = ZoneInfo(os.environ.get("CAFFE_TZ", "Europe/Rome"))
NOME_APP = os.environ.get("CAFFE_NOME", "Caffè Lab")

# Prodotti creati al primo avvio (prezzi e nomi si cambiano poi da Amministrazione).
# "conto": se indicato, il costo va su quel conto comune invece che su chi lo prende.
PRODOTTI_DEFAULT = [
    {"codice": "caffe", "nome": "Caffè", "emoji": "☕", "prezzo": 30, "conto": None},
    {"codice": "acqua", "nome": "Acqua", "emoji": "💧", "prezzo": 25, "conto": None},
    {"codice": "acqua_macchinetta", "nome": "Acqua macchinetta", "emoji": "🫗",
     "prezzo": 25, "conto": "Macchinetta del caffè"},
    {"codice": "bicchierino", "nome": "Bicchierino vuoto", "emoji": "🥤", "prezzo": 0, "conto": None},
]
# Magazzino: la merce che si compra e si consuma (quantità e soglie si cambiano da Amministrazione)
ARTICOLI_DEFAULT = [
    {"codice": "cialde", "nome": "Cialde", "emoji": "🟤", "soglia": 20},
    {"codice": "bottiglie", "nome": "Bottiglie", "emoji": "🍶", "soglia": 6},
    {"codice": "bicchierini", "nome": "Bicchierini", "emoji": "🥛", "soglia": 20},
]
# Cosa scala dal magazzino ogni prodotto preso (prodotto -> {articolo: pezzi})
RICETTE_DEFAULT = {
    "caffe": {"cialde": 1, "bicchierini": 1},
    "acqua": {"bottiglie": 1},
    "acqua_macchinetta": {"bottiglie": 1},
    "bicchierino": {"bicchierini": 1},
}
# Spiegazione sotto il prodotto, in home (l'admin la cambia da Amministrazione → Prodotti e prezzi)
DESCRIZIONI_DEFAULT = {
    "acqua_macchinetta": "Solo quando metti una bottiglia nuova nel serbatoio della macchinetta.",
    "bicchierino": "Solo se prendi un bicchierino senza caffè: quello del caffè è già contato.",
}
FINESTRA_ANNULLA = timedelta(minutes=10)   # entro quanto si può annullare da soli
ATTESA_MAX_PAGAMENTO = timedelta(days=3)   # poi un pagamento non confermato lo può confermare un admin
MAX_TENTATIVI_PIN = 5
DURATA_BLOCCO = timedelta(minutes=10)
MAX_QTA_PER_VOLTA = 20             # per ciascun prodotto in un singolo acquisto
MANUTENZIONI_ESEMPIO = [("Pulizia della macchinetta", 7), ("Decalcificazione", 30)]
TESTO_PULIZIA = "Ricorda di lasciare pulito dopo aver consumato il caffè!"
MAX_IMPORTO_CENT = 50000            # 500 €: oltre è quasi certamente un errore di battitura

# Avviso del lunedì per chi ha il saldo negativo
TESTO_AVVISO = "SALDA IL DEBITO, COMPRA IL CREDITO DI UN ALTRO UTENTE O COMPRA UNO DEI BENI"
ORA_AVVISO = int(os.environ.get("CAFFE_ORA_AVVISO", "8"))      # la settimana "riparte" lunedì alle 8:00
SMTP_HOST = os.environ.get("CAFFE_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("CAFFE_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("CAFFE_SMTP_USER", "")              # es. caffelab.unipg@gmail.com
SMTP_PASSWORD = os.environ.get("CAFFE_SMTP_PASSWORD", "")      # password per le app di Google
CRON_TOKEN = os.environ.get("CAFFE_CRON_TOKEN", "")            # facoltativo, per /cron/avvisi


def _chiave_segreta():
    """Usa SECRET_KEY se impostata, altrimenti ne genera una e la salva."""
    chiave = os.environ.get("SECRET_KEY")
    if chiave:
        return chiave
    os.makedirs(DATA_DIR, exist_ok=True)
    percorso = os.path.join(DATA_DIR, "secret_key")
    if not os.path.exists(percorso):
        with open(percorso, "w") as f:
            f.write(secrets.token_hex(32))
    with open(percorso) as f:
        return f.read().strip()


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config.update(
    MAX_CONTENT_LENGTH=1024 * 1024,                    # solo moduli, niente file da caricare
    SECRET_KEY=_chiave_segreta(),
    PERMANENT_SESSION_LIFETIME=timedelta(days=400),   # il telefono "si ricorda" di te
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("CAFFE_HTTPS", "0") == "1",
)

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS persone (
    id                INTEGER PRIMARY KEY,
    nome              TEXT    NOT NULL,
    cognome           TEXT    NOT NULL DEFAULT '',
    pin_hash          TEXT,
    admin             INTEGER NOT NULL DEFAULT 0,
    attivo            INTEGER NOT NULL DEFAULT 1,
    speciale          INTEGER NOT NULL DEFAULT 0,  -- conto senza accesso (es. Cassa)
    tentativi         INTEGER NOT NULL DEFAULT 0,
    bloccato_fino     TEXT,
    versione_sessione INTEGER NOT NULL DEFAULT 1,
    creato            TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS movimenti (
    id             INTEGER PRIMARY KEY,
    ts             TEXT    NOT NULL,              -- UTC, ISO 8601
    persona_id     INTEGER NOT NULL REFERENCES persone(id),
    tipo           TEXT    NOT NULL,              -- acquisto | trasferimento | spesa | rettifica | iniziale
    importo_cent   INTEGER NOT NULL,              -- con segno: + credito, - debito
    qta            INTEGER NOT NULL DEFAULT 0,    -- quantità (solo tipo acquisto)
    prodotto_id    INTEGER REFERENCES prodotti(id),
    controparte_id INTEGER REFERENCES persone(id),
    gruppo         TEXT,                          -- collega le righe di uno stesso acquisto/trasferimento
    nota           TEXT    NOT NULL DEFAULT '',
    creato_da      INTEGER REFERENCES persone(id),
    annullato      INTEGER NOT NULL DEFAULT 0,
    annullato_da   INTEGER REFERENCES persone(id),
    annullato_ts   TEXT
);
CREATE INDEX IF NOT EXISTS idx_mov_persona ON movimenti(persona_id);
CREATE INDEX IF NOT EXISTS idx_mov_gruppo  ON movimenti(gruppo);
CREATE TABLE IF NOT EXISTS prodotti (
    id           INTEGER PRIMARY KEY,
    codice       TEXT    UNIQUE,
    nome         TEXT    NOT NULL,
    emoji        TEXT    NOT NULL DEFAULT '',
    prezzo_cent  INTEGER NOT NULL,
    addebito_id  INTEGER REFERENCES persone(id),  -- se impostato, paga questo conto comune
    attivo       INTEGER NOT NULL DEFAULT 1,
    ordine       INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS impostazioni (
    chiave TEXT PRIMARY KEY,
    valore TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manutenzioni (
    id          INTEGER PRIMARY KEY,
    nome        TEXT    NOT NULL,
    ogni_giorni INTEGER NOT NULL,
    ultima_ts   TEXT    NOT NULL,                 -- UTC: ultima volta fatta (o creazione)
    ultima_da   INTEGER REFERENCES persone(id),
    attivo      INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS richieste (
    id             INTEGER PRIMARY KEY,
    ts             TEXT    NOT NULL,
    tipo           TEXT    NOT NULL,                   -- spesa | pagamento
    richiedente_id INTEGER NOT NULL REFERENCES persone(id),
    controparte_id INTEGER REFERENCES persone(id),     -- pagamento: chi ha ricevuto i soldi
    importo_cent   INTEGER NOT NULL,
    nota           TEXT    NOT NULL DEFAULT '',
    foto           TEXT    NOT NULL DEFAULT '',
    stato          TEXT    NOT NULL DEFAULT 'attesa',  -- attesa | approvata | rifiutata | annullata
    deciso_da      INTEGER REFERENCES persone(id),
    deciso_ts      TEXT
);
CREATE INDEX IF NOT EXISTS idx_richieste_stato ON richieste(stato);
CREATE TABLE IF NOT EXISTS registro_accessi (
    id         INTEGER PRIMARY KEY,
    ts         TEXT    NOT NULL,
    persona_id INTEGER,                     -- vuoto se l'account nuovo rifiutato è stato cancellato
    account    TEXT    NOT NULL DEFAULT '', -- nome dell'account com'era prima della richiesta
    richiesto  TEXT    NOT NULL DEFAULT '', -- nome e cognome inseriti da chi ha chiesto l'accesso
    email      TEXT    NOT NULL DEFAULT '',
    nuovo      INTEGER NOT NULL DEFAULT 0,  -- 1 = registrazione di un account nuovo
    esito      TEXT    NOT NULL,            -- approvato | rifiutato | automatico
    deciso_da  INTEGER                      -- admin che ha deciso (vuoto = da console)
);
CREATE TABLE IF NOT EXISTS articoli (
    id      INTEGER PRIMARY KEY,
    codice  TEXT    UNIQUE,
    nome    TEXT    NOT NULL,
    emoji   TEXT    NOT NULL DEFAULT '',
    soglia  INTEGER NOT NULL DEFAULT 0,          -- sotto (o uguale) compare l'avviso di comprarne
    attivo  INTEGER NOT NULL DEFAULT 1,
    ordine  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ricette (
    prodotto_id INTEGER NOT NULL REFERENCES prodotti(id),
    articolo_id INTEGER NOT NULL REFERENCES articoli(id),
    qta         INTEGER NOT NULL,                 -- pezzi scalati per ogni prodotto preso
    PRIMARY KEY (prodotto_id, articolo_id)
);
-- Registro del magazzino: la giacenza è la somma delle righe (come i saldi con i movimenti)
CREATE TABLE IF NOT EXISTS magazzino (
    id           INTEGER PRIMARY KEY,
    ts           TEXT    NOT NULL,
    articolo_id  INTEGER NOT NULL REFERENCES articoli(id),
    qta          INTEGER NOT NULL,                -- con segno: + entra, - esce
    tipo         TEXT    NOT NULL,                -- carico | consumo | inventario
    costo_cent   INTEGER NOT NULL DEFAULT 0,      -- carico: quanto è costata questa quantità
    movimento_id INTEGER REFERENCES movimenti(id),-- consumo: l'acquisto (se annullato non conta)
    richiesta_id INTEGER REFERENCES richieste(id),-- carico: la spesa approvata
    persona_id   INTEGER REFERENCES persone(id),  -- chi l'ha fatto
    nota         TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_magazzino_articolo ON magazzino(articolo_id);
-- Articoli dichiarati in una spesa (diventano un carico quando la spesa è approvata)
CREATE TABLE IF NOT EXISTS richieste_articoli (
    richiesta_id INTEGER NOT NULL REFERENCES richieste(id),
    articolo_id  INTEGER NOT NULL REFERENCES articoli(id),
    qta          INTEGER NOT NULL,
    costo_cent   INTEGER NOT NULL
);
-- Comunicazioni interne scritte da un admin: compaiono in home finché ognuno non spunta «Ho letto»
CREATE TABLE IF NOT EXISTS comunicazioni (
    id        INTEGER PRIMARY KEY,
    ts        TEXT    NOT NULL,
    autore_id INTEGER REFERENCES persone(id),
    testo     TEXT    NOT NULL,
    attiva    INTEGER NOT NULL DEFAULT 1           -- 0 = ritirata dall'admin: non compare più
);
CREATE TABLE IF NOT EXISTS comunicazioni_lette (
    comunicazione_id INTEGER NOT NULL REFERENCES comunicazioni(id),
    persona_id       INTEGER NOT NULL REFERENCES persone(id),
    ts               TEXT    NOT NULL,
    PRIMARY KEY (comunicazione_id, persona_id)
);
CREATE TABLE IF NOT EXISTS manutenzioni_fatte (
    id              INTEGER PRIMARY KEY,
    manutenzione_id INTEGER NOT NULL REFERENCES manutenzioni(id),
    ts              TEXT    NOT NULL,
    persona_id      INTEGER REFERENCES persone(id)
);
"""


def connetti():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def db():
    if "db" not in g:
        g.db = connetti()
    return g.db


@app.teardown_appcontext
def chiudi_db(_exc):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def inizializza_db():
    con = connetti()
    with con:
        con.executescript(SCHEMA)
        # Aggiornamento da una versione precedente (solo caffè)
        colonne = {r["name"] for r in con.execute("PRAGMA table_info(movimenti)")}
        if "prodotto_id" not in colonne:
            con.execute("ALTER TABLE movimenti ADD COLUMN prodotto_id INTEGER REFERENCES prodotti(id)")
        colonne_pr = {r["name"] for r in con.execute("PRAGMA table_info(prodotti)")}
        if "descrizione" not in colonne_pr:      # spiegazione sotto il prodotto, in home
            con.execute("ALTER TABLE prodotti ADD COLUMN descrizione TEXT NOT NULL DEFAULT ''")
        colonne_p = {r["name"] for r in con.execute("PRAGMA table_info(persone)")}
        for col, tipo in (("email", "TEXT NOT NULL DEFAULT ''"),
                          ("avvisi_email", "INTEGER NOT NULL DEFAULT 1"),
                          ("avviso_letto", "TEXT NOT NULL DEFAULT ''"),
                          ("lingua", "TEXT NOT NULL DEFAULT ''"),
                          # accesso approvato dall'admin (chi era già attivo resta approvato)
                          ("approvato", "INTEGER NOT NULL DEFAULT 1"),
                          ("richiesta_ts", "TEXT NOT NULL DEFAULT ''"),
                          ("nuovo_nome", "TEXT NOT NULL DEFAULT ''"),
                          ("nuovo_cognome", "TEXT NOT NULL DEFAULT ''"),
                          ("nuovo_account", "INTEGER NOT NULL DEFAULT 0"),
                          # come vuole essere pagato (facoltativi, visibili nella sua scheda)
                          ("paypal", "TEXT NOT NULL DEFAULT ''"),
                          ("iban", "TEXT NOT NULL DEFAULT ''"),
                          # ultima voce di novita.py che ha spuntato «Ho letto»
                          ("novita_lette", "TEXT NOT NULL DEFAULT ''")):
            if col not in colonne_p:
                con.execute(f"ALTER TABLE persone ADD COLUMN {col} {tipo}")
        # Le prime email partiranno dal prossimo lunedì, non appena si installa l'app
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('avviso_settimana', ?)",
                    (settimana_corrente(),))
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('avviso_esito', '')")
        # Backup per email agli amministratori: il primo parte subito, poi ogni lunedì
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('backup_settimana', '')")
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('backup_esito', '')")
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('limite_debito_cent', '0')")
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('limite_modo', 'avvisa')")
        # Promemoria di manutenzione di esempio (una volta sola; l'admin li modifica)
        if con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('manutenzioni_esempio', '1')").rowcount:
            for nome, giorni in MANUTENZIONI_ESEMPIO:
                con.execute("INSERT INTO manutenzioni (nome, ogni_giorni, ultima_ts) VALUES (?,?,?)",
                            (nome, giorni, adesso()))
        # Il conto comune «Conto Caffè» si chiama ora «Macchinetta del caffè» (una volta sola:
        # dopo l'admin può rinominarlo come vuole)
        if con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('rinomina_conto_caffe', '1')").rowcount:
            con.execute("UPDATE persone SET nome='Macchinetta del caffè' WHERE nome='Conto Caffè' AND speciale=1")
        # Prodotti di partenza (una volta sola)
        for i, pr in enumerate(PRODOTTI_DEFAULT):
            if con.execute("SELECT 1 FROM prodotti WHERE codice=?", (pr["codice"],)).fetchone():
                continue
            prezzo = pr["prezzo"]
            if pr["codice"] == "caffe":
                vecchio = con.execute("SELECT valore FROM impostazioni WHERE chiave='prezzo_cent'").fetchone()
                prezzo = int(vecchio["valore"]) if vecchio else prezzo
            addebito = None
            if pr["conto"]:
                r = con.execute("SELECT id FROM persone WHERE nome=? AND speciale=1", (pr["conto"],)).fetchone()
                addebito = r["id"] if r else con.execute(
                    "INSERT INTO persone (nome, cognome, speciale, creato) VALUES (?, '', 1, ?)",
                    (pr["conto"], adesso())).lastrowid
            con.execute("INSERT INTO prodotti (codice, nome, emoji, prezzo_cent, addebito_id, ordine)"
                        " VALUES (?,?,?,?,?,?)", (pr["codice"], pr["nome"], pr["emoji"], prezzo,
                                                  addebito, i))
        # Spiegazioni di partenza sotto i prodotti che si sbagliano più spesso (una volta sola)
        if con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('descrizioni_iniziali', '1')").rowcount:
            for codice, testo in DESCRIZIONI_DEFAULT.items():
                con.execute("UPDATE prodotti SET descrizione=? WHERE codice=? AND descrizione=''", (testo, codice))
        # Magazzino: articoli di partenza e cosa consuma ogni prodotto (una volta sola)
        for i, ar in enumerate(ARTICOLI_DEFAULT):
            con.execute("INSERT OR IGNORE INTO articoli (codice, nome, emoji, soglia, ordine) VALUES (?,?,?,?,?)",
                        (ar["codice"], ar["nome"], ar["emoji"], ar["soglia"], i))
        if con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('ricette_iniziali', '1')").rowcount:
            for codice_pr, pezzi in RICETTE_DEFAULT.items():
                for codice_ar, qta in pezzi.items():
                    con.execute("INSERT OR IGNORE INTO ricette SELECT p.id, a.id, ? FROM prodotti p, articoli a "
                                "WHERE p.codice=? AND a.codice=?", (qta, codice_pr, codice_ar))
        caffe = con.execute("SELECT id FROM prodotti WHERE codice='caffe'").fetchone()["id"]
        con.execute("UPDATE movimenti SET tipo='acquisto', prodotto_id=? WHERE tipo='caffe'", (caffe,))
    con.close()


# --------------------------------------------------------------------------
# Utilità
# --------------------------------------------------------------------------
def adesso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def da_iso(s):
    return datetime.fromisoformat(s)


def euro(cent, segno=True):
    """1234 -> '+12,34 €'  |  -50 -> '−0,50 €'"""
    cent = int(cent or 0)
    s = f"{abs(cent) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if not segno or cent == 0:
        return f"{'−' if cent < 0 else ''}{s} €"
    return f"{'+' if cent > 0 else '−'}{s} €"


def leggi_euro(testo, consenti_negativo=False, consenti_zero=False):
    """'5' / '5,50' / '5.5' / '-3,20' -> centesimi (int). None se non valido (anche 0, salvo consenti_zero)."""
    if testo is None:
        return None
    t = testo.strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not t:
        return None
    try:
        valore = round(float(t) * 100)
    except ValueError:
        return None
    if (valore == 0 and not consenti_zero) or abs(valore) > MAX_IMPORTO_CENT:
        return None
    if valore < 0 and not consenti_negativo:
        return None
    return valore


def ora_locale(iso):
    dt = da_iso(iso).astimezone(TZ)
    oggi = datetime.now(TZ)
    if dt.date() == oggi.date():
        return _("oggi {ora}", ora=f"{dt:%H:%M}")
    if dt.year == oggi.year:
        return f"{dt:%d/%m %H:%M}"
    return f"{dt:%d/%m/%Y %H:%M}"


def lingua_corrente():
    return g.get("lingua", "it") if has_app_context() else "it"


def _(chiave, /, **valori):
    """Traduce un testo italiano nella lingua di chi sta usando l'app."""
    return traduci(chiave, lingua_corrente(), **valori)


def settimana_corrente():
    """Settimana dell'avviso, es. '2026-W46'. Cambia ogni lunedì all'ORA_AVVISO."""
    rif = datetime.now(TZ) - timedelta(hours=ORA_AVVISO)
    anno, sett, _ = rif.isocalendar()
    return f"{anno}-W{sett:02d}"


def email_valida(e):
    e = (e or "").strip()
    return e if (len(e) <= 120 and "@" in e and "." in e.split("@")[-1] and " " not in e) else ""


def iban_valido(testo):
    """IBAN senza spazi e in maiuscolo se il codice di controllo torna, altrimenti ''."""
    t = re.sub(r"[\s-]", "", testo or "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", t):
        return ""
    numero = "".join(str(int(c, 36)) for c in t[4:] + t[:4])
    return t if int(numero) % 97 == 1 else ""


def iban_leggibile(iban):
    return " ".join(iban[i:i + 4] for i in range(0, len(iban or ""), 4))


def paypal_valido(testo):
    """Nome di paypal.me (anche incollato come link) oppure email del conto PayPal; '' se non valido."""
    t = re.sub(r"^(https?://)?(www\.)?paypal\.me/", "", (testo or "").strip(), flags=re.I).strip("/@ ")
    if "@" in t:
        return email_valida(t)
    return t if re.fullmatch(r"[A-Za-z0-9]{1,20}", t) else ""


def paypal_link(paypal):
    """Link paypal.me per un nome utente; per un'email non c'è un link diretto."""
    return "" if not paypal or "@" in paypal else f"https://paypal.me/{paypal}"


def nome_completo(p):
    if p is None:
        return "?"
    return f"{p['nome']} {p['cognome']}".strip()


app.jinja_env.filters["iban"] = iban_leggibile
app.jinja_env.filters["paypal_link"] = paypal_link
app.jinja_env.filters["euro"] = euro
app.jinja_env.filters["ora"] = ora_locale
app.jinja_env.filters["nome"] = nome_completo


def impostazione(chiave, predefinito=""):
    r = db().execute("SELECT valore FROM impostazioni WHERE chiave=?", (chiave,)).fetchone()
    return r["valore"] if r else predefinito


def imposta(chiave, valore):
    db().execute("INSERT INTO impostazioni VALUES (?, ?) ON CONFLICT(chiave) DO UPDATE SET valore=?",
                 (chiave, str(valore), str(valore)))


def limite_debito():
    """(limite in centesimi, modo) – limite 0 = nessun limite; modo 'avvisa' oppure 'blocca'."""
    try:
        cent = int(impostazione("limite_debito_cent", "0"))
    except ValueError:
        cent = 0
    modo = impostazione("limite_modo", "avvisa")
    return cent, modo if modo in ("avvisa", "blocca") else "avvisa"


def prodotti(solo_attivi=True):
    filtro = "WHERE attivo=1" if solo_attivi else ""
    return db().execute(f"SELECT * FROM prodotti {filtro} ORDER BY ordine, id").fetchall()


def prodotto(prid):
    if "_prodotti" not in g:
        g._prodotti = {p["id"]: p for p in prodotti(solo_attivi=False)}
    return g._prodotti.get(prid)


def conteggi_prodotti():
    """{persona_id: {prodotto_id: quantità}} sugli acquisti non annullati."""
    out = {}
    for r in db().execute("SELECT persona_id, prodotto_id, SUM(qta) AS n FROM movimenti "
                          "WHERE tipo='acquisto' AND annullato=0 GROUP BY persona_id, prodotto_id"):
        out.setdefault(r["persona_id"], {})[r["prodotto_id"]] = r["n"]
    return out


def articoli(solo_attivi=True):
    """Articoli del magazzino con la giacenza (somma del registro, senza i consumi annullati)
    e «contato»: se un admin ha già inserito almeno una volta la quantità vera."""
    filtro = "WHERE a.attivo=1" if solo_attivi else ""
    return db().execute(f"""
        SELECT a.*,
               COALESCE((SELECT SUM(g.qta) FROM magazzino g LEFT JOIN movimenti m ON m.id = g.movimento_id
                         WHERE g.articolo_id = a.id AND COALESCE(m.annullato, 0) = 0), 0) AS giacenza,
               EXISTS (SELECT 1 FROM magazzino g WHERE g.articolo_id = a.id AND g.tipo = 'inventario') AS contato
        FROM articoli a {filtro} ORDER BY a.ordine, a.id""").fetchall()


def articoli_da_comprare():
    """Articoli già contati almeno una volta che sono arrivati alla soglia (o sotto)."""
    return [a for a in articoli() if a["contato"] and a["giacenza"] <= a["soglia"]]


def nome_articolo(a):
    return _(a["nome"])


def scala_magazzino(movimento_id, prodotto_id, qta, chi, con=None):
    """Un acquisto consuma la merce della ricetta del prodotto. Se l'acquisto viene annullato,
    le righe restano ma non contano più (la giacenza le esclude)."""
    con = con or db()
    for r in con.execute("SELECT articolo_id, qta FROM ricette WHERE prodotto_id=?", (prodotto_id,)).fetchall():
        con.execute("INSERT INTO magazzino (ts, articolo_id, qta, tipo, movimento_id, persona_id) "
                    "VALUES (?,?,?, 'consumo', ?, ?)", (adesso(), r["articolo_id"], -r["qta"] * qta,
                                                        movimento_id, chi))


def carica_magazzino(richiesta_id, chi, con=None):
    """Spesa approvata: la merce dichiarata entra in magazzino, con il suo costo."""
    con = con or db()
    for r in con.execute("SELECT * FROM richieste_articoli WHERE richiesta_id=?", (richiesta_id,)).fetchall():
        con.execute("INSERT INTO magazzino (ts, articolo_id, qta, tipo, costo_cent, richiesta_id, persona_id) "
                    "VALUES (?,?,?, 'carico', ?, ?, ?)", (adesso(), r["articolo_id"], r["qta"],
                                                          r["costo_cent"], richiesta_id, chi))


def persona(pid):
    return db().execute("SELECT * FROM persone WHERE id=?", (pid,)).fetchone()


def saldo(pid):
    r = db().execute(
        "SELECT COALESCE(SUM(importo_cent),0) AS s FROM movimenti "
        "WHERE persona_id=? AND annullato=0", (pid,)).fetchone()
    return r["s"]


def elenco_saldi(includi_inattivi=False):
    filtro = "" if includi_inattivi else "WHERE p.attivo=1 OR COALESCE(m.s,0)<>0"
    return db().execute(f"""
        SELECT p.*, COALESCE(m.s,0) AS saldo, m.ultimo AS ultimo
        FROM persone p
        LEFT JOIN (SELECT persona_id,
                          SUM(importo_cent) AS s,
                          MAX(ts) AS ultimo
                   FROM movimenti WHERE annullato=0 GROUP BY persona_id) m
               ON m.persona_id = p.id
        {filtro}
        ORDER BY p.speciale, LOWER(p.nome), LOWER(p.cognome)
    """).fetchall()


def registra(persona_id, tipo, importo_cent, *, qta=0, prodotto_id=None, controparte_id=None,
             gruppo=None, nota="", creato_da=None, con=None):
    con = con or db()
    cur = con.execute(
        "INSERT INTO movimenti (ts, persona_id, tipo, importo_cent, qta, prodotto_id,"
        " controparte_id, gruppo, nota, creato_da) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (adesso(), persona_id, tipo, importo_cent, qta, prodotto_id, controparte_id, gruppo,
         nota, creato_da))
    return cur.lastrowid


def nome_prodotto(pr):
    return _(pr["nome"])          # i nomi di serie hanno la traduzione, quelli nuovi restano come sono


def etichetta_prodotto(pr, qta):
    return f"{pr['emoji']} {nome_prodotto(pr)} × {qta}".strip()


def _dopo(testo, prefisso):
    return testo[len(prefisso):] if testo.startswith(prefisso) else testo


def descrizione(m):
    """Testo di un movimento, nella lingua di chi lo guarda."""
    nota = m["nota"] or ""
    if m["tipo"] == "acquisto":
        pr = prodotto(m["prodotto_id"])
        testo = etichetta_prodotto(pr, m["qta"]) if pr else f"× {m['qta']}"
        if nota.startswith("presa da "):
            nota = _("presa da {nome}", nome=_dopo(nota, "presa da "))
        return f"{testo} – {nota}" if nota else testo
    if m["tipo"] == "iniziale":
        return _("Saldo iniziale ({origine})", origine=_(nota)) if nota else _("Saldo iniziale")
    if m["tipo"] == "trasferimento" and m["controparte_id"]:
        altro = nome_completo(persona(m["controparte_id"]))
        extra = nota.split(" – ", 1)[1] if " – " in nota else ""
        mio = m["persona_id"] == m["creato_da"]
        if m["importo_cent"] > 0:
            testo = (_("Soldi dati a {nome}", nome=altro) if mio
                     else _("{nome} si è preso il tuo debito", nome=altro))
        else:
            testo = (_("Mi sono preso il debito di {nome}", nome=altro) if mio
                     else _("Soldi ricevuti da {nome}", nome=altro))
        return f"{testo} – {extra}" if extra else testo
    if m["tipo"] == "spesa":
        return _("Spesa per il gruppo: {cosa}", cosa=_dopo(nota, "Spesa per il gruppo: "))
    if m["tipo"] == "rettifica":
        return _("Rettifica: {motivo}", motivo=_dopo(nota, "Rettifica: "))
    return nota or m["tipo"].capitalize()


app.jinja_env.filters["descrizione"] = descrizione


def puo_annullare(m, utente):
    if m["annullato"] or m["tipo"] == "iniziale":
        return False
    if utente["admin"]:
        return True
    # spese e pagamenti passano già da un'approvazione: da soli si annullano solo gli acquisti
    if m["creato_da"] != utente["id"] or m["tipo"] != "acquisto":
        return False
    return datetime.now(timezone.utc) - da_iso(m["ts"]) <= FINESTRA_ANNULLA


inizializza_db()


# --------------------------------------------------------------------------
# Sessione, accesso e protezione CSRF
# --------------------------------------------------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def prima_di_ogni_richiesta():
    g.lingua = session.get("lingua") or request.accept_languages.best_match(LINGUE, default="it")
    if request.method == "POST":
        token = request.form.get("_csrf", "")
        if not token or not secrets.compare_digest(token, session.get("_csrf", "")):
            abort(400, "Sessione scaduta")
    g.utente = None
    g.in_attesa = None
    uid = session.get("uid")
    if uid:
        p = persona(uid)
        if p and p["attivo"] and not p["speciale"] and p["pin_hash"] \
                and session.get("ver") == p["versione_sessione"]:
            if p["approvato"]:
                g.utente = p
            else:
                g.in_attesa = p          # PIN scelto, ma l'admin non ha ancora dato l'ok
            if p["lingua"] in LINGUE and not session.get("lingua"):
                g.lingua = session["lingua"] = p["lingua"]
        else:
            session.pop("uid", None)


@app.get("/lingua/<codice>")
def cambia_lingua(codice):
    if codice in LINGUE:
        session["lingua"] = codice
        if g.utente:
            with db():
                db().execute("UPDATE persone SET lingua=? WHERE id=?", (codice, g.utente["id"]))
    destinazione = request.referrer or ""
    if not destinazione.startswith(request.host_url):
        destinazione = url_for("home")
    return redirect(destinazione)


@app.context_processor
def variabili_template():
    return {"utente": g.get("utente"), "nome_app": NOME_APP, "lingua": lingua_corrente(),
            "versione_css": VERSIONE_CSS}


# Cambia a ogni aggiornamento del CSS, così i telefoni non usano la copia vecchia in cache
try:
    VERSIONE_CSS = int(os.path.getmtime(os.path.join(app.root_path, "static", "stile.css")))
except OSError:
    VERSIONE_CSS = 0


app.jinja_env.globals["_"] = _


def login_richiesto(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not g.utente:
            return redirect(url_for("attesa" if g.get("in_attesa") else "accedi"))
        return f(*a, **kw)
    return wrapper


def admin_richiesto(f):
    @wraps(f)
    @login_richiesto
    def wrapper(*a, **kw):
        if not g.utente["admin"]:
            abort(403)
        return f(*a, **kw)
    return wrapper


def apri_sessione(p):
    lingua = session.get("lingua")
    session.clear()
    if lingua:
        session["lingua"] = lingua
    session.permanent = True
    session["uid"] = p["id"]
    session["ver"] = p["versione_sessione"]


def pin_valido(pin):
    return pin.isdigit() and 4 <= len(pin) <= 8


def persone_con_accesso():
    return db().execute(
        "SELECT * FROM persone WHERE attivo=1 AND speciale=0 "
        "ORDER BY LOWER(nome), LOWER(cognome)").fetchall()


# --------------------------------------------------------------------------
# Accesso
# --------------------------------------------------------------------------
@app.route("/accedi", methods=["GET", "POST"])
def accedi():
    if g.utente:
        return redirect(url_for("home"))
    if g.in_attesa:
        return redirect(url_for("attesa"))
    if request.method == "POST":
        p = persona(request.form.get("persona_id", type=int) or 0)
        pin = request.form.get("pin", "").strip()
        if not p or not p["attivo"] or p["speciale"]:
            flash(_("Scegli il tuo nome dall'elenco."), "errore")
            return redirect(url_for("accedi"))
        if not p["pin_hash"]:
            return render_template("primo_accesso.html", p=p)
        if p["bloccato_fino"] and da_iso(p["bloccato_fino"]) > datetime.now(timezone.utc):
            flash(_("Troppi tentativi sbagliati: riprova tra qualche minuto."), "errore")
            return redirect(url_for("accedi"))
        if check_password_hash(p["pin_hash"], pin):
            with db():
                db().execute("UPDATE persone SET tentativi=0, bloccato_fino=NULL WHERE id=?",
                             (p["id"],))
            apri_sessione(p)
            return redirect(url_for("home" if p["approvato"] else "attesa"))
        tentativi = p["tentativi"] + 1
        blocco = None
        if tentativi >= MAX_TENTATIVI_PIN:
            blocco = (datetime.now(timezone.utc) + DURATA_BLOCCO).isoformat(timespec="seconds")
            tentativi = 0
        with db():
            db().execute("UPDATE persone SET tentativi=?, bloccato_fino=? WHERE id=?",
                         (tentativi, blocco, p["id"]))
        flash(_("PIN sbagliato."), "errore")
        return redirect(url_for("accedi", p=p["id"]))
    return render_template("accedi.html", persone=persone_con_accesso(),
                           selezionato=request.args.get("p", type=int))


@app.post("/primo-accesso")
def primo_accesso():
    p = persona(request.form.get("persona_id", type=int) or 0)
    if not p or p["pin_hash"] or p["speciale"] or not p["attivo"]:
        flash(_("Questo account è già stato attivato. Se non sei stato tu, avvisa l'amministratore."),
              "errore")
        return redirect(url_for("accedi"))
    nome = request.form.get("nome", "").strip()
    cognome = request.form.get("cognome", "").strip()
    pin, pin2 = request.form.get("pin", "").strip(), request.form.get("pin2", "").strip()
    errore = None
    if not nome or not cognome:
        errore = "Inserisci nome e cognome."
    elif not pin_valido(pin):
        errore = "Il PIN deve avere da 4 a 8 cifre."
    elif pin != pin2:
        errore = "I due PIN non coincidono."
    elif request.form.get("email", "").strip() and not email_valida(request.form.get("email")):
        errore = "Indirizzo email non valido (puoi anche lasciarlo vuoto)."
    if errore:
        flash(_(errore), "errore")
        return render_template("primo_accesso.html", p=p, nome=nome, cognome=cognome,
                               email=request.form.get("email", ""))
    email = email_valida(request.form.get("email"))
    with db():
        if p["admin"]:          # gli amministratori non devono aspettare
            db().execute("UPDATE persone SET nome=?, cognome=?, pin_hash=?, email=?, approvato=1 "
                         "WHERE id=?", (nome, cognome, generate_password_hash(pin), email, p["id"]))
            scrivi_registro_accesso(persona(p["id"]), "automatico", p["id"])
        else:                   # il nome nuovo diventa effettivo solo quando l'admin approva
            db().execute("UPDATE persone SET pin_hash=?, email=?, approvato=0, richiesta_ts=?, "
                         "nuovo_nome=?, nuovo_cognome=?, nuovo_account=0 WHERE id=?",
                         (generate_password_hash(pin), email, adesso(), nome, cognome, p["id"]))
    apri_sessione(persona(p["id"]))
    if p["admin"]:
        flash(_("Account attivato! Da ora questo telefono si ricorda di te."), "ok")
        return redirect(url_for("home"))
    return redirect(url_for("attesa"))


@app.get("/attesa")
def attesa():
    if g.utente:
        flash(_("Il tuo accesso è stato approvato: benvenuto!"), "ok")
        return redirect(url_for("home"))
    if not g.in_attesa:
        return redirect(url_for("accedi"))
    return render_template("attesa.html", p=g.in_attesa)


@app.route("/registrati", methods=["GET", "POST"])
def registrati():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cognome = request.form.get("cognome", "").strip()
        pin, pin2 = request.form.get("pin", "").strip(), request.form.get("pin2", "").strip()
        errore = None
        if not nome or not cognome:
            errore = "Inserisci nome e cognome."
        elif not pin_valido(pin):
            errore = "Il PIN deve avere da 4 a 8 cifre."
        elif pin != pin2:
            errore = "I due PIN non coincidono."
        elif request.form.get("email", "").strip() and not email_valida(request.form.get("email")):
            errore = "Indirizzo email non valido (puoi anche lasciarlo vuoto)."
        elif db().execute("SELECT 1 FROM persone WHERE LOWER(nome)=LOWER(?) AND "
                          "LOWER(cognome)=LOWER(?)", (nome, cognome)).fetchone():
            errore = "Esiste già una persona con questo nome: cercala nell'elenco della pagina di accesso."
        if errore:
            flash(_(errore), "errore")
            return render_template("registrati.html", nome=nome, cognome=cognome,
                                   email=request.form.get("email", ""))
        with db():
            cur = db().execute(
                "INSERT INTO persone (nome, cognome, pin_hash, email, creato, approvato, "
                "richiesta_ts, nuovo_account) VALUES (?,?,?,?,?,0,?,1)",
                (nome, cognome, generate_password_hash(pin),
                 email_valida(request.form.get("email")), adesso(), adesso()))
        apri_sessione(persona(cur.lastrowid))
        return redirect(url_for("attesa"))
    return render_template("registrati.html")


@app.post("/esci")
def esci():
    lingua = session.get("lingua")
    session.clear()
    if lingua:
        session["lingua"] = lingua
    flash(_("Sei uscito. Per rientrare scegli il tuo nome e inserisci il PIN."), "ok")
    return redirect(url_for("accedi"))


# --------------------------------------------------------------------------
# Pagina principale: segna caffè
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Novità degli aggiornamenti e comunicazioni interne (notifiche in home con «Ho letto»)
# --------------------------------------------------------------------------
def novita_da_leggere(u):
    """Voci di novita.py non ancora spuntate, nella lingua di chi legge. Chi ha creato
    l'account dopo un aggiornamento non vede quelle voci: per lui non sono novità."""
    lingua = lingua_corrente()
    return [{"id": n["id"], "punti": n.get(lingua) or n["it"]} for n in NOVITA
            if n["id"] > (u["novita_lette"] or "") and n["id"] >= (u["creato"] or "")[:10]]


def comunicazioni_da_leggere(uid):
    return db().execute("""
        SELECT c.*, p.nome, p.cognome FROM comunicazioni c LEFT JOIN persone p ON p.id = c.autore_id
        WHERE c.attiva = 1 AND NOT EXISTS (SELECT 1 FROM comunicazioni_lette l
                                           WHERE l.comunicazione_id = c.id AND l.persona_id = ?)
        ORDER BY c.id DESC""", (uid,)).fetchall()


@app.post("/novita/lette")
@login_richiesto
def novita_lette():
    if NOVITA:
        with db():
            db().execute("UPDATE persone SET novita_lette=? WHERE id=?", (NOVITA[0]["id"], g.utente["id"]))
    return redirect(url_for("home"))


@app.post("/comunicazione/<int:cid>/letta")
@login_richiesto
def comunicazione_letta(cid):
    if db().execute("SELECT 1 FROM comunicazioni WHERE id=?", (cid,)).fetchone():
        with db():
            db().execute("INSERT OR IGNORE INTO comunicazioni_lette VALUES (?,?,?)", (cid, g.utente["id"], adesso()))
    return redirect(url_for("home"))


@app.get("/")
@login_richiesto
def home():
    u = g.utente
    ultimi = db().execute(
        "SELECT * FROM movimenti WHERE persona_id=? ORDER BY id DESC LIMIT 6",
        (u["id"],)).fetchall()
    creatori = {m["creato_da"] for m in ultimi if m["creato_da"]}
    nomi = {c: nome_completo(persona(c)) for c in creatori}
    mio_saldo = saldo(u["id"])
    limite, modo = limite_debito()
    oltre_limite = bool(limite) and mio_saldo < -limite
    avviso = None
    if mio_saldo < 0 and (oltre_limite or u["avviso_letto"] != settimana_corrente()):
        avviso = {"cassa": conto_cassa(), "creditori": creditori(db(), 3),
                  "importo": f"{-mio_saldo / 100:.2f}".replace(".", ","), "oltre_limite": oltre_limite}
    manutenzioni = [m for m in manutenzioni_con_stato() if m["da_fare"]] if u["admin"] else []
    # merce sotto la soglia: lo vedono gli admin e chi è in debito (comprandola rientra)
    da_comprare = articoli_da_comprare() if u["admin"] or mio_saldo < 0 else []
    return render_template("home.html", saldo=mio_saldo, ultimi=ultimi, nomi=nomi, avviso=avviso,
                           manutenzioni=manutenzioni, limite=limite, limite_modo=modo, da_comprare=da_comprare,
                           novita=novita_da_leggere(u), comunicazioni=comunicazioni_da_leggere(u["id"]),
                           da_fare=conta_da_fare(u), mie_in_attesa=mie_richieste_in_attesa(u["id"]),
                           prodotti=prodotti(), conti={p["id"]: nome_completo(p)
                                                       for p in elenco_saldi()},
                           ultimo=ultimo_acquisto_annullabile(u["id"]),
                           nonce=secrets.token_urlsafe(8))


@app.post("/avviso/letto")
@login_richiesto
def avviso_letto():
    with db():
        db().execute("UPDATE persone SET avviso_letto=? WHERE id=?",
                     (settimana_corrente(), g.utente["id"]))
    return redirect(url_for("home"))


def conto_cassa():
    r = db().execute("SELECT id FROM persone WHERE speciale=1 AND attivo=1 AND LOWER(nome)='cassa'"
                     ).fetchone()
    return r["id"] if r else None


def manutenzioni_con_stato(solo_attive=True):
    """Ogni manutenzione con: giorni passati, data di scadenza, se è da fare."""
    filtro = "WHERE m.attivo=1" if solo_attive else ""
    righe = db().execute(f"""SELECT m.*, p.nome AS da_nome, p.cognome AS da_cognome
                             FROM manutenzioni m LEFT JOIN persone p ON p.id = m.ultima_da
                             {filtro} ORDER BY m.attivo DESC, m.nome""").fetchall()
    oggi = datetime.now(TZ).date()
    out = []
    for r in righe:
        ultima = da_iso(r["ultima_ts"]).astimezone(TZ).date()
        scadenza = ultima + timedelta(days=r["ogni_giorni"])
        out.append({**dict(r), "giorni_fa": (oggi - ultima).days, "ultima_data": ultima,
                    "scadenza": scadenza, "da_fare": oggi >= scadenza,
                    "tra_giorni": (scadenza - oggi).days,
                    "da": f"{r['da_nome'] or ''} {r['da_cognome'] or ''}".strip()})
    return out


@app.post("/manutenzione/<int:mid>/fatta")
@admin_richiesto
def manutenzione_fatta(mid):
    m = db().execute("SELECT * FROM manutenzioni WHERE id=?", (mid,)).fetchone() or abort(404)
    with db():
        db().execute("UPDATE manutenzioni SET ultima_ts=?, ultima_da=? WHERE id=?",
                     (adesso(), g.utente["id"], mid))
        db().execute("INSERT INTO manutenzioni_fatte (manutenzione_id, ts, persona_id) VALUES (?,?,?)",
                     (mid, adesso(), g.utente["id"]))
    flash(_("Segnata come fatta: {nome}. Il prossimo promemoria tra {giorni} giorni.",
            nome=m["nome"], giorni=m["ogni_giorni"]), "ok")
    return redirect(request.referrer or url_for("home"))


def ultimo_acquisto_annullabile(uid):
    """L'ultimo acquisto registrato da me negli ultimi minuti, riassunto in una riga."""
    m = db().execute("SELECT * FROM movimenti WHERE creato_da=? AND tipo='acquisto' "
                     "ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    if not m or not puo_annullare(m, {"admin": 0, "id": uid}):
        return None
    righe = db().execute("SELECT * FROM movimenti WHERE gruppo=? ORDER BY id",
                         (m["gruppo"],)).fetchall() if m["gruppo"] else [m]
    testo = ", ".join(etichetta_prodotto(prodotto(r["prodotto_id"]), r["qta"]) for r in righe)
    return {"id": m["id"], "testo": testo, "ts": m["ts"]}


def nonce_gia_usato(nonce):
    """Evita doppie registrazioni (doppio tocco, invio ripetuto del modulo)."""
    usati = session.get("nonce", [])
    if not nonce or nonce in usati:
        return True
    session["nonce"] = (usati + [nonce])[-15:]
    return False


@app.post("/acquista")
@login_richiesto
def acquista():
    u = g.utente
    scelte = []
    for pr in prodotti():
        q = request.form.get(f"q{pr['id']}", type=int) or 0
        if not 0 <= q <= MAX_QTA_PER_VOLTA:
            flash(_("Puoi segnare al massimo {n} pezzi per prodotto.", n=MAX_QTA_PER_VOLTA), "errore")
            return redirect(url_for("home"))
        if q:
            scelte.append((pr, q))
    if not scelte:
        flash(_("Scegli almeno un prodotto con il +."), "errore")
        return redirect(url_for("home"))
    limite, modo = limite_debito()
    a_mio_carico = sum(q * pr["prezzo_cent"] for pr, q in scelte if not pr["addebito_id"])
    if limite and a_mio_carico and saldo(u["id"]) - a_mio_carico < -limite:
        if modo == "blocca":
            flash(_("Hai raggiunto il limite di debito di {limite}: salda il debito prima di prendere altro.",
                    limite=euro(limite, segno=False)), "errore")
            return redirect(url_for("home"))
        if request.form.get("oltre_limite") != "1":
            flash(_("Sei oltre il limite di debito di {limite}: spunta la casella per confermare l'acquisto.",
                    limite=euro(limite, segno=False)), "errore")
            return redirect(url_for("home"))
    if nonce_gia_usato(request.form.get("nonce")):
        return redirect(url_for("home"))
    gruppo = uuid.uuid4().hex
    a_carico_di_altri = []
    with db():
        for pr, q in scelte:
            chi = pr["addebito_id"] or u["id"]
            nota = f"presa da {nome_completo(u)}" if chi != u["id"] else ""
            mid = registra(chi, "acquisto", -q * pr["prezzo_cent"], qta=q, prodotto_id=pr["id"],
                           gruppo=gruppo, nota=nota, creato_da=u["id"])
            scala_magazzino(mid, pr["id"], q, u["id"])
            if chi != u["id"]:
                a_carico_di_altri.append(_("{cosa} sul conto {conto}", cosa=nome_prodotto(pr),
                                           conto=nome_completo(persona(chi))))
    testo = ", ".join(etichetta_prodotto(pr, q) for pr, q in scelte)
    extra = f" ({'; '.join(a_carico_di_altri)})" if a_carico_di_altri else ""
    flash(_("Segnato: {cosa}{extra}. Il tuo saldo: {saldo}", cosa=testo, extra=extra,
            saldo=euro(saldo(u['id']))), "ok")
    if any(pr["codice"] == "caffe" for pr, _q in scelte):
        flash("🧹 " + _(TESTO_PULIZIA), "pulizia")
    return redirect(url_for("home"))


@app.post("/annulla/<int:mid>")
@login_richiesto
def annulla(mid):
    m = db().execute("SELECT * FROM movimenti WHERE id=?", (mid,)).fetchone()
    if not m or not puo_annullare(m, g.utente):
        flash(_("Questo movimento non si può più annullare. Chiedi all'amministratore."), "errore")
        return redirect(request.referrer or url_for("home"))
    with db():
        if m["gruppo"]:
            db().execute("UPDATE movimenti SET annullato=1, annullato_da=?, annullato_ts=? "
                         "WHERE gruppo=?", (g.utente["id"], adesso(), m["gruppo"]))
        else:
            db().execute("UPDATE movimenti SET annullato=1, annullato_da=?, annullato_ts=? "
                         "WHERE id=?", (g.utente["id"], adesso(), mid))
    flash(_("Movimento annullato."), "ok")
    return redirect(request.referrer or url_for("home"))


# --------------------------------------------------------------------------
# Saldi, movimenti, pagamenti, spese
# --------------------------------------------------------------------------
@app.get("/saldi")
@login_richiesto
def saldi():
    righe = elenco_saldi()
    persone = [r for r in righe if not r["speciale"]]
    debiti = sum(r["saldo"] for r in persone if r["saldo"] < 0)
    crediti = sum(r["saldo"] for r in persone if r["saldo"] > 0)
    ordine = request.args.get("ordine", "nome")
    if ordine == "saldo":
        righe = sorted(righe, key=lambda r: (r["speciale"], r["saldo"]))
    return render_template("saldi.html", righe=righe, debiti=debiti, crediti=crediti,
                           ordine=ordine, prodotti=prodotti(solo_attivi=False),
                           conteggi=conteggi_prodotti())


@app.get("/movimenti")
@login_richiesto
def movimenti():
    tutti = request.args.get("tutti") == "1"
    if tutti:
        righe = db().execute("SELECT * FROM movimenti ORDER BY id DESC LIMIT 300").fetchall()
    else:
        righe = db().execute("SELECT * FROM movimenti WHERE persona_id=? ORDER BY id DESC "
                             "LIMIT 300", (g.utente["id"],)).fetchall()
    ids = {r["persona_id"] for r in righe} | {r["creato_da"] for r in righe if r["creato_da"]}
    nomi = {i: nome_completo(persona(i)) for i in ids}
    annullabili = {r["id"] for r in righe if puo_annullare(r, g.utente)}
    return render_template("movimenti.html", righe=righe, nomi=nomi, tutti=tutti,
                           annullabili=annullabili)


@app.route("/paga", methods=["GET", "POST"])
@login_richiesto
def paga():
    u = g.utente
    altri = [p for p in elenco_saldi() if p["id"] != u["id"] and p["attivo"]]
    if request.method == "POST":
        verso = request.form.get("verso")
        altro = persona(request.form.get("controparte", type=int) or 0)
        importo = leggi_euro(request.form.get("importo"))
        nota = request.form.get("nota", "").strip()[:200]
        errore = None
        if verso not in ("dato", "accollo"):
            errore = "Scegli che tipo di operazione vuoi fare."
        elif not altro or altro["id"] == u["id"] or not altro["attivo"]:
            errore = "Scegli la persona."
        elif importo is None:
            errore = "Importo non valido (es. 5 oppure 2,50)."
        if errore:
            flash(_(errore), "errore")
            return render_template("paga.html", altri=altri, form=request.form,
                                   nonce=secrets.token_urlsafe(8))
        if nonce_gia_usato(request.form.get("nonce")):
            return redirect(url_for("movimenti"))
        n_io, n_altro = nome_completo(u), nome_completo(altro)
        extra = f" – {nota}" if nota else ""
        gruppo = uuid.uuid4().hex
        if verso == "dato" and not (u["admin"] and altro["speciale"]):
            # il saldo dell'altro scende: conta solo quando lui (o l'admin, per i conti comuni) conferma.
            # Vale anche se paga un admin: nessuno conferma da solo un proprio pagamento.
            with db():
                db().execute("INSERT INTO richieste (ts, tipo, richiedente_id, controparte_id, "
                             "importo_cent, nota) VALUES (?, 'pagamento', ?, ?, ?, ?)",
                             (adesso(), u["id"], altro["id"], importo, nota))
            if altro["speciale"]:
                flash(_("Pagamento inviato: conterà quando un amministratore confermerà di aver ricevuto i soldi."), "ok")
            else:
                flash(_("Pagamento inviato: conterà quando {nome} confermerà di aver ricevuto i soldi.",
                        nome=n_altro), "ok")
            return redirect(url_for("home"))
        with db():
            if verso == "dato":         # solo un admin che versa a un conto comune: vale subito, ma resta nel registro
                registra_pagamento(u, altro, importo, nota, gruppo)
                db().execute("INSERT INTO richieste (ts, tipo, richiedente_id, controparte_id, importo_cent, "
                             "nota, stato, deciso_da, deciso_ts) VALUES (?, 'pagamento', ?, ?, ?, ?, "
                             "'approvata', ?, ?)", (adesso(), u["id"], altro["id"], importo, nota,
                                                    u["id"], adesso()))
            else:
                registra(u["id"], "trasferimento", -importo, controparte_id=altro["id"],
                         gruppo=gruppo, nota=f"Mi sono preso il debito di {n_altro}{extra}",
                         creato_da=u["id"])
                registra(altro["id"], "trasferimento", importo, controparte_id=u["id"],
                         gruppo=gruppo, nota=f"{n_io} si è preso il tuo debito{extra}",
                         creato_da=u["id"])
        flash(_("Registrato. Il tuo saldo ora è {mio}; quello di {nome} è {suo}.",
                mio=euro(saldo(u['id'])), nome=n_altro, suo=euro(saldo(altro['id']))), "ok")
        return redirect(url_for("home"))
    precompilato = {"verso": request.args.get("verso", "dato"),
                    "importo": request.args.get("importo", ""),
                    "controparte": request.args.get("a", "")}
    return render_template("paga.html", altri=altri, form=precompilato,
                           nonce=secrets.token_urlsafe(8))


@app.route("/profilo", methods=["GET", "POST"])
@login_richiesto
def profilo():
    u = g.utente
    if request.method == "POST":
        testo = request.form.get("email", "").strip()
        email = email_valida(testo)
        testo_paypal = request.form.get("paypal", "").strip()
        paypal = paypal_valido(testo_paypal)
        testo_iban = request.form.get("iban", "").strip()
        iban = iban_valido(testo_iban)
        errore = None
        if testo and not email:
            errore = _("Indirizzo email non valido.")
        elif testo_paypal and not paypal:
            errore = _("PayPal non valido: scrivi il tuo nome di paypal.me (es. mariorossi) oppure l'email del conto PayPal.")
        elif testo_iban and not iban:
            errore = _("IBAN non valido: controlla che sia completo e senza errori di battitura.")
        if errore:
            flash(errore, "errore")
            return render_template("profilo.html", email_attiva=email_configurata(), form=request.form)
        with db():
            db().execute("UPDATE persone SET email=?, avvisi_email=?, paypal=?, iban=? WHERE id=?",
                         (email, 1 if request.form.get("avvisi_email") else 0, paypal, iban, u["id"]))
        flash(_("Profilo aggiornato."), "ok")
        return redirect(url_for("home"))
    return render_template("profilo.html", email_attiva=email_configurata(),
                           form={"email": u["email"], "paypal": u["paypal"], "iban": iban_leggibile(u["iban"]),
                                 "avvisi_email": u["avvisi_email"]})


@app.get("/persona/<int:pid>")
@login_richiesto
def scheda_persona(pid):
    """Scheda pubblica (per chi ha fatto l'accesso): nome, saldo e come vuole essere pagato."""
    p = next((r for r in elenco_saldi(includi_inattivi=True) if r["id"] == pid), None) or abort(404)
    return render_template("persona.html", p=p)


@app.route("/spesa", methods=["GET", "POST"])
@login_richiesto
def spesa():
    def pagina(form):
        return render_template("spesa.html", form=form, articoli=articoli(), nonce=secrets.token_urlsafe(8),
                               evidenzia=request.args.get("articolo", type=int))
    if request.method == "POST":
        righe, nota, importo, errore = leggi_spesa(request.form)
        if errore:
            flash(errore, "errore")
            return pagina(request.form)
        if nonce_gia_usato(request.form.get("nonce")):
            return redirect(url_for("home"))
        # tutte le spese, anche quelle degli admin, aspettano l'approvazione di un admin
        with db():
            rid = db().execute("INSERT INTO richieste (ts, tipo, richiedente_id, importo_cent, nota) "
                               "VALUES (?, 'spesa', ?, ?, ?)",
                               (adesso(), g.utente["id"], importo, nota)).lastrowid
            salva_articoli_spesa(rid, righe)
        if g.utente["admin"] and unico_admin(g.utente):
            flash(_("Spesa inviata. Sei l'unico amministratore: approvala tu in «Richieste»."), "ok")
        elif g.utente["admin"]:
            flash(_("Spesa inviata: l'importo ti verrà accreditato quando un altro amministratore la approva."), "ok")
        else:
            flash(_("Spesa inviata: l'importo ti verrà accreditato quando un amministratore la approva."), "ok")
        return redirect(url_for("home"))
    return pagina({})


MAX_PEZZI_SPESA = 10000


def leggi_spesa(form):
    """Legge il modulo della spesa: per ogni articolo del magazzino pezzi e costo (obbligatori
    entrambi), più «altro» (descrizione e costo). Restituisce (righe, nota, totale, errore)."""
    righe = []
    for a in articoli():
        testo_qta = (form.get(f"qta_{a['id']}") or "").strip()
        testo_costo = (form.get(f"costo_{a['id']}") or "").strip()
        if not testo_qta and not testo_costo:
            continue
        qta = int(testo_qta) if testo_qta.isdigit() else 0
        costo = leggi_euro(testo_costo)
        if not 0 < qta <= MAX_PEZZI_SPESA:
            return [], "", 0, _("Scrivi quanti pezzi di {nome} hai comprato.", nome=nome_articolo(a))
        if costo is None:
            return [], "", 0, _("Scrivi quanto hai speso per {nome} (es. 4,50).", nome=nome_articolo(a))
        righe.append((a, qta, costo))
    altro = (form.get("nota") or "").strip()[:200]
    testo_importo = (form.get("importo") or "").strip()
    costo_altro = leggi_euro(testo_importo) if testo_importo else 0
    if costo_altro is None:
        return [], "", 0, _("Importo non valido (es. 5 oppure 2,50).")
    if costo_altro and not altro:
        return [], "", 0, _("Scrivi cos'altro hai comprato.")
    if altro and not costo_altro:
        return [], "", 0, _("Scrivi quanto hai speso per il resto.")
    totale = sum(costo for _a, _q, costo in righe) + costo_altro
    if not totale:
        return [], "", 0, _("Inserisci l'importo e cosa hai comprato.")
    if totale > MAX_IMPORTO_CENT:
        return [], "", 0, _("Importo non valido (es. 5 oppure 2,50).")
    # descrizione in italiano (come le altre note): «50 cialde, 100 bicchierini, zucchero»
    parti = [f"{qta} {a['nome'].lower()}" for a, qta, _c in righe] + ([altro] if altro else [])
    return righe, ", ".join(parti)[:200], totale, None


def salva_articoli_spesa(rid, righe):
    for a, qta, costo in righe:
        db().execute("INSERT INTO richieste_articoli (richiesta_id, articolo_id, qta, costo_cent) VALUES (?,?,?,?)",
                     (rid, a["id"], qta, costo))


# --------------------------------------------------------------------------
# Richieste da approvare: spese, pagamenti, nuovi accessi
# --------------------------------------------------------------------------
def scrivi_registro_accesso(p, esito, deciso_da, con=None):
    con = con or db()
    richiesto = f"{p['nuovo_nome']} {p['nuovo_cognome']}".strip() or nome_completo(p)
    con.execute("INSERT INTO registro_accessi (ts, persona_id, account, richiesto, email, nuovo, esito, "
                "deciso_da) VALUES (?,?,?,?,?,?,?,?)",
                (adesso(), p["id"], "" if p["nuovo_account"] else nome_completo(p), richiesto,
                 p["email"] or "", p["nuovo_account"], esito, deciso_da))


def registra_pagamento(da, a, importo, nota, gruppo=None):
    """«da» ha dato soldi ad «a»: il saldo di «da» sale, quello di «a» scende."""
    gruppo = gruppo or uuid.uuid4().hex
    extra = f" – {nota}" if nota else ""
    registra(da["id"], "trasferimento", importo, controparte_id=a["id"], gruppo=gruppo,
             nota=f"Soldi dati a {nome_completo(a)}{extra}", creato_da=da["id"])
    registra(a["id"], "trasferimento", -importo, controparte_id=da["id"], gruppo=gruppo,
             nota=f"Soldi ricevuti da {nome_completo(da)}{extra}", creato_da=da["id"])


def richiesta_ferma(r):
    """True se la richiesta aspetta da più di ATTESA_MAX_PAGAMENTO."""
    return datetime.now(timezone.utc) - da_iso(r["ts"]) > ATTESA_MAX_PAGAMENTO


def unico_admin(utente):
    """True se «utente» è l'unico amministratore che può entrare nell'app."""
    return not db().execute("SELECT 1 FROM persone WHERE admin=1 AND attivo=1 AND speciale=0 AND approvato=1 "
                            "AND pin_hash IS NOT NULL AND id<>? LIMIT 1", (utente["id"],)).fetchone()


def puo_decidere(r, utente):
    """Chi può approvare una richiesta.
    Spesa: un admin, ma non la propria (a meno che sia l'unico admin). Pagamento: chi ha ricevuto i soldi; un admin solo se i soldi sono andati
    a un conto comune oppure se la richiesta è ferma da più di 3 giorni. Mai chi ha pagato."""
    if r["stato"] != "attesa":
        return False
    if r["tipo"] != "pagamento":
        if not utente["admin"]:
            return False
        return r["richiedente_id"] != utente["id"] or unico_admin(utente)
    if r["controparte_id"] == utente["id"]:
        return True
    if not utente["admin"] or r["richiedente_id"] == utente["id"]:
        return False
    altro = persona(r["controparte_id"])
    return bool(altro and altro["speciale"]) or richiesta_ferma(r)


def richieste_da_decidere(utente):
    if utente["admin"]:
        righe = db().execute("SELECT * FROM richieste WHERE stato='attesa' ORDER BY id").fetchall()
    else:
        righe = db().execute("SELECT * FROM richieste WHERE stato='attesa' AND tipo='pagamento' "
                             "AND controparte_id=? ORDER BY id", (utente["id"],)).fetchall()
    return [r for r in righe if puo_decidere(r, utente)]


def accessi_in_attesa():
    return db().execute("SELECT * FROM persone WHERE pin_hash IS NOT NULL AND approvato=0 "
                        "AND attivo=1 AND speciale=0 ORDER BY richiesta_ts").fetchall()


def mie_richieste_in_attesa(uid):
    return db().execute("SELECT * FROM richieste WHERE stato='attesa' AND richiedente_id=? "
                        "ORDER BY id DESC", (uid,)).fetchall()


def conta_da_fare(utente):
    n = len(richieste_da_decidere(utente))
    if utente["admin"]:
        n += len(accessi_in_attesa())
    return n


def descrivi_richiesta(r):
    chi = nome_completo(persona(r["richiedente_id"]))
    if r["tipo"] == "spesa":
        return _("{nome} ha comprato per il gruppo: {cosa}", nome=chi, cosa=r["nota"])
    testo = _("{nome} dice di aver dato dei soldi a {altro}", nome=chi,
              altro=nome_completo(persona(r["controparte_id"])))
    return f"{testo} – {r['nota']}" if r["nota"] else testo


app.jinja_env.filters["richiesta"] = descrivi_richiesta


@app.get("/richieste")
@login_richiesto
def richieste():
    u = g.utente
    elenco = richieste_da_decidere(u)
    return render_template("richieste.html", da_decidere=elenco,
                           accessi=accessi_in_attesa() if u["admin"] else [],
                           mie=mie_richieste_in_attesa(u["id"]),
                           vecchie={r["id"] for r in elenco if richiesta_ferma(r)},
                           nomi={p["id"]: nome_completo(p) for p in elenco_saldi(includi_inattivi=True)})


@app.post("/richieste/<int:rid>/<azione>")
@login_richiesto
def decidi_richiesta(rid, azione):
    u = g.utente
    r = db().execute("SELECT * FROM richieste WHERE id=?", (rid,)).fetchone() or abort(404)
    if azione == "annulla":
        if r["richiedente_id"] != u["id"] or r["stato"] != "attesa":
            abort(403)
        with db():
            db().execute("UPDATE richieste SET stato='annullata', deciso_da=?, deciso_ts=? WHERE id=?",
                         (u["id"], adesso(), rid))
        flash(_("Richiesta annullata."), "ok")
        return redirect(request.referrer or url_for("home"))
    if azione not in ("approva", "rifiuta") or not puo_decidere(r, u):
        abort(403)
    richiedente = persona(r["richiedente_id"])
    with db():
        db().execute("UPDATE richieste SET stato=?, deciso_da=?, deciso_ts=? WHERE id=? AND stato='attesa'",
                     ("approvata" if azione == "approva" else "rifiutata", u["id"], adesso(), rid))
        if azione == "approva":
            if r["tipo"] == "spesa":
                registra(richiedente["id"], "spesa", r["importo_cent"],
                         nota=f"Spesa per il gruppo: {r['nota']}", creato_da=richiedente["id"])
                carica_magazzino(rid, richiedente["id"])
            else:
                registra_pagamento(richiedente, persona(r["controparte_id"]), r["importo_cent"], r["nota"])
    flash(_("Approvata: {cosa}", cosa=descrivi_richiesta(r)) if azione == "approva"
          else _("Rifiutata: {cosa}", cosa=descrivi_richiesta(r)), "ok")
    return redirect(request.referrer or url_for("richieste"))


@app.post("/admin/accesso/<int:pid>/<azione>")
@admin_richiesto
def admin_accesso(pid, azione):
    p = persona(pid) or abort(404)
    if not p["pin_hash"] or p["approvato"]:
        return redirect(url_for("richieste"))
    if azione not in ("approva", "rifiuta"):
        abort(404)
    with db():
        scrivi_registro_accesso(p, "approvato" if azione == "approva" else "rifiutato", g.utente["id"])
        if azione == "approva":
            db().execute("UPDATE persone SET approvato=1, "
                         "nome = CASE WHEN nuovo_nome<>'' THEN nuovo_nome ELSE nome END, "
                         "cognome = CASE WHEN nuovo_nome<>'' THEN nuovo_cognome ELSE cognome END, "
                         "nuovo_nome='', nuovo_cognome='', nuovo_account=0 WHERE id=?", (pid,))
            flash(_("Accesso approvato: {nome}.", nome=nome_completo(persona(pid))), "ok")
        elif azione == "rifiuta":
            usato = db().execute("SELECT 1 FROM movimenti WHERE persona_id=? OR creato_da=? LIMIT 1",
                                 (pid, pid)).fetchone()
            if p["nuovo_account"] and not usato:
                db().execute("DELETE FROM richieste WHERE richiedente_id=?", (pid,))
                db().execute("DELETE FROM persone WHERE id=?", (pid,))
            else:     # l'account torna "mai entrato": il vero proprietario potrà attivarlo
                db().execute("UPDATE persone SET pin_hash=NULL, email='', approvato=0, nuovo_nome='', "
                             "nuovo_cognome='', versione_sessione=versione_sessione+1 WHERE id=?", (pid,))
            flash(_("Accesso rifiutato: {nome}.", nome=nome_completo(p)), "ok")
    return redirect(request.referrer or url_for("richieste"))


def registro_dati(limite=300):
    accessi = db().execute("SELECT * FROM registro_accessi ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    decise = db().execute("SELECT * FROM richieste WHERE stato<>'attesa' ORDER BY COALESCE(deciso_ts, ts) DESC, "
                          "id DESC LIMIT ?", (limite,)).fetchall()
    nomi = {p["id"]: nome_completo(p) for p in db().execute("SELECT * FROM persone")}
    admin = {p["id"] for p in db().execute("SELECT id FROM persone WHERE admin=1")}
    return accessi, [r for r in decise if r["tipo"] == "spesa"], \
        [r for r in decise if r["tipo"] == "pagamento"], nomi, admin


@app.get("/admin/registro")
@admin_richiesto
def admin_registro():
    accessi, spese, pagamenti, nomi, admin = registro_dati()
    return render_template("registro.html", accessi=accessi, spese=spese, pagamenti=pagamenti,
                           nomi=nomi, admin_ids=admin, sezione=request.args.get("sezione", ""))


@app.get("/come-funziona")
def come_funziona():
    limite, modo = limite_debito()
    return render_template("come_funziona.html", prodotti=prodotti(), limite=limite, limite_modo=modo)


# --------------------------------------------------------------------------
# Statistiche dei consumi: visibili a tutti quelli che hanno fatto l'accesso
# --------------------------------------------------------------------------
PERIODI = ("giorno", "settimana", "mese", "anno")
QUANTI_PERIODI = {"giorno": 14, "settimana": 12, "mese": 12}   # gli anni: dal primo con dati


def consumi(persona_id=None):
    """[(giorno locale, prodotto_id, quantità)] degli acquisti non annullati, di tutti o di un conto.
    Come nel saldo, un prodotto pagato da un conto comune (es. l'acqua macchinetta, pagata dalla
    Macchinetta del caffè) conta su quel conto, non su chi l'ha preso."""
    righe = db().execute("""
        SELECT ts, prodotto_id, qta FROM movimenti
        WHERE tipo = 'acquisto' AND annullato = 0 AND qta > 0 AND (? IS NULL OR persona_id = ?)""",
                         (persona_id, persona_id)).fetchall()
    return [(da_iso(r["ts"]).astimezone(TZ).date(), r["prodotto_id"], r["qta"]) for r in righe]


def inizio_periodo(giorno, periodo):
    """Primo giorno del periodo (giorno, settimana da lunedì, mese, anno) che contiene «giorno»."""
    if periodo == "settimana":
        return giorno - timedelta(days=giorno.weekday())
    if periodo == "mese":
        return giorno.replace(day=1)
    if periodo == "anno":
        return giorno.replace(month=1, day=1)
    return giorno


def periodo_prima(inizio, periodo):
    if periodo == "settimana":
        return inizio - timedelta(days=7)
    if periodo == "mese":
        return (inizio - timedelta(days=1)).replace(day=1)
    if periodo == "anno":
        return inizio.replace(year=inizio.year - 1)
    return inizio - timedelta(days=1)


def etichetta_periodo(inizio, periodo, oggi):
    if periodo == "giorno":
        if inizio == oggi:
            return _("oggi")
        return _("ieri") if inizio == oggi - timedelta(days=1) else f"{inizio:%d/%m}"
    if periodo == "settimana":
        if inizio == inizio_periodo(oggi, "settimana"):
            return _("questa settimana")
        return _("dal {data}", data=f"{inizio:%d/%m}")
    if periodo == "mese":
        return f"{inizio:%m/%Y}"
    return str(inizio.year)


@app.get("/statistiche")
@login_richiesto
def statistiche():
    periodo = request.args.get("periodo")
    periodo = periodo if periodo in PERIODI else "giorno"
    chi = persona(request.args.get("persona", type=int) or 0)
    dati = consumi(chi["id"] if chi else None)
    oggi = datetime.now(TZ).date()
    quanti = QUANTI_PERIODI.get(periodo) or \
        oggi.year - min((giorno.year for giorno, _p, _q in dati), default=oggi.year) + 1
    inizi = [inizio_periodo(oggi, periodo)]          # dal più recente
    while len(inizi) < quanti:
        inizi.append(periodo_prima(inizi[-1], periodo))
    conteggi = {i: {} for i in inizi}
    attuali = {p: {} for p in PERIODI}               # oggi, questa settimana, questo mese, quest'anno
    ultimi_30 = {}
    for giorno, prid, qta in dati:
        k = inizio_periodo(giorno, periodo)
        if k in conteggi:
            conteggi[k][prid] = conteggi[k].get(prid, 0) + qta
        for p in PERIODI:
            if inizio_periodo(giorno, p) == inizio_periodo(oggi, p):
                attuali[p][prid] = attuali[p].get(prid, 0) + qta
        if 0 <= (oggi - giorno).days < 30:
            ultimi_30[prid] = ultimi_30.get(prid, 0) + qta
    righe = [{"etichetta": etichetta_periodo(i, periodo, oggi), "conteggi": conteggi[i],
              "totale": sum(conteggi[i].values())} for i in inizi]
    tutti_i_prodotti = prodotti(solo_attivi=False)
    usati = {prid for _g, prid, _q in dati}
    return render_template(
        "statistiche.html", periodo=periodo, chi=chi, righe=righe, attuali=attuali,
        massimo=max(r["totale"] for r in righe) or 1, ci_sono_dati=bool(dati),
        media={prid: f"{n / 30:.1f}".replace(".", ",") for prid, n in ultimi_30.items()},
        prodotti=[pr for pr in tutti_i_prodotti if pr["attivo"] or pr["id"] in usati],
        # il colore segue il prodotto (posizione fissa nell'elenco), non cambia con i filtri
        colori={pr["id"]: min(i, 7) for i, pr in enumerate(tutti_i_prodotti)},
        nomi_prodotti={pr["id"]: nome_prodotto(pr) for pr in tutti_i_prodotti},
        persone=[p for p in elenco_saldi() if not p["speciale"]],
        # conti comuni che pagano qualche prodotto (es. Macchinetta del caffè per l'acqua macchinetta)
        conti=db().execute("""SELECT * FROM persone WHERE speciale = 1 AND id IN
                              (SELECT persona_id FROM movimenti WHERE tipo = 'acquisto'
                               UNION SELECT addebito_id FROM prodotti WHERE addebito_id IS NOT NULL)
                              ORDER BY LOWER(nome)""").fetchall())


# --------------------------------------------------------------------------
# Avviso del lunedì via email
# --------------------------------------------------------------------------
def email_configurata():
    return bool(SMTP_USER and SMTP_PASSWORD)


def saldi_persone(con):
    return con.execute("""
        SELECT p.*, COALESCE(SUM(m.importo_cent), 0) AS saldo
        FROM persone p LEFT JOIN movimenti m ON m.persona_id = p.id AND m.annullato = 0
        WHERE p.attivo = 1 AND p.speciale = 0
        GROUP BY p.id""").fetchall()


def creditori(con, n=3):
    righe = [r for r in saldi_persone(con) if r["saldo"] > 0]
    return sorted(righe, key=lambda r: -r["saldo"])[:n]


def testo_email_avviso(p, cred, indirizzo):
    lingua = p["lingua"] if p["lingua"] in LINGUE else "it"
    t = lambda chiave, /, **kw: traduci(chiave, lingua, **kw)
    righe_cred = ", ".join(f"{nome_completo(c)} ({euro(c['saldo'])})" for c in cred) \
        or t("nessuno al momento")
    oggetto = t("{app}: il tuo saldo è {saldo}", app=NOME_APP, saldo=euro(p["saldo"]))
    corpo = "\n".join([
        t("Ciao {nome},", nome=p["nome"]), "",
        t("il tuo saldo su {app} è {saldo}.", app=NOME_APP, saldo=euro(p["saldo"])), "",
        t(TESTO_AVVISO), "",
        t("- Salda il debito: versa i soldi nella cassa e registralo nell'app"),
        t("  (Pagamenti tra persone → «Ho dato dei soldi a qualcuno» → Cassa)."),
        t("- Compra il credito di un altro utente: dai i soldi a chi è in credito e registralo"),
        t("  in «Pagamenti tra persone». In credito ora: {elenco}.", elenco=righe_cred),
        t("- Compra uno dei beni: compra caffè, acqua o altro per il gruppo e registralo"),
        t("  in «Ho comprato per il gruppo»."), "",
        t("Apri l'app: {url}", url=indirizzo), "",
        t("Questo avviso arriva ogni lunedì finché il saldo è negativo."),
        t("Per non riceverlo più per email: nell'app vai su Profilo e togli la spunta."), "",
    ])
    return oggetto, corpo


def spedisci(messaggi):
    """messaggi = [(destinatario, oggetto, corpo)] oppure con un quarto elemento:
    la lista degli allegati [(nome_file, byte, tipo, sottotipo)]. Ritorna (inviati, errori)."""
    if not messaggi:
        return 0, []
    inviati, errori = 0, []
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        for dest, oggetto, corpo, *altro in messaggi:
            msg = EmailMessage()
            msg["From"] = f"{NOME_APP} <{SMTP_USER}>"
            msg["To"] = dest
            msg["Subject"] = oggetto
            msg.set_content(corpo)
            for nome_file, dati, tipo, sottotipo in (altro[0] if altro else []):
                msg.add_attachment(dati, maintype=tipo, subtype=sottotipo, filename=nome_file)
            try:
                server.send_message(msg)
                inviati += 1
            except smtplib.SMTPException as e:
                errori.append(f"{dest}: {e}")
    return inviati, errori


def anteprima_avvisi(con, indirizzo):
    """Chi è in negativo e cosa riceverebbe adesso, senza spedire nulla.
    Ogni voce: persona, saldo, email, motivo ('' = la riceve, 'senza_email', 'disattivato'),
    oggetto e corpo dell'email (anche per chi non la riceve, per vedere il testo)."""
    cred = creditori(con, 3)
    voci = []
    for p in sorted((p for p in saldi_persone(con) if p["saldo"] < 0), key=lambda p: p["saldo"]):
        motivo = "" if p["email"] and p["avvisi_email"] else \
            ("senza_email" if not p["email"] else "disattivato")
        oggetto, corpo = testo_email_avviso(p, cred, indirizzo)
        voci.append({"persona": p, "nome": nome_completo(p), "saldo": p["saldo"], "email": p["email"],
                     "motivo": motivo, "oggetto": oggetto, "corpo": corpo})
    return voci


def invia_avvisi(con, indirizzo, solo_se_dovuto=True):
    """Manda l'email a chi è in negativo. Con solo_se_dovuto, al massimo una volta a settimana.
    Ritorna un dizionario con l'esito, oppure None se questa settimana è già stato fatto."""
    settimana = settimana_corrente()
    if solo_se_dovuto:
        with con:   # "prenota" la settimana: se due richieste arrivano insieme, ne parte una sola
            preso = con.execute("UPDATE impostazioni SET valore=? WHERE chiave='avviso_settimana' "
                                "AND valore<>?", (settimana, settimana)).rowcount
        if not preso:
            return None
    voci = anteprima_avvisi(con, indirizzo)
    messaggi = [(v["email"], v["oggetto"], v["corpo"]) for v in voci if not v["motivo"]]
    esito = {"quando": adesso(), "settimana": settimana, "in_negativo": len(voci),
             "con_email": len(messaggi), "inviati": 0, "errori": []}
    try:
        esito["inviati"], esito["errori"] = spedisci(messaggi)
    except Exception as e:   # credenziali sbagliate, rete, …
        esito["errori"] = [f"{type(e).__name__}: {e}"]
    with con:
        con.execute("UPDATE impostazioni SET valore=? WHERE chiave='avviso_esito'",
                    (json.dumps(esito, ensure_ascii=False),))
    return esito


# --------------------------------------------------------------------------
# Backup settimanale per email agli amministratori
# --------------------------------------------------------------------------
def copia_database(con):
    """Copia completa e coerente del database, come byte (si può fare mentre l'app lavora)."""
    fd, percorso = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        dest = sqlite3.connect(percorso)
        con.backup(dest)
        dest.close()
        with open(percorso, "rb") as f:
            return f.read()
    finally:
        os.unlink(percorso)


def destinatari_backup(con):
    return con.execute("SELECT * FROM persone WHERE admin=1 AND attivo=1 AND speciale=0 "
                       "AND email<>'' ORDER BY nome, cognome").fetchall()


def testo_email_backup(p, ora, negativi, file_excel, file_db):
    lingua = p["lingua"] if p["lingua"] in LINGUE else "it"
    t = lambda chiave, /, **kw: traduci(chiave, lingua, **kw)
    oggetto = t("{app}: backup del {data}", app=NOME_APP, data=f"{ora:%d/%m/%Y}")
    corpo = "\n".join([
        t("Ciao {nome},", nome=p["nome"]), "",
        t("ecco il backup settimanale di {app}, con i dati aggiornati al {quando}.",
          app=NOME_APP, quando=f"{ora:%d/%m/%Y %H:%M}"), "",
        t("In allegato:"),
        t("- {file}: saldi, movimenti e approvazioni, da aprire con Excel;", file=file_excel),
        t("- {file}: il database completo, serve per rimettere in piedi l'app.", file=file_db), "",
        t("In negativo adesso: {n} persone, per un totale di {totale}.", n=len(negativi),
          totale=euro(-sum(x["saldo"] for x in negativi), segno=False)), "",
        t("Conserva questa email: se l'account PythonAnywhere si perde, con il file .db si ripristina tutto (guida, «Ripristino da un backup»)."),
        t("Contiene i dati del gruppo e i PIN cifrati: non inoltrarla."), "",
        t("Arriva ogni lunedì agli amministratori che hanno l'email nel Profilo."), "",
    ])
    return oggetto, corpo


def invia_backup(solo_se_dovuto=True):
    """Manda l'Excel e il database agli amministratori che hanno l'email.
    Con solo_se_dovuto, al massimo una volta a settimana (dal lunedì alle 8).
    Ritorna l'esito, oppure None se non c'era niente da fare."""
    con = db()
    settimana = settimana_corrente()
    dest = destinatari_backup(con)
    if not dest:
        return None if solo_se_dovuto else {"destinatari": [], "inviati": 0, "errori": []}
    with con:   # "prenota" la settimana: se due richieste arrivano insieme, ne parte uno solo
        preso = con.execute("UPDATE impostazioni SET valore=? WHERE chiave='backup_settimana' "
                            "AND valore<>?", (settimana, settimana)).rowcount
    if solo_se_dovuto and not preso:
        return None
    ora = datetime.now(TZ)
    file_excel, file_db = f"caffe_{ora:%Y-%m-%d}.xlsx", f"caffe_backup_{ora:%Y-%m-%d}.db"
    dati_db = copia_database(con)
    negativi = [x for x in saldi_persone(con) if x["saldo"] < 0]
    excel, messaggi = {}, []
    for p in dest:
        lingua = p["lingua"] if p["lingua"] in LINGUE else "it"
        if lingua not in excel:
            excel[lingua] = crea_excel(con_approvazioni=True, lingua=lingua)
        messaggi.append((p["email"], *testo_email_backup(p, ora, negativi, file_excel, file_db),
                         [(file_excel, excel[lingua], *TIPO_XLSX.split("/")),
                          (file_db, dati_db, "application", "octet-stream")]))
    esito = {"quando": adesso(), "settimana": settimana,
             "destinatari": [nome_completo(p) for p in dest], "inviati": 0, "errori": []}
    try:
        esito["inviati"], esito["errori"] = spedisci(messaggi)
    except Exception as e:   # credenziali sbagliate, rete, …
        esito["errori"] = [f"{type(e).__name__}: {e}"]
    with con:
        con.execute("UPDATE impostazioni SET valore=? WHERE chiave='backup_esito'",
                    (json.dumps(esito, ensure_ascii=False),))
    return esito


def _lavori_del_lunedi(indirizzo, avvisi, backup):
    """Avvisi a chi è in negativo e backup agli admin, dopo aver già risposto all'utente."""
    with app.app_context():
        if avvisi:
            try:
                invia_avvisi(db(), indirizzo)
            except Exception:
                app.logger.exception("Invio avvisi del lunedì non riuscito")
        if backup:
            try:
                invia_backup()
            except Exception:
                app.logger.exception("Backup del lunedì non riuscito")


@app.after_request
def lavori_automatici(risposta):
    """Senza attività pianificate: la prima pagina aperta dopo lunedì alle 8 fa partire
    le email (avvisi e backup), dopo aver già risposto all'utente (così non deve aspettare)."""
    try:
        if email_configurata() and request.endpoint not in (None, "static"):
            settimana = settimana_corrente()
            r = db().execute("""SELECT
                (SELECT valore FROM impostazioni WHERE chiave='avviso_settimana') AS avvisi,
                (SELECT valore FROM impostazioni WHERE chiave='backup_settimana') AS backup,
                EXISTS (SELECT 1 FROM persone WHERE admin=1 AND attivo=1 AND speciale=0
                        AND email<>'') AS admin_con_email""").fetchone()
            avvisi = r["avvisi"] is not None and r["avvisi"] != settimana
            backup = bool(r["admin_con_email"]) and r["backup"] is not None and r["backup"] != settimana
            if avvisi or backup:
                indirizzo = os.environ.get("CAFFE_URL") or url_for("home", _external=True)
                risposta.call_on_close(lambda: _lavori_del_lunedi(indirizzo, avvisi, backup))
    except Exception:
        app.logger.exception("Controllo email del lunedì non riuscito")
    return risposta


@app.get("/cron/avvisi")
def cron_avvisi():
    """Facoltativo: da chiamare ogni lunedì con un servizio di cron online."""
    if not CRON_TOKEN or not secrets.compare_digest(request.args.get("token", ""), CRON_TOKEN):
        abort(404)
    esito = invia_avvisi(db(), os.environ.get("CAFFE_URL") or url_for("home", _external=True))
    return {"stato": "già inviati questa settimana"} if esito is None else esito


# --------------------------------------------------------------------------
# Export Excel e QR code
# --------------------------------------------------------------------------
@app.get("/export.xlsx")
@login_richiesto
def export_excel():
    nome_file = f"caffe_{datetime.now(TZ):%Y-%m-%d}.xlsx"
    return send_file(io.BytesIO(crea_excel(con_approvazioni=bool(g.utente["admin"]))),
                     as_attachment=True, download_name=nome_file, mimetype=TIPO_XLSX)


TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def crea_excel(con_approvazioni=False, lingua=None):
    """Il file Excel (saldi, movimenti e, per gli admin, approvazioni) come byte.
    Funziona anche fuori da una pagina (backup del lunedì), nella lingua indicata."""
    if lingua:
        prima = g.get("lingua")
        g.lingua = lingua
        try:
            return crea_excel(con_approvazioni)
        finally:
            g.lingua = prima
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    font, bold = Font(name="Arial"), Font(name="Arial", bold=True)
    grigio = PatternFill("solid", start_color="D9D9D9")
    wb = Workbook()

    ws = wb.active
    from openpyxl.utils import get_column_letter
    elenco_prod = prodotti(solo_attivi=False)
    conteggi = conteggi_prodotti()
    ws.title = _("Saldi")
    ws.append([_("Nome"), _("Cognome"), _("Saldo (€)")] + [_("{nome} (n°)", nome=nome_prodotto(p))
                                                         for p in elenco_prod]
              + [_("Tipo"), _("Attivo"), _("Ultimo movimento")])
    righe = elenco_saldi(includi_inattivi=True)
    for r in righe:
        c = conteggi.get(r["id"], {})
        ws.append([r["nome"], r["cognome"], r["saldo"] / 100]
                  + [c.get(p["id"], 0) for p in elenco_prod]
                  + [_("Conto comune") if r["speciale"] else _("Persona"),
                     _("Sì") if r["attivo"] else _("No"),
                     ora_locale(r["ultimo"]) if r["ultimo"] else ""])
    n = len(righe) + 1
    ws.append([_("TOTALE"), ""] + [f"=SUM({get_column_letter(k)}2:{get_column_letter(k)}{n})"
                                for k in range(3, 4 + len(elenco_prod))])
    for riga in ws.iter_rows():
        for c in riga:
            c.font = font
    for c in ws[1] + ws[n + 1]:
        c.font, c.fill = bold, grigio
    for c in ws["C"][1:]:
        c.number_format = '+0.00;-0.00;0.00'
    for k in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(k)].width = 16 if k <= 3 else 14
    ws.freeze_panes = "A2"

    ws2 = wb.create_sheet(_("Movimenti"))
    ws2.append([_("Data e ora"), _("Persona"), _("Tipo"), _("Descrizione"), _("Prodotto"),
                _("Quantità"), _("Importo (€)"), _("Registrato da"), _("Annullato")])
    nomi = {p["id"]: nome_completo(p) for p in righe}
    for m in db().execute("SELECT * FROM movimenti ORDER BY id").fetchall():
        ws2.append([da_iso(m["ts"]).astimezone(TZ).strftime("%d/%m/%Y %H:%M"),
                    nomi.get(m["persona_id"], "?"), _(m["tipo"]), descrizione(m),
                    nome_prodotto(prodotto(m["prodotto_id"])) if m["prodotto_id"]
                    and prodotto(m["prodotto_id"]) else "",
                    m["qta"] or None, m["importo_cent"] / 100,
                    nomi.get(m["creato_da"], ""), _("Sì") if m["annullato"] else ""])
    for riga in ws2.iter_rows():
        for c in riga:
            c.font = font
    for c in ws2[1]:
        c.font, c.fill = bold, grigio
    for c in ws2["G"][1:]:
        c.number_format = '+0.00;-0.00;0.00'
    for col, w in zip("ABCDEFGHI", (17, 20, 13, 46, 20, 9, 12, 20, 10)):
        ws2.column_dimensions[col].width = w
    ws2.freeze_panes = "A2"
    for c in ws2["D"]:
        c.alignment = Alignment(wrap_text=False)

    if con_approvazioni:
        accessi, spese, pagamenti, nomi, _ids = registro_dati(limite=100000)
        ws3 = wb.create_sheet(_("Approvazioni"))
        ws3.append([_("Data e ora"), _("Tipo"), _("Richiesta da"), _("Descrizione"), _("Importo (€)"),
                    _("Esito"), _("Deciso da"), _("Data decisione")])
        esiti = {"approvata": _("approvata"), "rifiutata": _("rifiutata"), "annullata": _("annullata dal richiedente")}
        for r in spese + pagamenti:
            ws3.append([da_iso(r["ts"]).astimezone(TZ).strftime("%d/%m/%Y %H:%M"),
                        _("Spesa") if r["tipo"] == "spesa" else _("Pagamento"),
                        nomi.get(r["richiedente_id"], "?"), descrivi_richiesta(r), r["importo_cent"] / 100,
                        esiti.get(r["stato"], r["stato"]), nomi.get(r["deciso_da"], ""),
                        da_iso(r["deciso_ts"]).astimezone(TZ).strftime("%d/%m/%Y %H:%M") if r["deciso_ts"] else ""])
        for a in accessi:
            ws3.append([da_iso(a["ts"]).astimezone(TZ).strftime("%d/%m/%Y %H:%M"), _("Accesso"),
                        a["richiesto"], a["account"] and _("per l'account «{nome}»", nome=a["account"]) or _("nuovo account"),
                        None, _(a["esito"]), nomi.get(a["deciso_da"], _("console")),
                        da_iso(a["ts"]).astimezone(TZ).strftime("%d/%m/%Y %H:%M")])
        for riga in ws3.iter_rows():
            for c in riga:
                c.font = font
        for c in ws3[1]:
            c.font, c.fill = bold, grigio
        for col, w in zip("ABCDEFGH", (17, 12, 20, 50, 12, 22, 20, 17)):
            ws3.column_dimensions[col].width = w
        ws3.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@app.get("/qr")
@login_richiesto
def qr():
    import segno
    from urllib.parse import urlparse
    indirizzo = indirizzo_qr()
    # viewBox (omitsize) così il QR si ridimensiona sempre intero, a schermo e in stampa
    svg = segno.make(indirizzo, error="m").svg_inline(scale=12, border=2, dark="#2b1d14", omitsize=True)
    # se il QR porta a un indirizzo diverso da quello che si sta usando (es. CAFFE_URL sbagliato), avvisa
    diverso = urlparse(indirizzo).netloc.lower() != request.host.lower()
    return render_template("qr.html", svg=svg, indirizzo=indirizzo, prodotti=prodotti(),
                           diverso=diverso, host_attuale=request.host)


def indirizzo_qr():
    return os.environ.get("CAFFE_URL") or url_for("home", _external=True)


@app.get("/qr.png")
@login_richiesto
def qr_png():
    """Il QR come immagine: si può salvare, stampare o mettere in un documento (funziona anche dall'icona su iPhone)."""
    import segno
    buf = io.BytesIO()
    segno.make(indirizzo_qr(), error="m").save(buf, kind="png", scale=20, border=3, dark="#2b1d14")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name="qr-caffe-lab.png", as_attachment=False)


# --------------------------------------------------------------------------
# Amministrazione
# --------------------------------------------------------------------------
@app.get("/admin")
@admin_richiesto
def admin():
    righe = elenco_saldi(includi_inattivi=True)
    r = db().execute("SELECT valore FROM impostazioni WHERE chiave='avviso_esito'").fetchone()
    esito = json.loads(r["valore"]) if r and r["valore"] else None
    persone_neg = [p for p in saldi_persone(db()) if p["saldo"] < 0]
    r = db().execute("SELECT valore FROM impostazioni WHERE chiave='backup_esito'").fetchone()
    esito_backup = json.loads(r["valore"]) if r and r["valore"] else None
    admin_attivi = [p for p in righe if p["admin"] and p["attivo"] and not p["speciale"]]
    return render_template("admin.html", righe=righe, prodotti=prodotti(solo_attivi=False),
                           esito_backup=esito_backup,
                           backup_a=[nome_completo(p) for p in admin_attivi if p["email"]],
                           backup_senza_email=[nome_completo(p) for p in admin_attivi if not p["email"]],
                           conti=[r for r in righe if r["speciale"]], esito=esito,
                           email_attiva=email_configurata(), smtp_user=SMTP_USER,
                           n_negativo=len(persone_neg),
                           limite=limite_debito()[0], limite_modo=limite_debito()[1],
                           n_oltre=sum(1 for p in persone_neg
                                       if limite_debito()[0] and p["saldo"] < -limite_debito()[0]),
                           n_da_approvare=conta_da_fare(g.utente),
                           comunicazioni=comunicazioni_admin(), max_testo=MAX_TESTO_COMUNICAZIONE,
                           n_con_accesso=sum(1 for p in righe if p["attivo"] and not p["speciale"]
                                             and p["pin_hash"] and p["approvato"]),
                           n_senza_email=sum(1 for p in persone_neg if not p["email"]),
                           manutenzioni=manutenzioni_con_stato(solo_attive=False),
                           storico_manutenzioni=db().execute("""
                               SELECT f.ts, m.nome, p.nome AS pn, p.cognome AS pc
                               FROM manutenzioni_fatte f JOIN manutenzioni m ON m.id = f.manutenzione_id
                               LEFT JOIN persone p ON p.id = f.persona_id
                               ORDER BY f.id DESC LIMIT 10""").fetchall())


def _leggi_manutenzione_da_form():
    nome = request.form.get("nome", "").strip()[:60]
    giorni = request.form.get("ogni_giorni", type=int) or 0
    return nome, giorni


@app.post("/admin/manutenzione/nuova")
@admin_richiesto
def admin_manutenzione_nuova():
    nome, giorni = _leggi_manutenzione_da_form()
    if not nome or not 1 <= giorni <= 730:
        flash(_("Servono un nome e un numero di giorni tra 1 e 730."), "errore")
    else:
        with db():
            db().execute("INSERT INTO manutenzioni (nome, ogni_giorni, ultima_ts) VALUES (?,?,?)",
                         (nome, giorni, adesso()))
        flash(_("Promemoria aggiunto: {nome}, ogni {giorni} giorni.", nome=nome, giorni=giorni), "ok")
    return redirect(url_for("admin"))


@app.post("/admin/manutenzione/<int:mid>")
@admin_richiesto
def admin_manutenzione(mid):
    m = db().execute("SELECT * FROM manutenzioni WHERE id=?", (mid,)).fetchone() or abort(404)
    if request.form.get("elimina"):
        with db():
            db().execute("DELETE FROM manutenzioni_fatte WHERE manutenzione_id=?", (mid,))
            db().execute("DELETE FROM manutenzioni WHERE id=?", (mid,))
        flash(_("Promemoria eliminato: {nome}.", nome=m["nome"]), "ok")
        return redirect(url_for("admin"))
    nome, giorni = _leggi_manutenzione_da_form()
    if not nome or not 1 <= giorni <= 730:
        flash(_("Servono un nome e un numero di giorni tra 1 e 730."), "errore")
        return redirect(url_for("admin"))
    ultima = m["ultima_ts"]
    data = request.form.get("ultima", "").strip()          # AAAA-MM-GG dal selettore di data
    if data:
        try:
            giorno = datetime.strptime(data, "%Y-%m-%d").replace(hour=12, tzinfo=TZ)
            if giorno.date() > datetime.now(TZ).date():
                raise ValueError
            ultima = giorno.astimezone(timezone.utc).isoformat(timespec="seconds")
        except ValueError:
            flash(_("Data non valida (non può essere nel futuro)."), "errore")
            return redirect(url_for("admin"))
    with db():
        db().execute("UPDATE manutenzioni SET nome=?, ogni_giorni=?, ultima_ts=?, attivo=? WHERE id=?",
                     (nome, giorni, ultima, 1 if request.form.get("attivo") else 0, mid))
    flash(_("Promemoria aggiornato: {nome}.", nome=nome), "ok")
    return redirect(url_for("admin"))


@app.post("/admin/limite")
@admin_richiesto
def admin_limite():
    testo = request.form.get("limite", "").strip()
    cent = 0 if testo.strip("0,.€ ") == "" else leggi_euro(testo)
    if cent is None:
        flash(_("Limite non valido (es. 10 oppure 7,50; 0 = nessun limite)."), "errore")
        return redirect(url_for("admin"))
    modo = "blocca" if request.form.get("modo") == "blocca" else "avvisa"
    with db():
        imposta("limite_debito_cent", cent)
        imposta("limite_modo", modo)
    flash(_("Limite di debito tolto.") if not cent else
          _("Limite di debito: {limite} ({modo}).", limite=euro(cent, segno=False),
            modo=_("blocca gli acquisti") if modo == "blocca" else _("avvisa e chiede conferma")), "ok")
    return redirect(url_for("admin"))


@app.post("/admin/avvisi/prova")
@admin_richiesto
def admin_avvisi_prova():
    u = g.utente
    if not email_configurata():
        flash(_("Email non configurata: vedi la guida (CAFFE_SMTP_USER e CAFFE_SMTP_PASSWORD)."), "errore")
    elif not u["email"]:
        flash(_("Aggiungi prima la tua email nel Profilo."), "errore")
    else:
        prova = dict(u)
        prova["saldo"] = saldo(u["id"]) if saldo(u["id"]) < 0 else -420
        oggetto, corpo = testo_email_avviso(prova, creditori(db(), 3),
                                            os.environ.get("CAFFE_URL") or url_for("home", _external=True))
        try:
            n, errori = spedisci([(u["email"], "[PROVA] " + oggetto, corpo)])
            flash(_("Email di prova inviata a {email}.", email=u['email']) if n
                  else _("Invio non riuscito: {errore}", errore=errori),
                  "ok" if n else "errore")
        except Exception as e:
            flash(_("Invio non riuscito: {errore}", errore=f"{type(e).__name__}: {e}"), "errore")
    return redirect(url_for("admin"))


@app.get("/admin/avvisi/anteprima")
@admin_richiesto
def admin_avvisi_anteprima():
    """Prova a secco: chi riceverebbe l'avviso e con quale testo. Non spedisce nulla."""
    voci = anteprima_avvisi(db(), os.environ.get("CAFFE_URL") or url_for("home", _external=True))
    return render_template("avvisi_anteprima.html", voci=voci, email_attiva=email_configurata(),
                           mittente=f"{NOME_APP} <{SMTP_USER}>" if SMTP_USER else "",
                           n_ricevono=sum(1 for v in voci if not v["motivo"]))


@app.post("/admin/avvisi/invia")
@admin_richiesto
def admin_avvisi_invia():
    if not email_configurata():
        flash(_("Email non configurata: vedi la guida."), "errore")
        return redirect(url_for("admin"))
    esito = invia_avvisi(db(), os.environ.get("CAFFE_URL") or url_for("home", _external=True),
                         solo_se_dovuto=False)
    flash(_("Avvisi inviati: {n} su {tot}.", n=esito['inviati'], tot=esito['con_email'])
          + (" " + _("Errori: {errori}", errori="; ".join(esito["errori"])) if esito["errori"] else ""),
          "errore" if esito["errori"] else "ok")
    return redirect(url_for("admin"))


@app.post("/admin/backup/invia")
@admin_richiesto
def admin_backup_invia():
    if not email_configurata():
        flash(_("Email non configurata: vedi la guida."), "errore")
        return redirect(url_for("admin") + "#backup")
    esito = invia_backup(solo_se_dovuto=False)
    if not esito["destinatari"]:
        flash(_("Nessun amministratore ha l'email: aggiungi la tua nel Profilo."), "errore")
    elif esito["errori"]:
        flash(_("Invio non riuscito: {errore}", errore="; ".join(esito["errori"])), "errore")
    else:
        flash(_("Backup inviato a: {nomi}", nomi=", ".join(esito["destinatari"])), "ok")
    return redirect(url_for("admin") + "#backup")


def _leggi_prodotto_da_form():
    nome = request.form.get("nome", "").strip()[:40]
    emoji = request.form.get("emoji", "").strip()[:4]
    prezzo = leggi_euro(request.form.get("prezzo"), consenti_zero=True)   # 0 = gratis (es. bicchierino vuoto)
    addebito = request.form.get("addebito_id", type=int) or None
    if addebito:
        conto = persona(addebito)
        if not conto or not conto["speciale"]:
            addebito = None
    descrizione = " ".join(request.form.get("descrizione", "").split())[:150]
    return nome, emoji, prezzo, addebito, descrizione


@app.post("/admin/prodotto/<int:prid>")
@admin_richiesto
def admin_prodotto(prid):
    pr = prodotto(prid) or abort(404)
    nome, emoji, prezzo, addebito, descrizione = _leggi_prodotto_da_form()
    if not nome or prezzo is None:
        flash(_("Servono un nome e un prezzo valido."), "errore")
        return redirect(url_for("admin"))
    attivo = 1 if request.form.get("attivo") else 0
    with db():
        db().execute("UPDATE prodotti SET nome=?, emoji=?, prezzo_cent=?, addebito_id=?, attivo=?, descrizione=?"
                     " WHERE id=?", (nome, emoji, prezzo, addebito, attivo, descrizione, prid))
    flash(_("{nome} aggiornato. Il prezzo vale per gli acquisti da ora in poi.", nome=nome), "ok")
    return redirect(url_for("admin"))


@app.post("/admin/prodotto/nuovo")
@admin_richiesto
def admin_prodotto_nuovo():
    nome, emoji, prezzo, addebito, descrizione = _leggi_prodotto_da_form()
    if not nome or prezzo is None:
        flash(_("Servono un nome e un prezzo valido."), "errore")
        return redirect(url_for("admin"))
    ordine = (db().execute("SELECT MAX(ordine) AS m FROM prodotti").fetchone()["m"] or 0) + 1
    with db():
        db().execute("INSERT INTO prodotti (nome, emoji, prezzo_cent, addebito_id, ordine, descrizione) "
                     "VALUES (?,?,?,?,?,?)", (nome, emoji, prezzo, addebito, ordine, descrizione))
    flash(_("Prodotto aggiunto: {nome}.", nome=nome), "ok")
    return redirect(url_for("admin"))


@app.post("/admin/persona/nuova")
@admin_richiesto
def admin_nuova_persona():
    nome = request.form.get("nome", "").strip()
    cognome = request.form.get("cognome", "").strip()
    speciale = 1 if request.form.get("speciale") else 0
    iniziale = request.form.get("saldo", "").strip()
    if iniziale.strip("0,.+-€ ") == "":      # vuoto o zero: nessun saldo iniziale
        iniziale = ""
    cent = leggi_euro(iniziale, consenti_negativo=True) if iniziale else None
    if not nome:
        flash(_("Il nome è obbligatorio."), "errore")
        return redirect(url_for("admin"))
    if iniziale and cent is None:
        flash(_("Saldo iniziale non valido."), "errore")
        return redirect(url_for("admin"))
    with db():
        cur = db().execute("INSERT INTO persone (nome, cognome, speciale, creato) "
                           "VALUES (?,?,?,?)", (nome, cognome, speciale, adesso()))
        if cent:
            registra(cur.lastrowid, "iniziale", cent, creato_da=g.utente["id"])
    flash(_("Aggiunto: {nome}.", nome=f"{nome} {cognome}".strip()), "ok")
    return redirect(url_for("admin"))


@app.route("/admin/persona/<int:pid>", methods=["GET", "POST"])
@admin_richiesto
def admin_persona(pid):
    p = persona(pid) or abort(404)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip() or p["nome"]
        cognome = request.form.get("cognome", "").strip()
        attivo = 1 if request.form.get("attivo") else 0
        adm = 1 if request.form.get("admin") else 0
        speciale = 1 if request.form.get("speciale") else 0
        email = email_valida(request.form.get("email"))
        if pid == g.utente["id"] and (not adm or not attivo):
            flash(_("Non puoi togliere a te stesso i permessi di amministratore o disattivarti."),
                  "errore")
            return redirect(url_for("admin_persona", pid=pid))
        with db():
            db().execute("UPDATE persone SET nome=?, cognome=?, attivo=?, admin=?, speciale=?, email=?,"
                         " versione_sessione = versione_sessione + ? WHERE id=?",
                         (nome, cognome, attivo, adm, speciale, email,
                          1 if (not attivo and p["attivo"]) else 0, pid))
        flash(_("Dati aggiornati."), "ok")
        return redirect(url_for("admin"))
    return render_template("admin_persona.html", p=p, saldo=saldo(pid))


@app.post("/admin/persona/<int:pid>/reset-pin")
@admin_richiesto
def admin_reset_pin(pid):
    p = persona(pid) or abort(404)
    with db():
        db().execute("UPDATE persone SET pin_hash=NULL, tentativi=0, bloccato_fino=NULL, "
                     "versione_sessione = versione_sessione + 1 WHERE id=?", (pid,))
    flash(_("PIN di {nome} azzerato: al prossimo accesso ne sceglierà uno nuovo.", nome=nome_completo(p)), "ok")
    return redirect(url_for("admin_persona", pid=pid))


@app.post("/admin/rettifica")
@admin_richiesto
def admin_rettifica():
    p = persona(request.form.get("persona_id", type=int) or 0)
    cent = leggi_euro(request.form.get("importo"), consenti_negativo=True)
    nota = request.form.get("nota", "").strip()[:200]
    if not p or cent is None or not nota:
        flash(_("Per la rettifica servono persona, importo (anche negativo) e motivo."), "errore")
    else:
        with db():
            registra(p["id"], "rettifica", cent, nota=f"Rettifica: {nota}",
                     creato_da=g.utente["id"])
        flash(_("Rettifica registrata per {nome}: {importo}.", nome=nome_completo(p), importo=euro(cent)), "ok")
    return redirect(url_for("admin"))


# --------------------------------------------------------------------------
# Magazzino (solo admin): quantità, soglie, cosa consuma ogni prodotto
# --------------------------------------------------------------------------
@app.get("/admin/magazzino")
@admin_richiesto
def admin_magazzino():
    elenco = articoli(solo_attivi=False)
    ricette = {(r["prodotto_id"], r["articolo_id"]): r["qta"]
               for r in db().execute("SELECT * FROM ricette").fetchall()}
    registro = db().execute("""
        SELECT g.*, a.nome AS articolo, a.emoji, COALESCE(m.annullato, 0) AS annullato
        FROM magazzino g JOIN articoli a ON a.id = g.articolo_id
        LEFT JOIN movimenti m ON m.id = g.movimento_id
        ORDER BY g.id DESC LIMIT 60""").fetchall()
    return render_template("magazzino.html", articoli=elenco, prodotti=prodotti(solo_attivi=False),
                           ricette=ricette, registro=registro,
                           nomi={p["id"]: nome_completo(p) for p in elenco_saldi(includi_inattivi=True)})


def _leggi_articolo_da_form():
    nome = request.form.get("nome", "").strip()[:40]
    emoji = request.form.get("emoji", "").strip()[:4]
    soglia = request.form.get("soglia", "").strip()
    return nome, emoji, int(soglia) if soglia.isdigit() and int(soglia) <= MAX_PEZZI_SPESA else None


@app.post("/admin/articolo/<int:aid>")
@admin_richiesto
def admin_articolo(aid):
    a = next((x for x in articoli(solo_attivi=False) if x["id"] == aid), None) or abort(404)
    nome, emoji, soglia = _leggi_articolo_da_form()
    testo_contati = request.form.get("contati", "").strip()
    contati = int(testo_contati) if testo_contati.isdigit() else None
    if not nome or soglia is None:
        flash(_("Servono un nome e una soglia (numero di pezzi, anche 0)."), "errore")
        return redirect(url_for("admin_magazzino"))
    if testo_contati and (contati is None or contati > MAX_PEZZI_SPESA):
        flash(_("Scrivi quanti pezzi hai contato (un numero intero, anche 0)."), "errore")
        return redirect(url_for("admin_magazzino"))
    with db():
        db().execute("UPDATE articoli SET nome=?, emoji=?, soglia=?, attivo=? WHERE id=?",
                     (nome, emoji, soglia, 1 if request.form.get("attivo") else 0, aid))
        if contati is not None:
            # la conta vera sostituisce quella calcolata: la differenza resta nel registro
            db().execute("INSERT INTO magazzino (ts, articolo_id, qta, tipo, persona_id, nota) "
                         "VALUES (?,?,?, 'inventario', ?, ?)",
                         (adesso(), aid, contati - a["giacenza"], g.utente["id"],
                          f"contati {contati} (prima {a['giacenza']})"))
    if contati is not None:
        flash(_("{nome}: ora ne risultano {n}.", nome=nome, n=contati), "ok")
    else:
        flash(_("{nome} aggiornato.", nome=nome), "ok")
    return redirect(url_for("admin_magazzino"))


@app.post("/admin/articolo/nuovo")
@admin_richiesto
def admin_articolo_nuovo():
    nome, emoji, soglia = _leggi_articolo_da_form()
    if not nome or soglia is None:
        flash(_("Servono un nome e una soglia (numero di pezzi, anche 0)."), "errore")
        return redirect(url_for("admin_magazzino"))
    ordine = (db().execute("SELECT MAX(ordine) AS m FROM articoli").fetchone()["m"] or 0) + 1
    with db():
        db().execute("INSERT INTO articoli (nome, emoji, soglia, ordine) VALUES (?,?,?,?)",
                     (nome, emoji, soglia, ordine))
    flash(_("Articolo aggiunto: {nome}. Inserisci quanti pezzi ci sono.", nome=nome), "ok")
    return redirect(url_for("admin_magazzino"))


@app.post("/admin/ricette")
@admin_richiesto
def admin_ricette():
    """Quanti pezzi di ogni articolo scala ciascun prodotto (vale per gli acquisti da ora in poi)."""
    nuove = []
    for pr in prodotti(solo_attivi=False):
        for a in articoli(solo_attivi=False):
            testo = request.form.get(f"r_{pr['id']}_{a['id']}", "").strip()
            if testo and (not testo.isdigit() or int(testo) > 20):
                flash(_("Nelle ricette scrivi un numero di pezzi da 0 a 20."), "errore")
                return redirect(url_for("admin_magazzino"))
            if testo and int(testo):
                nuove.append((pr["id"], a["id"], int(testo)))
    with db():
        db().execute("DELETE FROM ricette")
        db().executemany("INSERT INTO ricette (prodotto_id, articolo_id, qta) VALUES (?,?,?)", nuove)
    flash(_("Ricette salvate: valgono per gli acquisti da ora in poi."), "ok")
    return redirect(url_for("admin_magazzino"))


def bilancio_magazzino():
    """Bilancio della merce dall'inizio del magazzino, per articolo e per prodotto.

    Per ogni articolo, in pezzi e in euro (al costo medio delle spese approvate):
        iniziale (prima conta) + comprati − consumati ± differenze delle conte = in magazzino
    Le differenze sono i pezzi spariti (o trovati) tra il calcolo e la conta vera: di solito
    consumi non segnati. Per ogni prodotto: quanto ha incassato e quanto è costata la sua merce."""
    per_art = {a["id"]: {"articolo": a, "iniziale": 0, "comprati": 0, "spesa": 0, "consumati": 0,
                         "differenze": 0, "contato": False} for a in articoli(solo_attivi=False)}
    venduti = {}                                       # movimento_id -> (prodotto_id, qta, incasso)
    consumi_per_mov = {}                               # movimento_id -> [(articolo_id, pezzi)]
    for r in db().execute("""
            SELECT g.*, m.prodotto_id, m.qta AS qta_mov, m.importo_cent AS importo_mov,
                   COALESCE(m.annullato, 0) AS annullato
            FROM magazzino g LEFT JOIN movimenti m ON m.id = g.movimento_id ORDER BY g.id""").fetchall():
        x = per_art.get(r["articolo_id"])
        if x is None or r["annullato"]:
            continue
        if r["tipo"] == "carico":
            x["comprati"] += r["qta"]
            x["spesa"] += r["costo_cent"]
        elif r["tipo"] == "consumo":
            x["consumati"] -= r["qta"]
            if r["movimento_id"]:
                venduti[r["movimento_id"]] = (r["prodotto_id"], r["qta_mov"], -r["importo_mov"])
                consumi_per_mov.setdefault(r["movimento_id"], []).append((r["articolo_id"], -r["qta"]))
        elif r["tipo"] == "inventario":
            if x["contato"]:
                x["differenze"] += r["qta"]
            else:                                      # la prima conta è la quantità di partenza
                x["iniziale"] += r["qta"]
                x["contato"] = True
    for x in per_art.values():
        x["giacenza"] = x["iniziale"] + x["comprati"] - x["consumati"] + x["differenze"]
        medio = x["spesa"] / x["comprati"] if x["comprati"] else None
        x["costo_medio"] = None if medio is None else round(medio)
        for voce in ("iniziale", "comprati", "consumati", "differenze", "giacenza"):
            x[f"valore_{voce}"] = None if medio is None else round(x[voce] * medio)
        x["valore_comprati"] = x["spesa"] if x["comprati"] else 0

    def costo(articolo_id, pezzi):
        medio = per_art[articolo_id]["spesa"] / per_art[articolo_id]["comprati"] \
            if per_art.get(articolo_id) and per_art[articolo_id]["comprati"] else None
        return None if medio is None else pezzi * medio

    ricette = {}
    for r in db().execute("SELECT * FROM ricette").fetchall():
        ricette.setdefault(r["prodotto_id"], []).append((r["articolo_id"], r["qta"]))
    per_prod = []
    for pr in prodotti(solo_attivi=False):
        movs = [mid for mid, v in venduti.items() if v[0] == pr["id"]]
        if not movs and pr["id"] not in ricette:
            continue
        costi = [costo(a, n) for mid in movs for a, n in consumi_per_mov[mid]]
        unitari = [costo(a, n) for a, n in ricette.get(pr["id"], [])]
        per_prod.append({
            "prodotto": pr,
            "pezzi": sum(venduti[mid][1] for mid in movs),
            "incasso": sum(venduti[mid][2] for mid in movs),
            "costo": None if None in costi else round(sum(costi)),
            "costo_unitario": None if None in unitari or not unitari else round(sum(unitari)),
        })
    for p in per_prod:
        p["margine"] = None if p["costo"] is None else p["incasso"] - p["costo"]
        p["margine_unitario"] = None if p["costo_unitario"] is None \
            else p["prodotto"]["prezzo_cent"] - p["costo_unitario"]
    elenco = [x for x in per_art.values() if x["contato"] or x["comprati"] or x["consumati"]]

    def somma(chiave, righe):
        valori = [r[chiave] for r in righe]
        return None if None in valori else sum(valori)
    totali = {k: somma(k, elenco) for k in ("valore_iniziale", "valore_comprati", "valore_consumati",
                                             "valore_differenze", "valore_giacenza")}
    totali.update({k: somma(k, per_prod) for k in ("incasso", "costo", "margine")})
    return elenco, per_prod, totali


@app.get("/admin/bilancio")
@admin_richiesto
def admin_bilancio():
    elenco, per_prod, totali = bilancio_magazzino()
    return render_template("bilancio.html", articoli=elenco, prodotti=per_prod, totali=totali)


MAX_TESTO_COMUNICAZIONE = 1000


def comunicazioni_admin():
    """Ultime comunicazioni con quante persone le hanno lette (su quelle che possono entrare)."""
    return db().execute("""
        SELECT c.*, p.nome, p.cognome,
               (SELECT COUNT(*) FROM comunicazioni_lette l JOIN persone q ON q.id = l.persona_id
                WHERE l.comunicazione_id = c.id AND q.attivo = 1 AND q.speciale = 0) AS lette
        FROM comunicazioni c LEFT JOIN persone p ON p.id = c.autore_id
        ORDER BY c.id DESC LIMIT 15""").fetchall()


@app.post("/admin/comunicazione/nuova")
@admin_richiesto
def admin_comunicazione_nuova():
    testo = request.form.get("testo", "").strip()
    if not testo or len(testo) > MAX_TESTO_COMUNICAZIONE:
        flash(_("Scrivi il testo della comunicazione (al massimo {n} caratteri).", n=MAX_TESTO_COMUNICAZIONE),
              "errore")
        return redirect(url_for("admin") + "#comunicazioni")
    with db():
        cid = db().execute("INSERT INTO comunicazioni (ts, autore_id, testo) VALUES (?,?,?)",
                           (adesso(), g.utente["id"], testo)).lastrowid
        # chi la scrive l'ha già letta
        db().execute("INSERT INTO comunicazioni_lette VALUES (?,?,?)", (cid, g.utente["id"], adesso()))
    flash(_("Comunicazione pubblicata: la vedono tutti in home finché non spuntano «Ho letto»."), "ok")
    return redirect(url_for("admin") + "#comunicazioni")


@app.post("/admin/comunicazione/<int:cid>/ritira")
@admin_richiesto
def admin_comunicazione_ritira(cid):
    with db():
        n = db().execute("UPDATE comunicazioni SET attiva=0 WHERE id=?", (cid,)).rowcount
    if not n:
        abort(404)
    flash(_("Comunicazione ritirata: non compare più a nessuno."), "ok")
    return redirect(url_for("admin") + "#comunicazioni")


@app.post("/admin/acquisto-per")
@admin_richiesto
def admin_acquisto_per():
    """Segna un acquisto direttamente sul conto scelto (anche per chi non ha il telefono)."""
    p = persona(request.form.get("persona_id", type=int) or 0)
    pr = prodotto(request.form.get("prodotto_id", type=int) or 0)
    qta = request.form.get("qta", type=int) or 0
    if not p or not pr or not 1 <= qta <= 50:
        flash(_("Scegli persona, prodotto e una quantità valida."), "errore")
    else:
        with db():
            mid = registra(p["id"], "acquisto", -qta * pr["prezzo_cent"], qta=qta, prodotto_id=pr["id"],
                           creato_da=g.utente["id"])
            scala_magazzino(mid, pr["id"], qta, p["id"])
        flash(_("Segnato {cosa} a {nome}.", cosa=etichetta_prodotto(pr, qta), nome=nome_completo(p)), "ok")
    return redirect(url_for("admin"))


@app.get("/admin/backup")
@admin_richiesto
def admin_backup():
    """Scarica una copia completa del database (da conservare ogni tanto)."""
    return send_file(io.BytesIO(copia_database(db())), as_attachment=True,
                     download_name=f"caffe_backup_{datetime.now(TZ):%Y-%m-%d}.db",
                     mimetype="application/octet-stream")


@app.get("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="icona-192.png"))


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def errore_http(e):
    desc = str(e.description or "")
    messaggi = {400: _("Sessione scaduta: ricarica la pagina e riprova.") if desc.startswith("Sessione")
                else _("Richiesta non valida."),
                403: _("Questa pagina è riservata agli amministratori."),
                404: _("Pagina non trovata.")}
    return render_template("errore.html", messaggio=messaggi.get(e.code, "Errore.")), e.code


def crea_root(pin):
    """Solo per le prove sul PC: amministratore «root», già approvato, con questo PIN.
    Se esiste già, gli rimette il PIN e lo riattiva. Ritorna il suo id."""
    con = connetti()
    with con:
        r = con.execute("SELECT id FROM persone WHERE nome='root' AND cognome='' AND speciale=0").fetchone()
        if r:
            pid = r["id"]
        else:
            pid = con.execute("INSERT INTO persone (nome, cognome, speciale, creato) VALUES ('root', '', 0, ?)",
                              (adesso(),)).lastrowid
        con.execute("UPDATE persone SET pin_hash=?, admin=1, approvato=1, attivo=1, tentativi=0, "
                    "bloccato_fino=NULL, nuovo_nome='', nuovo_cognome='' WHERE id=?",
                    (generate_password_hash(pin), pid))
    con.close()
    return pid


if __name__ == "__main__":
    # Solo per provarla sul tuo PC: python3 app.py  ->  http://localhost:5000
    # Sul server (WSGI) questo blocco non viene mai eseguito, quindi l'utente root non c'è.
    if os.environ.get("CAFFE_ROOT", "1") != "0":
        pin_root = os.environ.get("CAFFE_ROOT_PIN", "0000")
        if not pin_valido(pin_root):
            raise SystemExit("CAFFE_ROOT_PIN deve avere da 4 a 8 cifre.")
        crea_root(pin_root)
        print(f"Per le prove: entra come «root» con il PIN {pin_root} (amministratore, già approvato).")
    app.run(host="0.0.0.0", port=5000, debug=False)
