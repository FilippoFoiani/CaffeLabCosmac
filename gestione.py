"""
Comandi di gestione da lanciare nella console (Bash) del server.

  python3 gestione.py importa saldi_iniziali.csv   carica persone e saldi iniziali
  python3 gestione.py elenco                       mostra persone, id e saldi
  python3 gestione.py admin 23                     rende amministratore la persona con id 23
  python3 gestione.py reset-pin 23                 azzera il PIN della persona con id 23
  python3 gestione.py avvisi                       manda le email del lunedì (una volta a settimana)
"""
import os
import csv
import sys

from app import adesso, app, connetti, email_configurata, euro, invia_avvisi, leggi_euro


def importa(percorso):
    con = connetti()
    aggiunti = saltati = 0
    try:   # UTF-8, oppure il formato che usa Excel su Windows
        with open(percorso, newline="", encoding="utf-8-sig") as f:
            testo_file = f.read()
    except UnicodeDecodeError:
        with open(percorso, newline="", encoding="cp1252") as f:
            testo_file = f.read()
    righe = [r for r in csv.DictReader(testo_file.splitlines(), delimiter=";")
             if (r.get("nome") or "").strip()]
    with con:
        for r in righe:
            nome, cognome = r["nome"].strip(), (r.get("cognome") or "").strip()
            esiste = con.execute("SELECT id FROM persone WHERE LOWER(nome)=LOWER(?) AND "
                                 "LOWER(cognome)=LOWER(?)", (nome, cognome)).fetchone()
            if esiste:
                print(f"  già presente, salto: {nome} {cognome}")
                saltati += 1
                continue
            speciale = 1 if (r.get("conto_speciale") or "").strip().lower() in ("1", "si", "sì", "x") else 0
            cur = con.execute("INSERT INTO persone (nome, cognome, speciale, creato) VALUES (?,?,?,?)",
                              (nome, cognome, speciale, adesso()))
            totale = 0
            # Una colonna per ogni foglio cartaceo (saldo_caffe, saldo_acqua, …) oppure "saldo"
            for colonna in [k for k in r if k and k.startswith("saldo")]:
                testo = (r.get(colonna) or "").strip()
                if not testo or not testo.strip("0,.+-€ "):
                    continue
                cent = leggi_euro(testo, consenti_negativo=True)
                if cent is None:
                    raise SystemExit(f"Saldo non valido per {nome} {cognome} ({colonna}): {testo!r}")
                origine = colonna.replace("saldo_", "foglio ").replace("caffe", "caffè") \
                    if colonna != "saldo" else "foglio cartaceo"
                con.execute("INSERT INTO movimenti (ts, persona_id, tipo, importo_cent, nota) "
                            "VALUES (?,?,?,?,?)", (adesso(), cur.lastrowid, "iniziale", cent, origine))
                totale += cent
            print(f"  + {nome} {cognome}: {euro(totale)}")
            aggiunti += 1
    print(f"Fatto: {aggiunti} aggiunti, {saltati} già presenti.")


def elenco():
    con = connetti()
    righe = con.execute("""
        SELECT p.*, COALESCE((SELECT SUM(importo_cent) FROM movimenti m
                              WHERE m.persona_id=p.id AND m.annullato=0),0) AS saldo
        FROM persone p ORDER BY p.id""").fetchall()
    for p in righe:
        flag = []
        if p["admin"]: flag.append("ADMIN")
        if p["speciale"]: flag.append("conto")
        if not p["attivo"]: flag.append("non attivo")
        if not p["pin_hash"] and not p["speciale"]: flag.append("mai entrato")
        print(f"{p['id']:>4}  {(p['nome'] + ' ' + p['cognome']).strip():<28} "
              f"{euro(p['saldo']):>12}  {' '.join(flag)}")


def imposta_admin(pid):
    con = connetti()
    with con:
        p = con.execute("SELECT * FROM persone WHERE id=?", (pid,)).fetchone()
        if p and p["pin_hash"] and not p["approvato"]:     # resta traccia: approvato da console
            richiesto = f"{p['nuovo_nome']} {p['nuovo_cognome']}".strip() or f"{p['nome']} {p['cognome']}".strip()
            con.execute("INSERT INTO registro_accessi (ts, persona_id, account, richiesto, email, nuovo, "
                        "esito, deciso_da) VALUES (?,?,?,?,?,?, 'approvato', NULL)",
                        (adesso(), pid, "" if p["nuovo_account"] else f"{p['nome']} {p['cognome']}".strip(),
                         richiesto, p["email"], p["nuovo_account"]))
        n = con.execute("UPDATE persone SET admin=1, approvato=1, "
                        "nome = CASE WHEN nuovo_nome<>'' THEN nuovo_nome ELSE nome END, "
                        "cognome = CASE WHEN nuovo_nome<>'' THEN nuovo_cognome ELSE cognome END, "
                        "nuovo_nome='', nuovo_cognome='' WHERE id=? AND speciale=0", (pid,)).rowcount
    print("Fatto." if n else "Id non trovato (o è un conto senza accesso). Usa: python3 gestione.py elenco")


def reset_pin(pid):
    con = connetti()
    with con:
        n = con.execute("UPDATE persone SET pin_hash=NULL, tentativi=0, bloccato_fino=NULL, "
                        "versione_sessione=versione_sessione+1 WHERE id=?", (pid,)).rowcount
    print("PIN azzerato." if n else "Id non trovato.")


if __name__ == "__main__":
    with app.app_context():
        args = sys.argv[1:]
        if len(args) == 2 and args[0] == "importa":
            importa(args[1])
        elif args == ["elenco"]:
            elenco()
        elif len(args) == 2 and args[0] == "admin" and args[1].isdigit():
            imposta_admin(int(args[1]))
        elif len(args) == 2 and args[0] == "reset-pin" and args[1].isdigit():
            reset_pin(int(args[1]))
        elif args == ["avvisi"]:
            if not email_configurata():
                raise SystemExit("Email non configurata (CAFFE_SMTP_USER / CAFFE_SMTP_PASSWORD).")
            esito = invia_avvisi(connetti(), os.environ.get("CAFFE_URL", ""))
            print("Già inviati questa settimana." if esito is None else esito)
        else:
            print(__doc__)
