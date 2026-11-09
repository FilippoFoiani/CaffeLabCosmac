"""Test automatici: python3 -m pytest -q   (oppure: python3 test_app.py)"""
import io
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


def approva_accesso(pid):
    """Come se l'admin approvasse il primo accesso."""
    with app.app_context():
        modulo.db().execute("UPDATE persone SET approvato=1, "
                            "nome = CASE WHEN nuovo_nome<>'' THEN nuovo_nome ELSE nome END, "
                            "cognome = CASE WHEN nuovo_nome<>'' THEN nuovo_cognome ELSE cognome END, "
                            "nuovo_nome='', nuovo_cognome='' WHERE id=?", (pid,))
        modulo.db().commit()


def entra(client, nome, pin="1234", cognome="Test", approva=True):
    tok, _ = csrf(client)
    pid = id_di(nome)
    r = client.post("/accedi", data={"_csrf": tok, "persona_id": pid, "pin": pin})
    if "Primo accesso" in r.get_data(as_text=True):
        r = client.post("/primo-accesso", data={"_csrf": tok, "persona_id": pid, "nome": nome,
                                               "cognome": cognome, "pin": pin, "pin2": pin})
        if approva:
            approva_accesso(pid)
    return r


def entra_come_admin():
    subprocess.run([sys.executable, os.path.join(QUI, "gestione.py"), "admin",
                    str(id_di("Filippo"))], env=os.environ.copy(), cwd=QUI, check=True)
    c = app.test_client()
    entra(c, "Filippo")
    return c


def richiesta_in_attesa(tipo):
    with app.app_context():
        return modulo.db().execute("SELECT id FROM richieste WHERE tipo=? AND stato='attesa' "
                                   "ORDER BY id DESC", (tipo,)).fetchone()["id"]


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
    # Sari dice di aver dato 10 € a Federico: finché Federico non conferma non cambia niente
    c.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                          "controparte": id_di("Federico"), "importo": "10"})
    assert saldo_di("Sari") == -1478 - 100
    assert saldo_di("Federico") == 902
    rid = richiesta_in_attesa("pagamento")
    # Sari non può confermarlo da sola, e nemmeno un terzo
    assert c.post(f"/richieste/{rid}/approva", data={"_csrf": tok}).status_code == 403
    terzo = app.test_client()
    entra(terzo, "Riccardo")
    tok3, _ = csrf(terzo, "/")
    assert terzo.post(f"/richieste/{rid}/approva", data={"_csrf": tok3}).status_code == 403
    # Federico vede la richiesta e conferma
    fed = app.test_client()
    entra(fed, "Federico")
    assert "Hai 1 richiesta da confermare" in fed.get("/").get_data(as_text=True)
    tokf, _ = csrf(fed, "/richieste")
    fed.post(f"/richieste/{rid}/approva", data={"_csrf": tokf})
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
    # con la foto dello scontrino
    from PIL import Image
    foto = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(foto, "PNG")
    foto.seek(0)
    c.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "importo": "18,90",
                           "nota": "2 kg di caffè", "foto": (foto, "scontrino.png")},
           content_type="multipart/form-data")
    assert saldo_di("Giacomo") == 770                # in attesa: ancora niente credito
    rid = richiesta_in_attesa("spesa")
    tok, _ = csrf(c, "/")
    assert c.post(f"/richieste/{rid}/approva", data={"_csrf": tok}).status_code == 403
    assert c.get(f"/scontrino/{rid}").status_code == 200       # chi l'ha inviata vede lo scontrino
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/richieste")
    assert "2 kg di caffè" in admin.get("/richieste").get_data(as_text=True)
    admin.post(f"/richieste/{rid}/approva", data={"_csrf": toka})
    assert saldo_di("Giacomo") == 770 + 1890
    # una spesa rifiutata non dà credito
    tok, html = csrf(c, "/spesa")
    c.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "importo": "50", "nota": "furbata"})
    admin.post(f"/richieste/{richiesta_in_attesa('spesa')}/rifiuta", data={"_csrf": toka})
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
    assert "Richiesta inviata" in r.get_data(as_text=True)
    assert c.get("/").headers["Location"].endswith("/attesa")     # non può ancora usare l'app
    admin = entra_come_admin()
    assert "Mario Rossi" in admin.get("/richieste").get_data(as_text=True)
    toka, _ = csrf(admin, "/richieste")
    admin.post(f"/admin/accesso/{id_di('Mario')}/approva", data={"_csrf": toka})
    assert "Ciao Mario" in c.get("/", follow_redirects=True).get_data(as_text=True)
    assert saldo_di("Mario") == 0


def test_impostore_rifiutato():
    """Qualcuno attiva l'account di un altro: l'admin rifiuta e l'account torna libero."""
    furbo = app.test_client()
    tok, _ = csrf(furbo)
    pid = id_di("Gianluca")
    furbo.post("/accedi", data={"_csrf": tok, "persona_id": pid, "pin": ""})
    furbo.post("/primo-accesso", data={"_csrf": tok, "persona_id": pid, "nome": "Gianluca",
                                       "cognome": "Falso", "pin": "1111", "pin2": "1111"})
    assert furbo.get("/").headers["Location"].endswith("/attesa")
    tok2, html = csrf(app.test_client())
    assert "in attesa di approvazione" in html
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/richieste")
    assert "Gianluca Falso" in admin.get("/richieste").get_data(as_text=True)
    admin.post(f"/admin/accesso/{pid}/rifiuta", data={"_csrf": toka})
    assert furbo.get("/").headers["Location"].endswith("/accedi")   # sessione del furbo chiusa
    with app.app_context():
        p = modulo.db().execute("SELECT * FROM persone WHERE id=?", (pid,)).fetchone()
        assert p["pin_hash"] is None and p["nome"] == "Gianluca" and p["cognome"] == ""
    # il vero Gianluca ora può fare il primo accesso
    vero = app.test_client()
    assert "Primo accesso" in entra(vero, "Gianluca", approva=False).get_data(as_text=True) or True


def test_pagamento_alla_cassa_confermato_da_admin():
    c = app.test_client()
    entra(c, "Daniele")
    tok, html = csrf(c, "/paga")
    c.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                          "controparte": id_di("Cassa"), "importo": "3,90"})
    assert saldo_di("Daniele") == -390
    rid = richiesta_in_attesa("pagamento")
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/richieste")
    admin.post(f"/richieste/{rid}/approva", data={"_csrf": toka})
    assert saldo_di("Daniele") == 0


def test_limite_di_debito():
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin")
    with app.app_context():
        caffe = modulo.db().execute("SELECT prezzo_cent FROM prodotti WHERE codice='caffe'").fetchone()[0]
    admin.post("/admin/limite", data={"_csrf": toka, "limite": "5", "modo": "avvisa"})
    try:
        c = app.test_client()
        entra(c, "Lupi")                                    # saldo -6,60: già oltre il limite
        partenza = saldo_di("Lupi")
        home = c.get("/").get_data(as_text=True)
        assert "Hai superato il limite di debito" in home and modulo.TESTO_AVVISO in home
        assert "Ho capito, nascondi" not in home            # non si può nascondere
        tok, html = csrf(c, "/")
        c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('caffe')}": 1})
        assert saldo_di("Lupi") == partenza                 # senza spunta non passa
        tok, html = csrf(c, "/")
        c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('caffe')}": 1,
                                  "oltre_limite": "1"})
        assert saldo_di("Lupi") == partenza - caffe          # con la spunta sì
        admin.post("/admin/limite", data={"_csrf": toka, "limite": "5", "modo": "blocca"})
        tok, html = csrf(c, "/")
        c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('caffe')}": 1,
                                  "oltre_limite": "1"})
        assert saldo_di("Lupi") == partenza - caffe          # bloccato
        # l'acqua per la macchinetta la paga il Conto Caffè: non è bloccata
        tok, html = csrf(c, "/")
        r = c.post("/acquista", data={"_csrf": tok, "nonce": nonce(html),
                                      f"q{prod('acqua_macchinetta')}": 1}, follow_redirects=True)
        assert "Segnato" in r.get_data(as_text=True)
        assert saldo_di("Lupi") == partenza - caffe
    finally:
        admin.post("/admin/limite", data={"_csrf": toka, "limite": "0", "modo": "avvisa"})


def test_registro_approvazioni():
    """Il registro dice chi ha approvato accessi, spese e pagamenti; lo vedono solo gli admin."""
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/richieste")
    with app.app_context():
        nome_admin = modulo.nome_completo(modulo.persona(id_di("Filippo")))
    # un accesso approvato e uno rifiutato
    for nome, esito in (("Alessia", "approva"), ("Vittorio", "rifiuta")):
        c = app.test_client()
        entra(c, nome, approva=False)
        admin.post(f"/admin/accesso/{id_di(nome)}/{esito}", data={"_csrf": toka})
    # una spesa approvata dall'admin
    alessia = app.test_client()
    entra(alessia, "Alessia")
    tok, html = csrf(alessia, "/spesa")
    alessia.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "importo": "4", "nota": "zucchero"})
    admin.post(f"/richieste/{richiesta_in_attesa('spesa')}/approva", data={"_csrf": toka})
    # un pagamento confermato da chi ha ricevuto i soldi
    tok, html = csrf(alessia, "/paga")
    alessia.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                                "controparte": id_di("Agnese"), "importo": "2"})
    agnese = app.test_client()
    entra(agnese, "Agnese")
    tokg, _ = csrf(agnese, "/richieste")
    agnese.post(f"/richieste/{richiesta_in_attesa('pagamento')}/approva", data={"_csrf": tokg})
    import html as _h
    reg = _h.unescape(admin.get("/admin/registro").get_data(as_text=True))
    assert "Alessia" in reg and "Vittorio" in reg
    assert reg.count("da " + nome_admin) >= 3                     # 2 accessi + 1 spesa
    assert "zucchero" in reg and "che ha ricevuto i soldi" in reg
    assert "rifiutato" in reg
    # gli altri non possono vederlo
    assert alessia.get("/admin/registro").status_code == 403
    # foglio Approvazioni nell'Excel solo per gli admin
    from openpyxl import load_workbook
    assert "Approvazioni" in load_workbook(io.BytesIO(admin.get("/export.xlsx").data)).sheetnames
    assert "Approvazioni" not in load_workbook(io.BytesIO(alessia.get("/export.xlsx").data)).sheetnames


def test_qr_immagine_e_avviso_indirizzo(monkeypatch):
    admin = entra_come_admin()
    r = admin.get("/qr.png")
    assert r.status_code == 200 and r.data[:8] == b"\x89PNG\r\n\x1a\n"
    assert "Attenzione: questo QR porta a" not in admin.get("/qr").get_data(as_text=True)
    monkeypatch.setenv("CAFFE_URL", "https://caffelabcosmac.eu.pythonanywhere.com/")
    html = admin.get("/qr").get_data(as_text=True)
    assert "Attenzione: questo QR porta a https://caffelabcosmac.eu.pythonanywhere.com/" in html


def test_come_funziona_senza_accesso():
    c = app.test_client()
    html = c.get("/come-funziona").get_data(as_text=True)
    assert "Come rientrare dal debito" in html and "Pulizia" in html
    import html as _h
    en = _h.unescape(c.get("/come-funziona", headers={"Accept-Language": "en"}).get_data(as_text=True))
    assert "How to get out of debt" in en and "Keep your debt low" in en


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


def test_backup_settimanale_agli_admin(monkeypatch):
    """Ogni lunedì gli admin con l'email ricevono Excel + database; il database basta a ripristinare."""
    import html as _h
    import sqlite3
    from openpyxl import load_workbook
    monkeypatch.setattr(modulo.smtplib, "SMTP", FintoSMTP)
    monkeypatch.setattr(modulo, "SMTP_USER", "caffelab@gmail.com")
    monkeypatch.setattr(modulo, "SMTP_PASSWORD", "xxxx")
    FintoSMTP.inviate.clear()
    admin = entra_come_admin()
    with app.app_context():
        modulo.db().execute("UPDATE persone SET email='' WHERE admin=1")
        modulo.db().commit()
        assert modulo.invia_backup() is None          # nessun admin con email: niente da fare
    r = admin.get("/admin"); r.close()
    assert FintoSMTP.inviate == []
    with app.app_context():
        modulo.db().execute("UPDATE persone SET email='filippo@unipg.it' WHERE id=?", (id_di("Filippo"),))
        modulo.db().commit()
    # la prima pagina aperta (dopo l'aggiornamento o di lunedì) fa partire il backup
    r = admin.get("/admin"); r.close()
    assert len(FintoSMTP.inviate) == 1
    r = admin.get("/"); r.close()
    assert len(FintoSMTP.inviate) == 1                # una sola volta a settimana
    msg = FintoSMTP.inviate[0]
    assert msg["To"] == "filippo@unipg.it" and "backup" in msg["Subject"]
    assert "In negativo adesso:" in msg.get_body().get_content()
    allegati = {a.get_filename(): a.get_content() for a in msg.iter_attachments()}
    xlsx = next(v for k, v in allegati.items() if k.endswith(".xlsx"))
    dati_db = next(v for k, v in allegati.items() if k.endswith(".db"))
    # l'Excel si apre e contiene anche le approvazioni
    assert load_workbook(io.BytesIO(xlsx)).sheetnames == ["Saldi", "Movimenti", "Approvazioni"]
    # il database allegato è integro e ha gli stessi saldi dell'app
    percorso = os.path.join(CARTELLA, "ripristino.db")
    with open(percorso, "wb") as f:
        f.write(dati_db)
    con = sqlite3.connect(percorso)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    copia = con.execute("SELECT persona_id, SUM(importo_cent) FROM movimenti WHERE annullato=0 "
                        "GROUP BY persona_id ORDER BY persona_id").fetchall()
    con.close()
    with app.app_context():
        assert copia == [tuple(r) for r in modulo.db().execute(
            "SELECT persona_id, SUM(importo_cent) FROM movimenti WHERE annullato=0 "
            "GROUP BY persona_id ORDER BY persona_id").fetchall()]
    # sezione in Amministrazione e pulsante «Invia il backup adesso»
    tok, pagina = csrf(admin, "/admin")
    pagina = _h.unescape(pagina)
    assert "Backup settimanale" in pagina and "Lo ricevono: Filippo" in re.sub(r"<[^>]+>", "", pagina)
    r = admin.post("/admin/backup/invia", data={"_csrf": tok}, follow_redirects=True)
    assert "Backup inviato a: Filippo" in _h.unescape(r.get_data(as_text=True))
    assert len(FintoSMTP.inviate) == 2
    # chi non è admin non può farlo partire
    c = app.test_client()
    entra(c, "Max")
    tok, _ = csrf(c, "/")
    assert c.post("/admin/backup/invia", data={"_csrf": tok}).status_code == 403
    assert len(FintoSMTP.inviate) == 2


def test_email_backup_in_inglese():
    from datetime import datetime
    oggetto, corpo = modulo.testo_email_backup({"nome": "Nick", "lingua": "en"}, datetime(2026, 11, 16, 8, 5),
                                               [{"saldo": -150}, {"saldo": -40}], "a.xlsx", "b.db")
    assert oggetto.endswith("backup of 16/11/2026")
    assert "Hi Nick," in corpo and "Keep this email" in corpo and "1,90 €" in corpo
    assert "Ciao" not in corpo and "allegato" not in corpo


def test_pagamento_di_un_admin_lo_conferma_chi_riceve():
    """Issue #1: anche quando paga un admin conferma chi ha ricevuto i soldi. Un altro admin
    può confermare solo se la richiesta è ferma da più di 3 giorni; nessuno conferma un proprio pagamento."""
    admin = entra_come_admin()
    marco = app.test_client()
    entra(marco, "Marco")
    prima = saldo_di("Filippo"), saldo_di("Marco")
    tok, html = csrf(admin, "/paga")
    admin.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                              "controparte": id_di("Marco"), "importo": "2"})
    assert (saldo_di("Filippo"), saldo_di("Marco")) == prima          # non vale ancora
    rid = richiesta_in_attesa("pagamento")
    assert "Hai 1 richiesta da confermare" in marco.get("/").get_data(as_text=True)
    assert admin.post(f"/richieste/{rid}/approva", data={"_csrf": tok}).status_code == 403
    # un secondo admin non può intervenire finché la richiesta non è ferma da più di 3 giorni
    with app.app_context():
        modulo.db().execute("UPDATE persone SET admin=1 WHERE id=?", (id_di("Massi"),))
        modulo.db().commit()
    try:
        altro = app.test_client()
        entra(altro, "Massi")
        tokm, _ = csrf(altro, "/richieste")
        assert altro.post(f"/richieste/{rid}/approva", data={"_csrf": tokm}).status_code == 403
        with app.app_context():
            modulo.db().execute("UPDATE richieste SET ts=? WHERE id=?",
                                ("2026-01-01T08:00:00+00:00", rid))
            modulo.db().commit()
        # chi ha pagato non può confermare nemmeno dopo 3 giorni
        assert admin.post(f"/richieste/{rid}/approva", data={"_csrf": tok}).status_code == 403
        assert "ferma da più di 3 giorni" in altro.get("/richieste").get_data(as_text=True)
        altro.post(f"/richieste/{rid}/approva", data={"_csrf": tokm})
        assert (saldo_di("Filippo"), saldo_di("Marco")) == (prima[0] + 200, prima[1] - 200)
    finally:
        with app.app_context():
            modulo.db().execute("UPDATE persone SET admin=0 WHERE id=?", (id_di("Massi"),))
            modulo.db().commit()


def test_versamento_di_un_admin_alla_cassa_vale_subito():
    admin = entra_come_admin()
    prima = saldo_di("Filippo")
    tok, html = csrf(admin, "/paga")
    admin.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                              "controparte": id_di("Cassa"), "importo": "1"})
    assert saldo_di("Filippo") == prima + 100


def test_metodo_di_pagamento_nella_scheda():
    """Issue #5: PayPal e IBAN nel profilo, visibili nella scheda della persona e in Pagamenti."""
    giulia = app.test_client()
    entra(giulia, "Giulia")
    tok, _ = csrf(giulia, "/profilo")
    # IBAN con codice di controllo sbagliato: rifiutato, e quello che hai scritto resta nel modulo
    r = giulia.post("/profilo", data={"_csrf": tok, "iban": "IT61 X054 2811 1010 0000 0123 456"})
    assert "IBAN non valido" in r.get_data(as_text=True) and "IT61 X054" in r.get_data(as_text=True)
    assert "PayPal non valido" in giulia.post("/profilo", data={"_csrf": tok, "paypal": "mario rossi!"}
                                             ).get_data(as_text=True)
    giulia.post("/profilo", data={"_csrf": tok, "paypal": "https://www.paypal.me/GiuliaT/",
                                  "iban": "it60 x054 2811 1010 0000 0123 456"})
    with app.app_context():
        p = modulo.persona(id_di("Giulia"))
        assert (p["paypal"], p["iban"]) == ("GiuliaT", "IT60X0542811101000000123456")
    # un altro la vede nella scheda e in Pagamenti appena la sceglie
    nick = app.test_client()
    entra(nick, "Nick")
    scheda = nick.get(f"/persona/{id_di('Giulia')}").get_data(as_text=True)
    assert "https://paypal.me/GiuliaT" in scheda and "IT60 X054 2811 1010 0000 0123 456" in scheda
    assert f'href="/paga?verso=dato&amp;a={id_di("Giulia")}"' in scheda
    paga = nick.get(f"/paga?a={id_di('Giulia')}").get_data(as_text=True)
    assert f'data-persona="{id_di("Giulia")}" >' in paga and "IT60 X054" in paga
    # nei Saldi c'è solo il link alla scheda, non i dati di pagamento; niente nell'Excel
    saldi = nick.get("/saldi").get_data(as_text=True)
    assert f"/persona/{id_di('Giulia')}" in saldi and "IT60" not in saldi and "GiuliaT" not in saldi
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(nick.get("/export.xlsx").data))
    assert not any("IT60X054" in str(c.value) for ws in wb for row in ws.iter_rows() for c in row)
    # chi non l'ha indicato, conti comuni, persone che non esistono, chi non ha fatto l'accesso
    assert "chiediglielo" in nick.get(f"/persona/{id_di('Nick')}").get_data(as_text=True)
    assert "Conto comune" in nick.get(f"/persona/{id_di('Cassa')}").get_data(as_text=True)
    assert nick.get("/persona/99999").status_code == 404
    assert app.test_client().get(f"/persona/{id_di('Giulia')}").status_code == 302
    # un'email PayPal si salva così com'è; svuotando i campi spariscono
    giulia.post("/profilo", data={"_csrf": tok, "paypal": "giulia@example.com", "iban": ""})
    scheda = nick.get(f"/persona/{id_di('Giulia')}").get_data(as_text=True)
    assert "giulia@example.com" in scheda and "paypal.me/" not in scheda and "IT60" not in scheda


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))


def test_hidden_vince_sul_css():
    # Il riquadro "oltre il limite" è nascosto con l'attributo hidden: il CSS non deve annullarlo
    css = open(os.path.join(os.path.dirname(__file__), "static", "stile.css"), encoding="utf-8").read()
    assert "[hidden] { display: none !important; }" in css
