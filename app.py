"""
Caffè Lab – web app per segnare caffè e acqua e gestire i saldi del gruppo.

Principio: ogni operazione (acquisto, pagamento, spesa, rettifica) è una riga
nel registro "movimenti". Il saldo di una persona è la somma dei suoi
movimenti non annullati. Saldo positivo = credito, negativo = debito.
"""
import io
import json
import os
import secrets
import smtplib
import sqlite3
import uuid
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (Flask, abort, flash, g, has_request_context, redirect, render_template,
                   request, send_file, session, url_for)

from lingue import LINGUE, traduci
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
     "prezzo": 25, "conto": "Conto Caffè"},
]
FINESTRA_ANNULLA = timedelta(minutes=10)   # entro quanto si può annullare da soli
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
        colonne_p = {r["name"] for r in con.execute("PRAGMA table_info(persone)")}
        for col, tipo in (("email", "TEXT NOT NULL DEFAULT ''"),
                          ("avvisi_email", "INTEGER NOT NULL DEFAULT 1"),
                          ("avviso_letto", "TEXT NOT NULL DEFAULT ''"),
                          ("lingua", "TEXT NOT NULL DEFAULT ''")):
            if col not in colonne_p:
                con.execute(f"ALTER TABLE persone ADD COLUMN {col} {tipo}")
        # Le prime email partiranno dal prossimo lunedì, non appena si installa l'app
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('avviso_settimana', ?)",
                    (settimana_corrente(),))
        con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('avviso_esito', '')")
        # Promemoria di manutenzione di esempio (una volta sola; l'admin li modifica)
        if con.execute("INSERT OR IGNORE INTO impostazioni VALUES ('manutenzioni_esempio', '1')").rowcount:
            for nome, giorni in MANUTENZIONI_ESEMPIO:
                con.execute("INSERT INTO manutenzioni (nome, ogni_giorni, ultima_ts) VALUES (?,?,?)",
                            (nome, giorni, adesso()))
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


def leggi_euro(testo, consenti_negativo=False):
    """'5' / '5,50' / '5.5' / '-3,20' -> centesimi (int). None se non valido."""
    if testo is None:
        return None
    t = testo.strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not t:
        return None
    try:
        valore = round(float(t) * 100)
    except ValueError:
        return None
    if valore == 0 or abs(valore) > MAX_IMPORTO_CENT:
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
    return g.get("lingua", "it") if has_request_context() else "it"


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


def nome_completo(p):
    if p is None:
        return "?"
    return f"{p['nome']} {p['cognome']}".strip()


app.jinja_env.filters["euro"] = euro
app.jinja_env.filters["ora"] = ora_locale
app.jinja_env.filters["nome"] = nome_completo


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
    if m["creato_da"] != utente["id"]:
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
    uid = session.get("uid")
    if uid:
        p = persona(uid)
        if p and p["attivo"] and not p["speciale"] and p["pin_hash"] \
                and session.get("ver") == p["versione_sessione"]:
            g.utente = p
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
    return {"utente": g.get("utente"), "nome_app": NOME_APP, "lingua": lingua_corrente()}


app.jinja_env.globals["_"] = _


def login_richiesto(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not g.utente:
            return redirect(url_for("accedi"))
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
            return redirect(url_for("home"))
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
        db().execute("UPDATE persone SET nome=?, cognome=?, pin_hash=?, email=? WHERE id=?",
                     (nome, cognome, generate_password_hash(pin), email, p["id"]))
    apri_sessione(persona(p["id"]))
    flash(_("Account attivato! Da ora questo telefono si ricorda di te."), "ok")
    return redirect(url_for("home"))


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
                "INSERT INTO persone (nome, cognome, pin_hash, email, creato) VALUES (?,?,?,?,?)",
                (nome, cognome, generate_password_hash(pin),
                 email_valida(request.form.get("email")), adesso()))
        apri_sessione(persona(cur.lastrowid))
        flash(_("Benvenuto! Il tuo account è pronto."), "ok")
        return redirect(url_for("home"))
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
    avviso = None
    if mio_saldo < 0 and u["avviso_letto"] != settimana_corrente():
        avviso = {"cassa": conto_cassa(), "creditori": creditori(db(), 3),
                  "importo": f"{-mio_saldo / 100:.2f}".replace(".", ",")}
    manutenzioni = [m for m in manutenzioni_con_stato() if m["da_fare"]] if u["admin"] else []
    return render_template("home.html", saldo=mio_saldo, ultimi=ultimi, nomi=nomi, avviso=avviso,
                           manutenzioni=manutenzioni,
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
    if nonce_gia_usato(request.form.get("nonce")):
        return redirect(url_for("home"))
    gruppo = uuid.uuid4().hex
    a_carico_di_altri = []
    with db():
        for pr, q in scelte:
            chi = pr["addebito_id"] or u["id"]
            nota = f"presa da {nome_completo(u)}" if chi != u["id"] else ""
            registra(chi, "acquisto", -q * pr["prezzo_cent"], qta=q, prodotto_id=pr["id"],
                     gruppo=gruppo, nota=nota, creato_da=u["id"])
            if chi != u["id"]:
                a_carico_di_altri.append(_("{cosa} a carico del {conto}", cosa=nome_prodotto(pr),
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
        with db():
            if verso == "dato":
                registra(u["id"], "trasferimento", importo, controparte_id=altro["id"],
                         gruppo=gruppo, nota=f"Soldi dati a {n_altro}{extra}", creato_da=u["id"])
                registra(altro["id"], "trasferimento", -importo, controparte_id=u["id"],
                         gruppo=gruppo, nota=f"Soldi ricevuti da {n_io}{extra}", creato_da=u["id"])
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
        if testo and not email:
            flash(_("Indirizzo email non valido."), "errore")
            return redirect(url_for("profilo"))
        with db():
            db().execute("UPDATE persone SET email=?, avvisi_email=? WHERE id=?",
                         (email, 1 if request.form.get("avvisi_email") else 0, u["id"]))
        flash(_("Profilo aggiornato."), "ok")
        return redirect(url_for("home"))
    return render_template("profilo.html", email_attiva=email_configurata())


@app.route("/spesa", methods=["GET", "POST"])
@login_richiesto
def spesa():
    if request.method == "POST":
        importo = leggi_euro(request.form.get("importo"))
        nota = request.form.get("nota", "").strip()[:200]
        if importo is None or not nota:
            flash(_("Inserisci l'importo e cosa hai comprato."), "errore")
            return render_template("spesa.html", form=request.form,
                                   nonce=secrets.token_urlsafe(8))
        if nonce_gia_usato(request.form.get("nonce")):
            return redirect(url_for("home"))
        with db():
            registra(g.utente["id"], "spesa", importo, nota=f"Spesa per il gruppo: {nota}",
                     creato_da=g.utente["id"])
        flash(_("Spesa registrata. Nuovo saldo: {saldo}", saldo=euro(saldo(g.utente['id']))), "ok")
        return redirect(url_for("home"))
    return render_template("spesa.html", form={}, nonce=secrets.token_urlsafe(8))


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
    """messaggi = [(destinatario, oggetto, corpo)]. Ritorna (inviati, errori)."""
    if not messaggi:
        return 0, []
    inviati, errori = 0, []
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        for dest, oggetto, corpo in messaggi:
            msg = EmailMessage()
            msg["From"] = f"{NOME_APP} <{SMTP_USER}>"
            msg["To"] = dest
            msg["Subject"] = oggetto
            msg.set_content(corpo)
            try:
                server.send_message(msg)
                inviati += 1
            except smtplib.SMTPException as e:
                errori.append(f"{dest}: {e}")
    return inviati, errori


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
    in_negativo = [p for p in saldi_persone(con) if p["saldo"] < 0]
    cred = creditori(con, 3)
    messaggi = [(p["email"], *testo_email_avviso(p, cred, indirizzo))
                for p in in_negativo if p["email"] and p["avvisi_email"]]
    esito = {"quando": adesso(), "settimana": settimana, "in_negativo": len(in_negativo),
             "con_email": len(messaggi), "inviati": 0, "errori": []}
    try:
        esito["inviati"], esito["errori"] = spedisci(messaggi)
    except Exception as e:   # credenziali sbagliate, rete, …
        esito["errori"] = [f"{type(e).__name__}: {e}"]
    with con:
        con.execute("UPDATE impostazioni SET valore=? WHERE chiave='avviso_esito'",
                    (json.dumps(esito, ensure_ascii=False),))
    return esito


def _avvisi_in_sottofondo(indirizzo):
    con = connetti()
    try:
        invia_avvisi(con, indirizzo)
    except Exception:
        app.logger.exception("Invio avvisi del lunedì non riuscito")
    finally:
        con.close()


@app.after_request
def avvisi_automatici(risposta):
    """Senza attività pianificate: il primo accesso dopo lunedì alle 8 fa partire le email,
    dopo aver già risposto all'utente (così non deve aspettare)."""
    try:
        if email_configurata() and request.endpoint not in (None, "static"):
            r = db().execute("SELECT valore FROM impostazioni WHERE chiave='avviso_settimana'").fetchone()
            if r and r["valore"] != settimana_corrente():
                indirizzo = os.environ.get("CAFFE_URL") or url_for("home", _external=True)
                risposta.call_on_close(lambda: _avvisi_in_sottofondo(indirizzo))
    except Exception:
        app.logger.exception("Controllo avvisi non riuscito")
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

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nome_file = f"caffe_{datetime.now(TZ):%Y-%m-%d}.xlsx"
    return send_file(buf, as_attachment=True, download_name=nome_file,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/qr")
@login_richiesto
def qr():
    import segno
    indirizzo = os.environ.get("CAFFE_URL") or url_for("home", _external=True)
    svg = segno.make(indirizzo, error="m").svg_inline(scale=12, border=2, dark="#2b1d14")
    return render_template("qr.html", svg=svg, indirizzo=indirizzo, prodotti=prodotti())


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
    return render_template("admin.html", righe=righe, prodotti=prodotti(solo_attivi=False),
                           conti=[r for r in righe if r["speciale"]], esito=esito,
                           email_attiva=email_configurata(), smtp_user=SMTP_USER,
                           n_negativo=len(persone_neg),
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


def _leggi_prodotto_da_form():
    nome = request.form.get("nome", "").strip()[:40]
    emoji = request.form.get("emoji", "").strip()[:4]
    prezzo = leggi_euro(request.form.get("prezzo"))
    addebito = request.form.get("addebito_id", type=int) or None
    if addebito:
        conto = persona(addebito)
        if not conto or not conto["speciale"]:
            addebito = None
    return nome, emoji, prezzo, addebito


@app.post("/admin/prodotto/<int:prid>")
@admin_richiesto
def admin_prodotto(prid):
    pr = prodotto(prid) or abort(404)
    nome, emoji, prezzo, addebito = _leggi_prodotto_da_form()
    if not nome or prezzo is None:
        flash(_("Servono un nome e un prezzo valido."), "errore")
        return redirect(url_for("admin"))
    attivo = 1 if request.form.get("attivo") else 0
    with db():
        db().execute("UPDATE prodotti SET nome=?, emoji=?, prezzo_cent=?, addebito_id=?, attivo=?"
                     " WHERE id=?", (nome, emoji, prezzo, addebito, attivo, prid))
    flash(_("{nome} aggiornato. Il prezzo vale per gli acquisti da ora in poi.", nome=nome), "ok")
    return redirect(url_for("admin"))


@app.post("/admin/prodotto/nuovo")
@admin_richiesto
def admin_prodotto_nuovo():
    nome, emoji, prezzo, addebito = _leggi_prodotto_da_form()
    if not nome or prezzo is None:
        flash(_("Servono un nome e un prezzo valido."), "errore")
        return redirect(url_for("admin"))
    ordine = (db().execute("SELECT MAX(ordine) AS m FROM prodotti").fetchone()["m"] or 0) + 1
    with db():
        db().execute("INSERT INTO prodotti (nome, emoji, prezzo_cent, addebito_id, ordine) "
                     "VALUES (?,?,?,?,?)", (nome, emoji, prezzo, addebito, ordine))
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
            registra(p["id"], "acquisto", -qta * pr["prezzo_cent"], qta=qta, prodotto_id=pr["id"],
                     creato_da=g.utente["id"])
        flash(_("Segnato {cosa} a {nome}.", cosa=etichetta_prodotto(pr, qta), nome=nome_completo(p)), "ok")
    return redirect(url_for("admin"))


@app.get("/admin/backup")
@admin_richiesto
def admin_backup():
    """Scarica una copia completa del database (da conservare ogni tanto)."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    dest = sqlite3.connect(tmp.name)
    db().backup(dest)
    dest.close()
    with open(tmp.name, "rb") as f:
        dati = f.read()
    os.unlink(tmp.name)
    return send_file(io.BytesIO(dati), as_attachment=True,
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


if __name__ == "__main__":
    # Solo per provarla sul tuo PC: python3 app.py  ->  http://localhost:5000
    app.run(host="0.0.0.0", port=5000, debug=False)
