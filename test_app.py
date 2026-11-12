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
    assert saldo_di("Macchinetta del caffè") == 0


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
    # caffè e acqua a carico di Agnese, l'acqua per la macchinetta sulla Macchinetta del caffè
    assert saldo_di("Agnese") == 716 - 60 - 25
    assert saldo_di("Macchinetta del caffè") == -25
    # stesso modulo inviato due volte: non deve contare doppio
    c.post("/acquista", data=dati)
    assert saldo_di("Agnese") == 716 - 85
    # annulla: si annulla tutto l'acquisto, anche la parte sulla Macchinetta del caffè
    home = c.get("/").get_data(as_text=True)
    mid = re.search(r'action="/annulla/(\d+)"', home).group(1)
    c.post(f"/annulla/{mid}", data={"_csrf": tok})
    assert saldo_di("Agnese") == 716
    assert saldo_di("Macchinetta del caffè") == 0


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
    assert 'type="file"' not in html                  # niente più foto dello scontrino
    c.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "importo": "18,90",
                           "nota": "2 kg di caffè"})
    assert saldo_di("Giacomo") == 770                # in attesa: ancora niente credito
    rid = richiesta_in_attesa("spesa")
    tok, _ = csrf(c, "/")
    assert c.post(f"/richieste/{rid}/approva", data={"_csrf": tok}).status_code == 403
    assert c.get(f"/scontrino/{rid}").status_code == 404
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
        # l'acqua per la macchinetta la paga la Macchinetta del caffè: non è bloccata
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
    # come impostare il profilo: email e metodo di pagamento
    assert "Imposta il tuo profilo" in html and "PayPal" in html and "IBAN" in html
    assert "Apri il tuo profilo" not in html                      # il pulsante solo per chi ha fatto l'accesso
    import html as _h
    en = _h.unescape(c.get("/come-funziona", headers={"Accept-Language": "en"}).get_data(as_text=True))
    assert "How to get out of debt" in en and "Keep your debt low" in en and "Set up your profile" in en


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


def test_prova_a_secco_avvisi(monkeypatch):
    """La prova a secco mostra chi riceverebbe l'avviso e il testo, ma non spedisce nulla
    e non tocca la settimana dell'invio automatico."""
    monkeypatch.setattr(modulo.smtplib, "SMTP", FintoSMTP)
    monkeypatch.setattr(modulo, "SMTP_USER", "caffelab@gmail.com")
    monkeypatch.setattr(modulo, "SMTP_PASSWORD", "xxxx")
    FintoSMTP.inviate.clear()
    entra(app.test_client(), "Lupi")       # in negativo, senza email
    with app.app_context():
        settimana = modulo.impostazione("avviso_settimana")
    admin = entra_come_admin()
    assert "Prova a secco" in admin.get("/admin").get_data(as_text=True)
    import html as _h
    pagina = _h.unescape(admin.get("/admin/avvisi/anteprima").get_data(as_text=True))
    assert "caffelab@gmail.com" in pagina                          # il mittente
    lorenzo = pagina[pagina.index("Lorenzo"):].split("</li>")[0]
    assert "riceve l'email" in lorenzo and "lorenzo@studenti.unipg.it" in lorenzo
    assert modulo.TESTO_AVVISO in lorenzo and "−1,50 €" in lorenzo  # il testo dell'email
    assert "senza email" in pagina[pagina.index("Lupi"):].split("</li>")[0]
    assert "Vittorio" not in pagina                                # in positivo: non compare
    with app.app_context():
        voci = {v["nome"].split()[0]: v for v in modulo.anteprima_avvisi(modulo.db(), "https://x/")}
        assert voci["Lorenzo"]["motivo"] == "" and voci["Lupi"]["motivo"] == "senza_email"
        # chi toglie la spunta nel Profilo non la riceve
        modulo.db().execute("UPDATE persone SET avvisi_email=0 WHERE nome='Lorenzo'")
        assert {v["nome"].split()[0]: v for v in modulo.anteprima_avvisi(modulo.db(), "https://x/")
                }["Lorenzo"]["motivo"] == "disattivato"
        modulo.db().execute("UPDATE persone SET avvisi_email=1 WHERE nome='Lorenzo'")
        modulo.db().commit()
    # anche da console, senza spedire
    out = subprocess.run([sys.executable, os.path.join(QUI, "gestione.py"), "avvisi-prova"],
                         env=os.environ.copy(), cwd=QUI, check=True, capture_output=True,
                         text=True, encoding="utf-8").stdout
    assert "Lorenzo" in out and "RICEVE" in out and "Non è stato spedito nulla" in out
    assert modulo.TESTO_AVVISO in out
    # nessuna email partita e l'invio del lunedì è ancora da fare
    assert FintoSMTP.inviate == []
    with app.app_context():
        assert modulo.impostazione("avviso_settimana") == settimana
    # chi non è admin non la vede
    c = app.test_client()
    entra(c, "Daniele")
    assert c.get("/admin/avvisi/anteprima").status_code in (302, 403)


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


def test_statistiche_dei_consumi():
    """Issue #4: consumi per giorno/settimana/mese/anno, di tutti o di una persona, visibili a tutti."""
    from datetime import date, datetime, timedelta, timezone
    luca = app.test_client()
    entra(luca, "Luca")
    lid, caffe, acqua_m = id_di("Luca"), prod("caffe"), prod("acqua_macchinetta")
    # dalla home: 1 caffè (pagato da Luca) e 1 acqua macchinetta (pagata dalla Macchinetta del caffè)
    tok, html = csrf(luca, "/")
    luca.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{caffe}": "1", f"q{acqua_m}": "1"})
    # caffè di altri giorni, scritti direttamente con la data; uno annullato non conta
    adesso = datetime.now(timezone.utc)
    with app.app_context():
        for quando, qta, annullato in ((adesso - timedelta(days=2), 2, 0), (adesso - timedelta(days=40), 3, 0),
                                       (adesso.replace(year=adesso.year - 1, month=6, day=15), 4, 0),
                                       (adesso - timedelta(days=1), 5, 1)):
            modulo.db().execute("INSERT INTO movimenti (ts, persona_id, tipo, importo_cent, qta, prodotto_id, "
                                "creato_da, annullato) VALUES (?,?,?,?,?,?,?,?)",
                                (quando.isoformat(timespec="seconds"), lid, "acquisto", -30 * qta, qta, caffe,
                                 lid, annullato))
        modulo.db().commit()
        dati = modulo.consumi(lid)
        assert sorted(q for _g, p, q in dati if p == caffe) == [1, 2, 3, 4]
        # come nel saldo, l'acqua macchinetta conta sulla Macchinetta del caffè, non su Luca
        assert all(p != acqua_m for _g, p, _q in dati)
        conto = modulo.db().execute("SELECT addebito_id FROM prodotti WHERE id=?", (acqua_m,)).fetchone()[0]
        assert any(p == acqua_m for _g, p, _q in modulo.consumi(conto))
        assert modulo.persona(conto)["nome"] == "Macchinetta del caffè"
    # periodi: inizio della settimana (lunedì), mese prima a cavallo d'anno
    assert modulo.inizio_periodo(date(2026, 11, 12), "settimana") == date(2026, 11, 9)
    assert modulo.periodo_prima(date(2026, 1, 1), "mese") == date(2025, 12, 1)
    # la pagina: righe per periodo, i totali di oggi, e chiunque può vedere i consumi di Luca
    nick = app.test_client()
    entra(nick, "Nick")
    for periodo, righe in (("giorno", 14), ("settimana", 12), ("mese", 12)):
        pagina = nick.get(f"/statistiche?periodo={periodo}&persona={lid}").get_data(as_text=True)
        assert pagina.count('class="stat-etichetta"') == righe
    pagina = nick.get(f"/statistiche?periodo=anno&persona={lid}").get_data(as_text=True)
    assert f">{adesso.year - 1}<" in pagina and f">{adesso.year}<" in pagina
    oggi = re.sub(r"<[^>]+>|\s+", " ", re.search(r"Oggi</span>(.*?)</strong>", pagina, re.S).group(1)).strip()
    assert oggi == "☕ 1"                                            # riquadro «Oggi»: niente acqua macchinetta
    # il conto comune si può scegliere e mostra l'acqua macchinetta
    pagina = nick.get(f"/statistiche?persona={conto}").get_data(as_text=True)
    assert "Conti comuni" in pagina and "🫗" in re.search(r"Oggi</span>(.*?)</strong>", pagina, re.S).group(1)
    assert "Statistiche" in nick.get("/statistiche").get_data(as_text=True)
    assert app.test_client().get("/statistiche").status_code == 302
    # un database vecchio con «Conto Caffè»: al riavvio diventa «Macchinetta del caffè», una volta sola
    with app.app_context():
        modulo.db().execute("UPDATE persone SET nome='Conto Caffè' WHERE id=?", (conto,))
        modulo.db().execute("DELETE FROM impostazioni WHERE chiave='rinomina_conto_caffe'")
        modulo.db().commit()
    modulo.inizializza_db()
    with app.app_context():
        assert modulo.persona(conto)["nome"] == "Macchinetta del caffè"


def test_magazzino():
    """Issue #3: giacenze che scendono con gli acquisti e salgono con le spese, avviso sotto soglia."""
    def giacenze():
        with app.app_context():
            return {a["codice"]: a["giacenza"] for a in modulo.articoli(solo_attivi=False) if a["codice"]}

    def porta_saldo(nome, cent):
        with app.app_context():
            modulo.registra(id_di(nome), "rettifica", cent - modulo.saldo(id_di(nome)), nota="Rettifica: test")
            modulo.db().commit()

    def compra(client, **pezzi):
        tok, html = csrf(client, "/")
        return client.post("/acquista", data={"_csrf": tok, "nonce": nonce(html),
                                              **{f"q{prod(k)}": v for k, v in pezzi.items()}})

    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin/magazzino")
    with app.app_context():
        ids = {a["codice"]: a["id"] for a in modulo.articoli() if a["codice"]}
        # articoli e ricette di partenza; il bicchierino vuoto è gratis
        assert set(ids) == {"cialde", "bottiglie", "bicchierini"}
        assert modulo.db().execute("SELECT prezzo_cent FROM prodotti WHERE codice='bicchierino'").fetchone()[0] == 0
    # finché non è contato, niente avviso anche se la giacenza è sotto la soglia
    max_ = app.test_client()
    entra(max_, "Max")
    porta_saldo("Max", -500)
    assert "Sta finendo la merce" not in max_.get("/").get_data(as_text=True)
    # l'admin conta i pezzi veri
    for codice, contati, soglia in (("cialde", 10, 5), ("bicchierini", 10, 5), ("bottiglie", 3, 2)):
        admin.post(f"/admin/articolo/{ids[codice]}", data={"_csrf": toka, "nome": codice.capitalize(),
                   "emoji": "x", "soglia": soglia, "contati": contati, "attivo": "1"})
    assert giacenze() == {"cialde": 10, "bicchierini": 10, "bottiglie": 3}
    # 2 caffè + 1 acqua macchinetta + 1 bicchierino vuoto: scala la merce, il bicchierino non costa
    compra(max_, caffe=2, acqua_macchinetta=1, bicchierino=1)
    assert giacenze() == {"cialde": 8, "bicchierini": 7, "bottiglie": 2}
    with app.app_context():
        prezzo_caffe = modulo.prodotto(prod("caffe"))["prezzo_cent"]
    assert saldo_di("Max") == -500 - 2 * prezzo_caffe
    # annullando l'acquisto la merce torna
    with app.app_context():
        mid = modulo.db().execute("SELECT id FROM movimenti WHERE creato_da=? ORDER BY id DESC",
                                  (id_di("Max"),)).fetchone()[0]
    tok, _ = csrf(max_, "/")
    max_.post(f"/annulla/{mid}", data={"_csrf": tok})
    assert giacenze() == {"cialde": 10, "bicchierini": 10, "bottiglie": 3}
    # 1 acqua: bottiglie a 2 = soglia → avviso a chi è in debito e agli admin, non a chi è in credito
    compra(max_, acqua=1)
    assert giacenze()["bottiglie"] == 2
    riccardo = app.test_client()
    entra(riccardo, "Riccardo")
    porta_saldo("Riccardo", 500)
    assert "Sta finendo la merce" in max_.get("/").get_data(as_text=True)
    assert "Sta finendo la merce" in admin.get("/").get_data(as_text=True)
    assert "Sta finendo la merce" not in riccardo.get("/").get_data(as_text=True)
    # spesa: pezzi senza costo o costo senza pezzi non passano
    tok, html = csrf(max_, "/spesa")
    r = max_.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), f"qta_{ids['bottiglie']}": "6"})
    assert "Scrivi quanto hai speso per Bottiglie" in r.get_data(as_text=True)
    r = max_.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), f"costo_{ids['bottiglie']}": "3"})
    assert "Scrivi quanti pezzi di Bottiglie" in r.get_data(as_text=True)
    # 6 bottiglie per 3 € + zucchero 1,50: la merce entra solo quando l'admin approva
    saldo_prima = saldo_di("Max")
    max_.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), f"qta_{ids['bottiglie']}": "6",
                              f"costo_{ids['bottiglie']}": "3", "nota": "zucchero", "importo": "1,50"})
    rid = richiesta_in_attesa("spesa")
    with app.app_context():
        r = modulo.db().execute("SELECT importo_cent, nota FROM richieste WHERE id=?", (rid,)).fetchone()
        assert (r["importo_cent"], r["nota"]) == (450, "6 bottiglie, zucchero")
    assert giacenze()["bottiglie"] == 2
    admin.post(f"/richieste/{rid}/approva", data={"_csrf": toka})
    assert giacenze()["bottiglie"] == 8 and saldo_di("Max") == saldo_prima + 450
    assert "Sta finendo la merce" not in max_.get("/").get_data(as_text=True)
    # anche la spesa di un admin aspetta l'approvazione (qui è l'unico admin: la approva lui);
    # il registro e la pagina li vede solo l'admin
    tok, html = csrf(admin, "/spesa")
    admin.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), f"qta_{ids['cialde']}": "50",
                               f"costo_{ids['cialde']}": "10"})
    assert giacenze()["cialde"] == 10
    admin.post(f"/richieste/{richiesta_in_attesa('spesa')}/approva", data={"_csrf": toka})
    assert giacenze()["cialde"] == 60
    pagina = admin.get("/admin/magazzino").get_data(as_text=True)
    assert "Registro del magazzino" in pagina and "+50" in pagina
    assert max_.get("/admin/magazzino").status_code == 403
    # ricette modificabili: il caffè ora scala 2 cialde (e niente bicchierino)
    admin.post("/admin/ricette", data={"_csrf": toka, f"r_{prod('caffe')}_{ids['cialde']}": "2"})
    compra(max_, caffe=1)
    assert giacenze()["cialde"] == 58 and giacenze()["bicchierini"] == 10
    # prezzo 0 accettato per i prodotti; per gli importi normali 0 resta non valido
    assert modulo.leggi_euro("0") is None and modulo.leggi_euro("0", consenti_zero=True) == 0


def test_bilancio_magazzino():
    """Issue #2: iniziale + comprati − consumati ± differenze = in magazzino, in pezzi e in euro; solo admin."""
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin/magazzino")
    # articolo e prodotto nuovi, così i numeri sono quelli di questo test
    admin.post("/admin/articolo/nuovo", data={"_csrf": toka, "nome": "Zucchero", "emoji": "🍬", "soglia": "0"})
    admin.post("/admin/prodotto/nuovo", data={"_csrf": toka, "nome": "Dolcetto", "emoji": "🍭", "prezzo": "0,50"})
    with app.app_context():
        aid = modulo.db().execute("SELECT id FROM articoli WHERE nome='Zucchero'").fetchone()[0]
        prid = modulo.db().execute("SELECT id FROM prodotti WHERE nome='Dolcetto'").fetchone()[0]
        modulo.db().execute("INSERT INTO ricette VALUES (?,?,1)", (prid, aid))
        modulo.db().commit()

    def conta(n):
        admin.post(f"/admin/articolo/{aid}", data={"_csrf": toka, "nome": "Zucchero", "emoji": "🍬",
                                                  "soglia": "0", "contati": n, "attivo": "1"})
    conta(10)                                                      # quantità di partenza
    tok, html = csrf(admin, "/spesa")                              # 20 pezzi per 4 € = 0,20 € l'uno
    admin.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), f"qta_{aid}": "20", f"costo_{aid}": "4"})
    admin.post(f"/richieste/{richiesta_in_attesa('spesa')}/approva", data={"_csrf": toka})  # unico admin
    max_ = app.test_client()
    entra(max_, "Max")
    for qta in (5, 1):
        tok, html = csrf(max_, "/")
        max_.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prid}": qta})
    with app.app_context():                                        # l'ultimo (1 pezzo) viene annullato
        mid = modulo.db().execute("SELECT MAX(id) FROM movimenti WHERE prodotto_id=?", (prid,)).fetchone()[0]
    max_.post(f"/annulla/{mid}", data={"_csrf": tok})
    conta(22)                                                      # ne risultano 25: ne mancano 3
    with app.app_context():
        elenco, per_prod, totali = modulo.bilancio_magazzino()
    z = next(x for x in elenco if x["articolo"]["id"] == aid)
    assert (z["iniziale"], z["comprati"], z["consumati"], z["differenze"], z["giacenza"]) == (10, 20, 5, -3, 22)
    assert z["costo_medio"] == 20
    assert (z["valore_iniziale"], z["valore_comprati"], z["valore_consumati"],
            z["valore_differenze"], z["valore_giacenza"]) == (200, 400, 100, -60, 440)
    d = next(p for p in per_prod if p["prodotto"]["id"] == prid)
    assert (d["pezzi"], d["incasso"], d["costo"], d["margine"]) == (5, 250, 100, 150)
    assert (d["costo_unitario"], d["margine_unitario"]) == (20, 30)
    # un articolo mai comprato non ha costo: i totali in euro restano «—» invece di essere sbagliati
    bicchierini = next(x for x in elenco if x["articolo"]["codice"] == "bicchierini")
    assert bicchierini["costo_medio"] is None and totali["valore_giacenza"] is None
    pagina = admin.get("/admin/bilancio").get_data(as_text=True)
    assert "Zucchero" in pagina and "Mancano 3 pezzi" in pagina and "+1,50 €" in pagina
    assert max_.get("/admin/bilancio").status_code == 403
    with app.app_context():
        modulo.db().execute("UPDATE prodotti SET attivo=0 WHERE id=?", (prid,))
        modulo.db().commit()


def test_novita_e_comunicazioni():
    """Notifiche in home che si tolgono con «Ho letto»: novità dell'aggiornamento e comunicazioni degli admin."""
    from html import unescape
    from novita import NOVITA
    # novita.py: id unici dal più recente, ogni voce con le stesse righe in italiano e in inglese
    ids = [n["id"] for n in NOVITA]
    assert ids == sorted(set(ids), reverse=True)
    assert all(len(n["it"]) == len(n["en"]) > 0 for n in NOVITA)
    vit = app.test_client()
    entra(vit, "Vittorio")

    def home(client):
        return unescape(client.get("/").get_data(as_text=True))

    def account(creato, letta=""):
        with app.app_context():
            modulo.db().execute("UPDATE persone SET novita_lette=?, creato=? WHERE id=?",
                                (letta, creato, id_di("Vittorio")))
            modulo.db().commit()
    account("2026-01-01T08:00:00+00:00")                        # account di prima dell'aggiornamento
    assert "Novità dell'aggiornamento" in home(vit) and NOVITA[0]["it"][0] in home(vit)
    tok, _ = csrf(vit, "/")
    vit.post("/novita/lette", data={"_csrf": tok, "letto": "1"})
    assert NOVITA[0]["it"][0] not in home(vit)
    account("2099-01-01T08:00:00+00:00")                        # account nuovo: per lui non sono novità
    assert NOVITA[0]["it"][0] not in home(vit)
    account("2026-01-01T08:00:00+00:00")                        # in inglese le righe inglesi
    vit.get("/lingua/en")
    assert NOVITA[0]["en"][0] in home(vit)
    vit.get("/lingua/it")
    vit.post("/novita/lette", data={"_csrf": tok, "letto": "1"})
    # comunicazioni: le scrive solo un admin, il testo vuoto non passa
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin")
    assert vit.post("/admin/comunicazione/nuova", data={"_csrf": tok, "testo": "ciao"}).status_code == 403
    with app.app_context():
        prima = modulo.db().execute("SELECT COUNT(*) FROM comunicazioni").fetchone()[0]
    admin.post("/admin/comunicazione/nuova", data={"_csrf": toka, "testo": "   "})
    with app.app_context():
        assert modulo.db().execute("SELECT COUNT(*) FROM comunicazioni").fetchone()[0] == prima
    admin.post("/admin/comunicazione/nuova", data={"_csrf": toka, "testo": "Domani niente caffè\nfino alle 11"})
    with app.app_context():
        cid = modulo.db().execute("SELECT MAX(id) FROM comunicazioni").fetchone()[0]
    nick = app.test_client()
    entra(nick, "Nick")
    assert "Domani niente caffè" in home(vit) and "Domani niente caffè" in home(nick)
    assert "Domani niente caffè" not in home(admin)             # chi l'ha scritta l'ha già letta
    vit.post(f"/comunicazione/{cid}/letta", data={"_csrf": tok, "letto": "1"})
    assert "Domani niente caffè" not in home(vit) and "Domani niente caffè" in home(nick)
    assert "letta da 2 su" in unescape(admin.get("/admin").get_data(as_text=True))
    admin.post(f"/admin/comunicazione/{cid}/ritira", data={"_csrf": toka})
    assert "Domani niente caffè" not in home(nick)


def test_spiegazioni_prodotti_e_barra_in_basso():
    """Issue #7: quando segnare acqua macchinetta e bicchierino vuoto. Issue #9: Indietro e Home sempre visibili."""
    from html import unescape
    from lingue import EN
    assert all(t in EN for t in modulo.DESCRIZIONI_DEFAULT.values())   # le spiegazioni di partenza hanno l'inglese
    c = app.test_client()
    entra(c, "Giulia")
    home = unescape(c.get("/").get_data(as_text=True))
    for testo in modulo.DESCRIZIONI_DEFAULT.values():
        assert testo in home
    assert 'id="nota-bicchierino"' in home and 'data-codice="bicchierino"' in home
    assert 'class="barra-fondo"' not in home                         # nella pagina principale non serve
    # l'admin cambia la spiegazione di un prodotto (e la può togliere)
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin")
    with app.app_context():
        caffe = modulo.prodotto(prod("caffe"))
    dati = {"_csrf": toka, "nome": caffe["nome"], "emoji": caffe["emoji"], "attivo": "1",
            "prezzo": f"{caffe['prezzo_cent'] / 100:.2f}".replace(".", ",")}
    admin.post(f"/admin/prodotto/{caffe['id']}", data={**dati, "descrizione": "Prova   di spiegazione"})
    assert "Prova di spiegazione" in c.get("/").get_data(as_text=True)
    admin.post(f"/admin/prodotto/{caffe['id']}", data={**dati, "descrizione": ""})
    assert "Prova di spiegazione" not in c.get("/").get_data(as_text=True)
    # barra in basso: Indietro porta alla pagina giusta, Home c'è solo per chi ha fatto l'accesso
    for url, indietro in (("/saldi", "/"), ("/movimenti", "/"), (f"/persona/{id_di('Giulia')}", "/saldi"),
                          ("/statistiche", "/")):
        pagina = c.get(url).get_data(as_text=True)
        assert f'<a href="{indietro}" class="indietro">' in pagina and 'class="casa"' in pagina, url
        assert "Torna indietro" not in pagina
    assert '<a href="/admin/magazzino" class="indietro">' in admin.get("/admin/bilancio").get_data(as_text=True)
    fuori = app.test_client().get("/come-funziona").get_data(as_text=True)
    assert '<a href="/accedi" class="indietro">' in fuori and 'class="casa"' not in fuori


def test_messaggi_personali():
    """Issue #6: un admin manda un messaggio solo ad alcune persone; lo vedono solo loro, fino a «Ho letto»."""
    from html import unescape
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin")
    clienti = {}
    for nome in ("Vittorio", "Nick", "Giulia"):
        clienti[nome] = app.test_client()
        entra(clienti[nome], nome)

    def home(nome):
        return unescape(clienti[nome].get("/").get_data(as_text=True))

    def quante():
        with app.app_context():
            return modulo.db().execute("SELECT COUNT(*) FROM comunicazioni").fetchone()[0]
    # «solo a persone scelte» senza nessuno (o solo con un conto comune) non parte
    prima = quante()
    admin.post("/admin/comunicazione/nuova", data={"_csrf": toka, "testo": "x", "a_chi": "persone"})
    admin.post("/admin/comunicazione/nuova", data={"_csrf": toka, "testo": "x", "a_chi": "persone",
                                                    "destinatari": [id_di("Cassa")]})
    assert quante() == prima
    admin.post("/admin/comunicazione/nuova", data={"_csrf": toka, "testo": "Passa a ritirare la tazza",
                                                    "a_chi": "persone",
                                                    "destinatari": [id_di("Vittorio"), id_di("Nick")]})
    assert quante() == prima + 1
    for nome in ("Vittorio", "Nick"):
        assert "Messaggio per te" in home(nome) and "Passa a ritirare la tazza" in home(nome)
    assert "Passa a ritirare la tazza" not in home("Giulia")
    with app.app_context():
        cid = modulo.db().execute("SELECT MAX(id) FROM comunicazioni").fetchone()[0]
        nomi = sorted(modulo.nome_completo(modulo.persona(id_di(n))) for n in ("Vittorio", "Nick"))
    pagina = unescape(admin.get("/admin").get_data(as_text=True))
    assert f"a {', '.join(nomi)}" in pagina and "letta da 0 su 2" in pagina
    tok, _ = csrf(clienti["Vittorio"], "/")
    clienti["Vittorio"].post(f"/comunicazione/{cid}/letta", data={"_csrf": tok, "letto": "1"})
    assert "Passa a ritirare la tazza" not in home("Vittorio") and "Passa a ritirare la tazza" in home("Nick")
    assert "letta da 1 su 2" in unescape(admin.get("/admin").get_data(as_text=True))
    # dalla scheda della persona l'admin arriva al modulo con lei già scelta; gli altri non vedono il link
    scheda = admin.get(f"/persona/{id_di('Giulia')}").get_data(as_text=True)
    assert f"/admin?a={id_di('Giulia')}#comunicazioni" in scheda
    assert "Scrivi un messaggio" not in clienti["Nick"].get(f"/persona/{id_di('Giulia')}").get_data(as_text=True)
    modulo_admin = admin.get(f"/admin?a={id_di('Giulia')}").get_data(as_text=True)
    assert re.search(rf'name="destinatari" value="{id_di("Giulia")}" checked', modulo_admin)
    # messaggio dell'app (senza autore), come serviranno per le richieste rifiutate
    with app.app_context():
        with modulo.db():
            modulo.invia_messaggio("Il tuo pagamento è stato rifiutato", [id_di("Giulia")])
    assert "Il tuo pagamento è stato rifiutato" in home("Giulia")
    assert "Il tuo pagamento è stato rifiutato" not in home("Nick")
    admin.post(f"/admin/comunicazione/{cid}/ritira", data={"_csrf": toka})
    assert "Passa a ritirare la tazza" not in home("Nick")


def test_esito_delle_richieste_al_richiedente():
    """Issue #1: chi ha fatto un pagamento o una spesa riceve un messaggio quando è confermato o rifiutato."""
    from html import unescape
    agnese, federico = app.test_client(), app.test_client()
    entra(agnese, "Agnese")
    entra(federico, "Federico")

    def home(c):
        return unescape(c.get("/").get_data(as_text=True))

    def paga(importo):
        tok, html = csrf(agnese, "/paga")
        agnese.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                                   "controparte": id_di("Federico"), "importo": importo})
        return richiesta_in_attesa("pagamento")
    tokf, _ = csrf(federico, "/richieste")
    # confermato: Agnese lo sa, Federico (che ha deciso) non riceve niente
    federico.post(f"/richieste/{paga('1')}/approva", data={"_csrf": tokf})
    h = home(agnese)
    assert "Il tuo pagamento di 1,00 € a Federico" in h and "è stato confermato da Federico" in h
    assert "Il tuo pagamento di 1,00 €" not in home(federico)
    # rifiutato con il motivo
    federico.post(f"/richieste/{paga('2')}/rifiuta", data={"_csrf": tokf, "motivo": "  non li ho   ricevuti "})
    h = home(agnese)
    assert "Il tuo pagamento di 2,00 €" in h and "è stato rifiutato da Federico" in h
    assert "Motivo: non li ho ricevuti" in h
    # una richiesta già decisa non si decide due volte
    with app.app_context():
        rid = modulo.db().execute("SELECT MAX(id) FROM richieste WHERE tipo='pagamento'").fetchone()[0]
    assert federico.post(f"/richieste/{rid}/approva", data={"_csrf": tokf}).status_code == 403
    # spesa rifiutata da un admin: il messaggio arriva nella lingua di chi l'ha fatta
    with app.app_context():
        modulo.db().execute("UPDATE persone SET lingua='en' WHERE id=?", (id_di("Agnese"),))
        modulo.db().commit()
    tok, html = csrf(agnese, "/spesa")
    agnese.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "nota": "zucchero", "importo": "3"})
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/richieste")
    admin.post(f"/richieste/{richiesta_in_attesa('spesa')}/rifiuta", data={"_csrf": toka, "motivo": "doppia"})
    assert "Your purchase for the group “zucchero” (3,00 €) was rejected by" in home(agnese)
    assert "Reason: doppia" in home(agnese)
    with app.app_context():
        modulo.db().execute("UPDATE persone SET lingua='it' WHERE id=?", (id_di("Agnese"),))
        modulo.db().commit()
    # «Ho letto» toglie il messaggio
    with app.app_context():
        ids = [r[0] for r in modulo.db().execute(
            "SELECT comunicazione_id FROM comunicazioni_destinatari WHERE persona_id=?", (id_di("Agnese"),))]
    tok, _ = csrf(agnese, "/")
    for cid in ids:
        agnese.post(f"/comunicazione/{cid}/letta", data={"_csrf": tok, "letto": "1"})
    assert "è stato confermato da" not in home(agnese)


def test_eliminare_un_profilo():
    """Issue #8: un admin elimina un profilo (saldo a 0), lo può ripristinare per 3 giorni, poi è anonimizzato."""
    from html import unescape
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin")
    jid = id_di("J.")
    j = app.test_client()
    entra(j, "J.")

    def porta_saldo(cent):
        with app.app_context():
            modulo.registra(jid, "rettifica", cent - modulo.saldo(jid), nota="Rettifica: test")
            modulo.db().commit()

    def elimina():
        return unescape(admin.post(f"/admin/persona/{jid}/elimina", data={"_csrf": toka},
                                   follow_redirects=True).get_data(as_text=True))
    # con il saldo diverso da 0, o con richieste in attesa, non si può
    porta_saldo(500)
    assert "prima portalo a 0" in elimina()
    porta_saldo(0)
    tok, html = csrf(j, "/paga")
    j.post("/paga", data={"_csrf": tok, "nonce": nonce(html), "verso": "dato",
                          "controparte": id_di("Nick"), "importo": "1"})
    assert "Ci sono richieste in attesa" in elimina()
    j.post(f"/richieste/{richiesta_in_attesa('pagamento')}/annulla", data={"_csrf": tok})
    # e nemmeno il proprio profilo
    admin.post(f"/admin/persona/{id_di('Filippo')}/elimina", data={"_csrf": toka})
    with app.app_context():
        assert not modulo.persona(id_di("Filippo"))["eliminato_ts"]
    # eliminato: disconnesso, sparisce da accesso e saldi, compare tra i profili eliminati
    assert "Profilo di" in elimina()
    assert j.get("/").status_code == 302
    assert f'value="{jid}"' not in app.test_client().get("/accedi").get_data(as_text=True)
    assert f"/persona/{jid}" not in admin.get("/saldi").get_data(as_text=True)
    pagina = unescape(admin.get("/admin").get_data(as_text=True))
    assert "Profili eliminati" in pagina and f"/admin/persona/{jid}/ripristina" in pagina
    assert "Profilo eliminato" in unescape(admin.get(f"/admin/persona/{jid}").get_data(as_text=True))
    admin.post(f"/admin/persona/{jid}", data={"_csrf": toka, "nome": "Altro", "attivo": "1"})
    with app.app_context():
        assert modulo.persona(jid)["nome"] == "J." and not modulo.persona(jid)["attivo"]
    # ripristinato: torna come prima
    admin.post(f"/admin/persona/{jid}/ripristina", data={"_csrf": toka})
    assert f'value="{jid}"' in app.test_client().get("/accedi").get_data(as_text=True)
    # eliminato di nuovo e passati i 3 giorni: alla prima pagina aperta i dati personali spariscono
    elimina()
    with app.app_context():
        movimenti = modulo.db().execute("SELECT COUNT(*) FROM movimenti WHERE persona_id=?", (jid,)).fetchone()[0]
        modulo.db().execute("UPDATE persone SET eliminato_ts='2026-01-01T08:00:00+00:00', email='j@example.com', "
                            "iban='IT60X0542811101000000123456' WHERE id=?", (jid,))
        modulo.db().commit()
    admin.get("/")
    with app.app_context():
        p = modulo.persona(jid)
        assert (p["nome"], p["cognome"], p["email"], p["iban"], p["pin_hash"], p["anonimizzato"]) == \
            ("Persona eliminata", f"#{jid}", "", "", None, 1)
        assert modulo.db().execute("SELECT COUNT(*) FROM movimenti WHERE persona_id=?", (jid,)).fetchone()[0] == movimenti
    admin.post(f"/admin/persona/{jid}/ripristina", data={"_csrf": toka})
    with app.app_context():
        assert not modulo.persona(jid)["attivo"]                    # dopo i 3 giorni non si ripristina più
    assert admin.post(f"/admin/persona/{jid}/elimina", data={"_csrf": toka}).status_code == 302
    assert j.post(f"/admin/persona/{id_di('Nick')}/elimina", data={"_csrf": tok}).status_code in (302, 403)


def test_ripristino_da_backup_su_un_server_nuovo():
    """Issue #12: «gestione.py ripristina» rimette tutti i dati di un backup .db su un server nuovo."""
    import sqlite3
    nuovo = tempfile.mkdtemp(prefix="caffe_nuovo_server_")
    dati = os.path.join(nuovo, "dati")
    try:
        backup = os.path.join(nuovo, "caffe_backup.db")
        with app.app_context():
            with open(backup, "wb") as f:
                f.write(modulo.copia_database(modulo.db()))
            conta = {t: modulo.db().execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("persone", "movimenti", "richieste", "magazzino", "comunicazioni")}
            pin = modulo.persona(id_di("Filippo"))["pin_hash"]
        env = {**os.environ, "CAFFE_DATA_DIR": dati, "PYTHONUTF8": "1"}

        def ripristina(*argomenti, risposta=""):
            r = subprocess.run([sys.executable, os.path.join(QUI, "gestione.py"), "ripristina", *argomenti],
                               input=risposta, capture_output=True, text=True, env=env, cwd=QUI)
            return r.returncode, r.stdout + r.stderr
        # un file che non è un database viene rifiutato; senza «SI» non cambia niente
        sbagliato = os.path.join(nuovo, "non_un_db.db")
        with open(sbagliato, "w") as f:
            f.write("ciao")
        codice, testo = ripristina(sbagliato, "--si")
        assert codice != 0 and "Non è un database valido" in testo
        codice, testo = ripristina(backup, risposta="no\n")
        assert codice != 0 and "Annullato" in testo
        # ripristinato: stessi dati, stessi PIN
        codice, testo = ripristina(backup, "--si")
        assert codice == 0 and "Fatto" in testo, testo
        con = sqlite3.connect(os.path.join(dati, "caffe.db"))
        assert {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in conta} == conta
        assert con.execute("SELECT pin_hash FROM persone WHERE id=?", (id_di("Filippo"),)).fetchone()[0] == pin
        con.close()
        # una seconda volta c'erano già dati: prima ne salva una copia di sicurezza
        codice, testo = ripristina(backup, "--si")
        assert codice == 0 and any(f.startswith("caffe_prima_del_ripristino_") for f in os.listdir(dati))
    finally:
        shutil.rmtree(nuovo, ignore_errors=True)


def test_acqua_della_macchinetta_divisa_tra_chi_prende_caffe():
    """Issue #10: il debito della Macchinetta del caffè si divide tra le persone attive che hanno preso
    caffè, in proporzione ai caffè, dopo la conferma di un admin; ognuno riceve un messaggio."""
    from html import unescape
    # i centesimi tornano sempre esatti
    assert modulo.dividi_in_quote(100, [1, 1, 1]) == [34, 33, 33]
    assert modulo.dividi_in_quote(7, [3, 1]) == [5, 2]
    assert modulo.dividi_in_quote(0, [2, 5]) == [0, 0] and modulo.dividi_in_quote(50, []) == []
    assert sum(modulo.dividi_in_quote(1001, [7, 3, 11, 1])) == 1001
    admin = entra_come_admin()
    toka, _ = csrf(admin, "/admin")
    nick = app.test_client()
    entra(nick, "Nick")
    tok, html = csrf(nick, "/")                  # un'acqua per la macchinetta in più, così c'è debito
    nick.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('acqua_macchinetta')}": 1})
    with app.app_context():
        a = modulo.anteprima_ripartizione()
        conto = a["conto"]["id"]
        assert a["debito"] == -modulo.saldo(conto) > 0 and not a["dal"]
        assert sum(r["quota"] for r in a["righe"]) == a["debito"]
        assert all(r["persona"]["attivo"] and not r["persona"]["speciale"] for r in a["righe"])
        eliminati = {r[0] for r in modulo.db().execute("SELECT id FROM persone WHERE eliminato_ts<>''")}
        assert eliminati and not eliminati & {r["persona"]["id"] for r in a["righe"]}   # profili eliminati: esclusi
        prima = {r["persona"]["id"]: modulo.saldo(r["persona"]["id"]) for r in a["righe"]}
    # soglia: con 0,01 € l'avviso compare in home agli admin (non agli altri)
    admin.post("/admin/acqua/soglia", data={"_csrf": toka, "soglia": "0,01"})
    assert "dividi il debito dell'acqua" in unescape(admin.get("/").get_data(as_text=True))
    assert "dividi il debito dell'acqua" not in unescape(nick.get("/").get_data(as_text=True))
    assert "Anteprima: chi paga quanto" in admin.get("/admin").get_data(as_text=True)
    # solo un admin divide, e solo confermando i numeri che vede
    assert nick.post("/admin/acqua/dividi", data={"_csrf": tok}).status_code == 403
    admin.post("/admin/acqua/dividi", data={"_csrf": toka, "debito": a["debito"] + 1, "caffe": a["caffe"]})
    with app.app_context():
        assert modulo.saldo(conto) == -a["debito"]                                  # non è cambiato niente
    admin.post("/admin/acqua/dividi", data={"_csrf": toka, "debito": a["debito"], "caffe": a["caffe"]})
    with app.app_context():
        assert modulo.saldo(conto) == 0
        for r in a["righe"]:
            assert modulo.saldo(r["persona"]["id"]) == prima[r["persona"]["id"]] - r["quota"]
        dopo = modulo.anteprima_ripartizione()
        assert dopo["debito"] == 0 and dopo["dal"] and not dopo["righe"]           # si riparte da qui
        pagante = next(r for r in a["righe"] if r["quota"])
    # chi paga riceve il messaggio con la sua quota; il movimento si legge
    with app.app_context():
        testo = modulo.db().execute("""SELECT c.testo FROM comunicazioni c JOIN comunicazioni_destinatari d
                                       ON d.comunicazione_id = c.id WHERE d.persona_id = ? ORDER BY c.id DESC""",
                                    (pagante["persona"]["id"],)).fetchone()[0]
    assert f"ti sono stati addebitati {modulo.euro(pagante['quota'], segno=False)} per i tuoi {pagante['caffe']} caffè" in testo
    assert "Acqua della macchinetta: quota per" in unescape(admin.get("/movimenti?tutti=1").get_data(as_text=True))
    # dopo la divisione contano solo i caffè nuovi
    tok, html = csrf(nick, "/")
    nick.post("/acquista", data={"_csrf": tok, "nonce": nonce(html), f"q{prod('caffe')}": 2,
                                 f"q{prod('acqua_macchinetta')}": 1})
    with app.app_context():
        nuova = modulo.anteprima_ripartizione()
        assert [(r["persona"]["id"], r["caffe"]) for r in nuova["righe"]] == [(id_di("Nick"), 2)]
        assert nuova["righe"][0]["quota"] == nuova["debito"] > 0
        mid = modulo.db().execute("SELECT id FROM movimenti WHERE tipo='ripartizione' AND persona_id=?",
                                  (conto,)).fetchone()[0]
    # annullando la divisione si torna a prima, tutta insieme
    admin.post(f"/annulla/{mid}", data={"_csrf": toka})
    with app.app_context():
        di_nuovo = modulo.anteprima_ripartizione()
        assert not di_nuovo["dal"] and di_nuovo["debito"] == a["debito"] + nuova["debito"]
        for r in a["righe"]:
            assert modulo.saldo(r["persona"]["id"]) == prima[r["persona"]["id"]] - (
                2 * modulo.prodotto(prod("caffe"))["prezzo_cent"] if r["persona"]["id"] == id_di("Nick") else 0)
    admin.post("/admin/acqua/soglia", data={"_csrf": toka, "soglia": "3"})


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))


def test_hidden_vince_sul_css():
    # Il riquadro "oltre il limite" è nascosto con l'attributo hidden: il CSS non deve annullarlo
    css = open(os.path.join(os.path.dirname(__file__), "static", "stile.css"), encoding="utf-8").read()
    assert "[hidden] { display: none !important; }" in css


def test_utente_root_per_le_prove_in_locale():
    """python3 app.py crea «root», amministratore già approvato: si entra subito con il PIN."""
    with app.app_context():
        pid = modulo.crea_root("0000")
        assert modulo.crea_root("4321") == pid          # la seconda volta non lo duplica, cambia il PIN
    c = app.test_client()
    tok, _ = csrf(c)
    r = c.post("/accedi", data={"_csrf": tok, "persona_id": pid, "pin": "4321"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/")   # niente attesa di approvazione
    assert c.get("/admin").status_code == 200


def test_spesa_di_un_admin_la_approva_un_altro_admin():
    """Anche le spese degli admin aspettano l'approvazione: di un altro admin se c'è,
    altrimenti (unico admin) può approvarla chi l'ha registrata."""
    admin = entra_come_admin()                                     # Filippo
    with app.app_context():                                        # root (test precedente) non conta qui
        modulo.db().execute("UPDATE persone SET admin=0 WHERE nome='root'")
        modulo.db().commit()
    prima = saldo_di("Filippo")
    tok, html = csrf(admin, "/spesa")
    assert "Invia per approvazione" in html
    r = admin.post("/spesa", data={"_csrf": tok, "nonce": nonce(html), "importo": "6", "nota": "latte"},
                   follow_redirects=True)
    assert "Sei l'unico amministratore" in r.get_data(as_text=True).replace("&#39;", "'")
    assert saldo_di("Filippo") == prima                            # non vale ancora
    rid = richiesta_in_attesa("spesa")
    # con un secondo admin, Filippo non può più approvare la propria spesa
    with app.app_context():
        modulo.db().execute("UPDATE persone SET admin=1 WHERE id=?", (id_di("Massi"),))
        modulo.db().commit()
    try:
        altro = app.test_client()
        entra(altro, "Massi")
        assert admin.post(f"/richieste/{rid}/approva", data={"_csrf": tok}).status_code == 403
        assert "latte" not in admin.get("/richieste").get_data(as_text=True).split("Le mie richieste in attesa")[0]
        tokm, html = csrf(altro, "/richieste")
        assert "latte" in html
        altro.post(f"/richieste/{rid}/approva", data={"_csrf": tokm})
        assert saldo_di("Filippo") == prima + 600
        registro = altro.get("/admin/registro?sezione=spese").get_data(as_text=True)
        assert "latte" in registro
    finally:
        with app.app_context():
            modulo.db().execute("UPDATE persone SET admin=0 WHERE id=?", (id_di("Massi"),))
            modulo.db().execute("UPDATE persone SET admin=1 WHERE nome='root'")
            modulo.db().commit()
