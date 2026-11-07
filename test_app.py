"""Test automatici: python3 -m pytest -q   (oppure: python3 test_app.py)"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

CARTELLA = tempfile.mkdtemp(prefix="caffe_test_")
os.environ["CAFFE_DATA_DIR"] = CARTELLA
QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)

import app as modulo  # noqa: E402

app = modulo.app


def csrf(client, url="/accedi"):
    html = client.get(url).get_data(as_text=True)
    m = re.search(r'name="_csrf" value="([^"]+)"', html)
    return m.group(1), html


def nonce(html):
    return re.search(r'name="nonce" value="([^"]+)"', html).group(1)


def id_di(nome):
    with app.app_context():
        return modulo.db().execute("SELECT id FROM persone WHERE nome=?", (nome,)).fetchone()["id"]


def prod(codice):
    with app.app_context():
        return modulo.db().execute("SELECT id FROM prodotti WHERE codice=?", (codice,)).fetchone()["id"]


def saldo_di(nome):
    with app.app_context():
        return modulo.saldo(id_di(nome))


def entra(client, nome, pin="1234", cognome="Test"):
    tok, _ = csrf(client)
    pid = id_di(nome)
    r = client.post("/accedi", data={"_csrf": tok, "persona_id": pid, "pin": pin})
    if "Primo accesso" in r.get_data(as_text=True):
        r = client.post("/primo-accesso", data={"_csrf": tok, "persona_id": pid, "nome": nome,
                                               "cognome": cognome, "pin": pin, "pin2": pin})
    return r


def setup_module(_):
    out = subprocess.run([sys.executable, os.path.join(QUI, "gestione.py"), "importa",
                          os.path.join(QUI, "saldi_iniziali.csv")],
                         capture_output=True, text=True, env=os.environ.copy(), cwd=QUI)
    assert out.returncode == 0, out.stderr
    assert "26 aggiunti" in out.stdout


def teardown_module(_):
    shutil.rmtree(CARTELLA, ignore_errors=True)


def test_import_saldi():
    assert saldo_di("Massi") == -1014 - 150      # foglio caffè + foglio acqua
    assert saldo_di("Giulio") == -949 + 1729
    assert saldo_di("Cassa") == 300
    assert saldo_di("Gianluca") == 0
    assert saldo_di("Conto Caffè") == 0


def test_serve_login():
    c = app.test_client()
    r = c.get("/")
    assert r.status_code == 302 and "/accedi" in r.headers["Location"]


def test_csrf_obbligatorio():
    c = app.test_client()
    r = c.post("/accedi", data={"persona_id": 1, "pin": "1234"})
    assert r.status_code == 400


def test_acquisto_multiplo_e_annulla():
    c = app.test_client()
    entra(c, "Agnese")
    home = c.get("/").get_data(as_text=True)
    assert "Ciao Agnese" in home and "+7,16 €" in home
    tok = re.search(r'name="_csrf" value="([^"]+)"', home).group(1)
    dati = {"_csrf": tok, "nonce": nonce(home), f"q{prod('caffe')}": 2,
            f"q{prod('acqua')}": 1, f"q{prod('acqua_macchinetta')}": 1}
    r = c.post("/acquista", data=dati, follow_redirects=True)
    assert "Caffè × 2" in r.get_data(as_text=True)
    # caffè e acqua a carico di Agnese, l'acqua per la macchinetta sul Conto Caffè
    assert saldo_di("Agnese") == 716 - 60 - 25
    assert saldo_di("Conto Caffè") == -25
    # stesso modulo inviato due volte: non deve contare doppio
    c.post("/acquista", data=dati)
    assert saldo_di("Agnese") == 716 - 85
    # annulla: si annulla tutto l'acquisto, anche la parte sul Conto Caffè
    home = c.get("/").get_data(as_text=True)
    mid = re.search(r'action="/annulla/(\d+)"', home).group(1)
    c.post(f"/annulla/{mid}", data={"_csrf": tok})
    assert saldo_di("Agnese") == 716
    assert saldo_di("Conto Caffè") == 0


def test_acquisto_vuoto_rifiutato():
    c = app.test_client()
    entra(c, "Riccardo")
    tok, html = csrf(c, "/")
    r = c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html)}, follow_redirects=True)
    assert "almeno un prodotto" in r.get_data(as_text=True)
    assert saldo_di("Riccardo") == -26


def test_pin_sbagliato_e_blocco():
    c = app.test_client()
    entra(c, "Giulio", pin="4321")
    c2 = app.test_client()
    for _ in range(5):
        tok, _ = csrf(c2)
        c2.post("/accedi", data={"_csrf": tok, "persona_id": id_di("Giulio"), "pin": "0000"})
    tok, _ = csrf(c2)
    r = c2.post("/accedi", data={"_csrf": tok, "persona_id": id_di("Giulio"), "pin": "4321"},
                follow_redirects=True)
    assert "Troppi tentativi" in r.get_data(as_text=True)


def test_trasferimenti():
    c = app.test_client()
    entra(c, "Sari")
    tok, html = csrf(c, "/paga")
    # Sari dà 10 € a Federico (in credito)
    c.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                          "controparte": id_di("Federico"), "importo": "10"})
    assert saldo_di("Sari") == -1478 - 100 + 1000   # caffè + acqua + pagamento
    assert saldo_di("Federico") == 902 - 1000
    # Sari si accolla 1,98 € del debito di Alessia
    tok, html = csrf(c, "/paga")
    c.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "accollo",
                          "controparte": id_di("Alessia"), "importo": "1,98"})
    assert saldo_di("Alessia") == 0
    assert saldo_di("Sari") == -578 - 198
    mov = c.get("/movimenti").get_data(as_text=True)
    assert "Soldi dati a Federico" in mov and "debito di Alessia" in mov


def test_spesa():
    c = app.test_client()
    entra(c, "Giacomo")
    tok, html = csrf(c, "/spesa")
    c.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "importo": "18,90",
                           "nota": "2 kg di caffè"})
    assert saldo_di("Giacomo") == 770 + 1890


def test_non_admin_bloccato():
    c = app.test_client()
    entra(c, "Max")
    assert c.get("/admin").status_code == 403


def test_admin_export_qr():
    subprocess.run([sys.executable, os.path.join(QUI, "gestione.py"), "admin",
                    str(id_di("Filippo"))], env=os.environ.copy(), cwd=QUI, check=True)
    c = app.test_client()
    entra(c, "Filippo")
    assert c.get("/admin").status_code == 200
    tok, _ = csrf(c, "/admin")
    c.post("/admin/rettifica", data={"_csrf": tok, "persona_id": id_di("Max"),
                                     "importo": "4,42", "nota": "versati in contanti"})
    assert saldo_di("Max") == 0
    c.post("/admin/acquisto-per", data={"_csrf": tok, "persona_id": id_di("Cassa"),
                                        "prodotto_id": prod("caffe"), "qta": 3})
    assert saldo_di("Cassa") == 300 - 90
    c.post(f"/admin/prodotto/{prod('caffe')}", data={"_csrf": tok, "nome": "Caffè", "emoji": "☕",
                                                     "prezzo": "0,35", "attivo": "1"})
    c.post("/admin/prodotto/nuovo", data={"_csrf": tok, "nome": "Tè", "emoji": "🍵", "prezzo": "0,20"})
    with app.app_context():
        prezzi = {p["nome"]: p["prezzo_cent"] for p in modulo.db().execute("SELECT * FROM prodotti")}
    assert prezzi["Caffè"] == 35 and prezzi["Tè"] == 20
    assert "Tè" in c.get("/").get_data(as_text=True)
    r = c.get("/export.xlsx")
    assert r.status_code == 200 and r.data[:2] == b"PK"
    import io
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(r.data))
    intestazione = [x.value for x in wb["Saldi"][1]]
    assert "Acqua (n°)" in intestazione and "Acqua macchinetta (n°)" in intestazione
    r = c.get("/qr")
    assert r.status_code == 200 and "<svg" in r.get_data(as_text=True)
    r = c.get("/admin/backup")
    assert r.status_code == 200 and r.data[:15] == b"SQLite format 3"
    assert c.get("/saldi").status_code == 200


def test_registrazione_nuova_persona():
    c = app.test_client()
    tok, _ = csrf(c, "/registrati")
    r = c.post("/registrati", data={"_csrf": tok, "nome": "Mario", "cognome": "Rossi",
                                    "pin": "2468", "pin2": "2468"}, follow_redirects=True)
    assert "Ciao Mario" in r.get_data(as_text=True)
    assert saldo_di("Mario") == 0


class FintoSMTP:
    """Sostituisce il server Gmail nei test: registra le email invece di spedirle."""
    inviate = []

    def __init__(self, host, port, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, utente, password):
        assert utente and password

    def send_message(self, msg):
        FintoSMTP.inviate.append(msg)


def test_avviso_lunedi_in_app():
    c = app.test_client()
    entra(c, "Lupi")                      # saldo -6,60
    home = c.get("/").get_data(as_text=True)
    assert modulo.TESTO_AVVISO in home
    assert "Salda il debito" in home and "Compra uno dei beni" in home
    tok = re.search(r'name="_csrf" value="([^"]+)"', home).group(1)
    c.post("/avviso/letto", data={"_csrf": tok})
    assert modulo.TESTO_AVVISO not in c.get("/").get_data(as_text=True)
    # chi è in positivo non lo vede
    c2 = app.test_client()
    entra(c2, "Agnese")
    assert modulo.TESTO_AVVISO not in c2.get("/").get_data(as_text=True)


def test_link_salda_debito_precompila():
    c = app.test_client()
    entra(c, "Daniele")
    html = c.get("/paga?verso=dato&importo=3,90&a=" + str(id_di("Cassa"))).get_data(as_text=True)
    assert 'value="3,90"' in html
    assert re.search(r'<option value="%d"[^>]*\n?\s*selected' % id_di("Cassa"), html)


def test_email_del_lunedi(monkeypatch):
    monkeypatch.setattr(modulo.smtplib, "SMTP", FintoSMTP)
    monkeypatch.setattr(modulo, "SMTP_USER", "caffelab@gmail.com")
    monkeypatch.setattr(modulo, "SMTP_PASSWORD", "xxxx")
    FintoSMTP.inviate.clear()
    c = app.test_client()
    entra(c, "Lorenzo")                   # saldo -1,50
    tok, _ = csrf(c, "/profilo")
    c.post("/profilo", data={"_csrf": tok, "email": "lorenzo@studenti.unipg.it", "avvisi_email": "1"})
    entra(app.test_client(), "Vittorio")  # in positivo: non deve ricevere nulla
    with app.app_context():
        modulo.db().execute("UPDATE persone SET email='vittorio@unipg.it' WHERE nome='Vittorio'")
        modulo.db().commit()
        con = modulo.connetti()
        # la settimana corrente è già "presa" all'installazione: non parte nulla
        assert modulo.invia_avvisi(con, "https://caffelab.eu.pythonanywhere.com/") is None
        con.execute("UPDATE impostazioni SET valore='2000-W01' WHERE chiave='avviso_settimana'")
        con.commit()
        esito = modulo.invia_avvisi(con, "https://caffelab.eu.pythonanywhere.com/")
        assert esito["inviati"] == 1 and not esito["errori"]
        # una sola volta a settimana
        assert modulo.invia_avvisi(con, "https://caffelab.eu.pythonanywhere.com/") is None
        con.close()
    msg = FintoSMTP.inviate[0]
    assert msg["To"] == "lorenzo@studenti.unipg.it"
    corpo = msg.get_content()
    assert modulo.TESTO_AVVISO in corpo and "−1,50 €" in corpo
    assert "Filippo" in corpo             # tra chi è in credito


def test_email_partono_al_primo_accesso_del_lunedi(monkeypatch):
    """Senza attività pianificate: la prima pagina aperta nella nuova settimana fa partire le email."""
    monkeypatch.setattr(modulo.smtplib, "SMTP", FintoSMTP)
    monkeypatch.setattr(modulo, "SMTP_USER", "caffelab@gmail.com")
    monkeypatch.setattr(modulo, "SMTP_PASSWORD", "xxxx")
    FintoSMTP.inviate.clear()
    with app.app_context():
        modulo.db().execute("UPDATE impostazioni SET valore='2000-W02' WHERE chiave='avviso_settimana'")
        modulo.db().commit()
    c = app.test_client()
    r = c.get("/accedi")
    r.close()                              # l'invio parte dopo aver risposto
    assert len(FintoSMTP.inviate) == 1     # Lorenzo, l'unico in negativo con email
    r = c.get("/accedi"); r.close()
    assert len(FintoSMTP.inviate) == 1     # non riparte nella stessa settimana


def test_avvertenza_pulizia_dopo_il_caffe():
    c = app.test_client()
    entra(c, "Giacomo")
    tok, html = csrf(c, "/")
    r = c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('caffe')}": 1},
               follow_redirects=True)
    assert modulo.TESTO_PULIZIA in r.get_data(as_text=True)
    tok, html = csrf(c, "/")
    r = c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('acqua')}": 1},
               follow_redirects=True)
    assert modulo.TESTO_PULIZIA not in r.get_data(as_text=True)   # solo acqua: niente avvertenza


def test_manutenzione_solo_admin():
    with app.app_context():
        con = modulo.db()
        nomi = [r["nome"] for r in con.execute("SELECT nome FROM manutenzioni")]
        assert nomi == ["Pulizia della macchinetta", "Decalcificazione"]
        # la pulizia risulta fatta 10 giorni fa: è scaduta (ogni 7 giorni)
        con.execute("UPDATE manutenzioni SET ultima_ts=? WHERE nome='Pulizia della macchinetta'",
                    ((modulo.datetime.now(modulo.timezone.utc) - modulo.timedelta(days=10)).isoformat(),))
        con.commit()
        mid = con.execute("SELECT id FROM manutenzioni WHERE nome='Pulizia della macchinetta'").fetchone()["id"]
    admin = app.test_client()
    entra(admin, "Filippo")
    home = admin.get("/").get_data(as_text=True)
    assert "Manutenzione della macchinetta da fare" in home and "Pulizia della macchinetta" in home
    assert "Decalcificazione" not in home.split("avviso-manutenzione")[1].split("</section>")[0]
    normale = app.test_client()
    entra(normale, "Alessia")
    assert "Manutenzione della macchinetta da fare" not in normale.get("/").get_data(as_text=True)
    tok, _ = csrf(normale, "/")
    assert normale.post(f"/manutenzione/{mid}/fatta", data={"_csrf": tok}).status_code == 403
    tok, _ = csrf(admin, "/")
    admin.post(f"/manutenzione/{mid}/fatta", data={"_csrf": tok})
    assert "Manutenzione della macchinetta da fare" not in admin.get("/").get_data(as_text=True)
    # modifica dall'amministrazione: ogni 3 giorni, ultima volta 5 giorni fa -> di nuovo da fare
    tok, _ = csrf(admin, "/admin")
    cinque = (modulo.datetime.now(modulo.TZ) - modulo.timedelta(days=5)).date().isoformat()
    admin.post(f"/admin/manutenzione/{mid}", data={"_csrf": tok, "nome": "Pulizia della macchinetta",
                                                   "ogni_giorni": "3", "ultima": cinque, "attivo": "1"})
    assert "Manutenzione della macchinetta da fare" in admin.get("/").get_data(as_text=True)
    admin.post("/admin/manutenzione/nuova", data={"_csrf": tok, "nome": "Cambio filtro", "ogni_giorni": "60"})
    assert "Cambio filtro" in admin.get("/admin").get_data(as_text=True)


def test_inglese():
    c = app.test_client()
    entra(c, "Tamara")
    c.get("/lingua/en", headers={"Referer": "http://localhost/"})
    import html as _html
    home = _html.unescape(c.get("/").get_data(as_text=True))
    assert "Hi Tamara" in home and "Everyone's balances" in home and "Coffee" in home
    assert "SETTLE YOUR DEBT, BUY ANOTHER USER'S CREDIT OR BUY ONE OF THE GOODS" in home
    # la scelta resta salvata sul profilo anche da un altro telefono
    with app.app_context():
        assert modulo.db().execute("SELECT lingua FROM persone WHERE nome='Tamara'").fetchone()["lingua"] == "en"
    for pagina in ("/saldi", "/movimenti?tutti=1", "/paga", "/spesa", "/profilo", "/qr"):
        assert c.get(pagina).status_code == 200
    c.get("/lingua/it")
    assert "Ciao Tamara" in c.get("/").get_data(as_text=True)
    # pagina di accesso in inglese se il browser è in inglese
    nuovo = app.test_client()
    assert "Who are you?" in nuovo.get("/accedi", headers={"Accept-Language": "en-GB,en;q=0.9"}).get_data(as_text=True)


def test_email_in_inglese():
    with app.app_context():
        p = dict(modulo.db().execute("SELECT * FROM persone WHERE nome='Nick'").fetchone())
    p["saldo"], p["lingua"] = -1387, "en"
    oggetto, corpo = modulo.testo_email_avviso(p, [], "https://x/")
    assert "your balance is" in oggetto
    assert "SETTLE YOUR DEBT" in corpo and "Hi Nick," in corpo


def test_traduzioni_complete():
    """Ogni testo scritto dentro _("...") nelle pagine e nel codice deve avere la traduzione inglese."""
    import glob
    from lingue import EN
    pat = re.compile(r'''(?<![\w.])_\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')''')
    mancanti = set()
    for f in glob.glob(os.path.join(QUI, "templates", "*.html")) + [os.path.join(QUI, "app.py")]:
        for m in pat.finditer(open(f, encoding="utf-8").read()):
            testo = m.group(1) if m.group(1) is not None else m.group(2)
            if testo not in EN:
                mancanti.add(testo)
    assert not mancanti, mancanti


def test_cron_protetto():
    c = app.test_client()
    assert c.get("/cron/avvisi").status_code == 404
    assert c.get("/cron/avvisi?token=sbagliato").status_code == 404


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
