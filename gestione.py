"""
Comandi di gestione da lanciare nella console (Bash) del server.

  python3 gestione.py importa saldi_iniziali.csv   carica persone e saldi iniziali
  python3 gestione.py elenco                       mostra persone, id e saldi
  python3 gestione.py admin 23                     rende amministratore la persona con id 23
  python3 gestione.py reset-pin 23                 azzera il PIN della persona con id 23
  python3 gestione.py avvisi                       manda le email del lunedì (una volta a settimana)
  python3 gestione.py avvisi-prova                 prova a secco: chi le riceverebbe e il testo, senza spedire
  python3 gestione.py avvisi-prova tu@esempio.it   manda solo a quell'indirizzo una copia [PROVA] dell'avviso
  python3 gestione.py ripristina caffe_backup.db   rimette tutti i dati da un backup .db (es. cambio di provider)
"""
import os
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import app as modulo_app
from app import (NOME_APP, SMTP_USER, adesso, anteprima_avvisi, app, connetti, email_configurata, euro,
                 invia_avvisi, leggi_euro, ora_locale, spedisci)


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


def prova_avvisi(indirizzo_prova=None):
    """Senza indirizzo: elenca chi riceverebbe l'avviso e mostra il testo, senza spedire nulla
    (e senza toccare l'invio del lunedì). Con un indirizzo: manda lì una sola copia [PROVA]."""
    voci = anteprima_avvisi(connetti(), os.environ.get("CAFFE_URL", ""))
    if indirizzo_prova:
        if not email_configurata():
            raise SystemExit("Email non configurata (CAFFE_SMTP_USER / CAFFE_SMTP_PASSWORD).")
        if not voci:
            raise SystemExit("Nessuno è in negativo: non c'è un avviso da mandare come prova.")
        v = voci[0]
        try:
            n, errori = spedisci([(indirizzo_prova, "[PROVA] " + v["oggetto"], v["corpo"])])
        except Exception as e:   # credenziali sbagliate, rete, …
            raise SystemExit(f"Invio non riuscito: {type(e).__name__}: {e}")
        print(f"Inviata a {indirizzo_prova} la copia dell'avviso di {v['nome']}." if n
              else f"Invio non riuscito: {errori}")
        return
    print(f"Mittente: {NOME_APP} <{SMTP_USER}>" if SMTP_USER else "Mittente: email non configurata")
    if SMTP_USER and not email_configurata():
        print("Attenzione: manca CAFFE_SMTP_PASSWORD, le email non partirebbero.")
    motivi = {"": "RICEVE", "senza_email": "senza email", "disattivato": "ha tolto la spunta"}
    for v in voci:
        print(f"  {v['nome']:<28} {euro(v['saldo']):>10}  {motivi[v['motivo']]:<18} {v['email']}")
    print(f"In negativo: {len(voci)}, la ricevono per email: {sum(1 for v in voci if not v['motivo'])}. "
          "Non è stato spedito nulla.")
    primo = next((v for v in voci if not v["motivo"]), voci[0] if voci else None)
    if primo:
        print(f"\n--- Esempio: email per {primo['nome']} ---\nOggetto: {primo['oggetto']}\n\n{primo['corpo']}")


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


TABELLE_NECESSARIE = {"persone", "movimenti", "prodotti", "impostazioni"}


def controlla_backup(percorso):
    """Apre il backup in sola lettura e controlla che sia un database di Caffè Lab integro.
    Restituisce un riassunto (dizionario) oppure esce con un messaggio chiaro."""
    file = Path(percorso)
    if not file.is_file():
        raise SystemExit(f"File non trovato: {percorso}")
    try:
        con = sqlite3.connect(file.resolve().as_uri() + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        esito = con.execute("PRAGMA integrity_check").fetchone()[0]
        tabelle = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.DatabaseError as e:
        raise SystemExit(f"Non è un database valido ({e}). Usa il file caffe_backup_….db del backup.")
    if esito != "ok":
        raise SystemExit(f"Il database è rovinato (controllo: {esito}). Prova con un backup precedente.")
    mancano = TABELLE_NECESSARIE - tabelle
    if mancano:
        raise SystemExit(f"Non sembra un backup di {NOME_APP}: mancano le tabelle {', '.join(sorted(mancano))}.")
    riassunto = {
        "persone": con.execute("SELECT COUNT(*) FROM persone WHERE speciale=0").fetchone()[0],
        "admin": con.execute("SELECT COUNT(*) FROM persone WHERE speciale=0 AND admin=1").fetchone()[0],
        "movimenti": con.execute("SELECT COUNT(*) FROM movimenti").fetchone()[0],
        "ultimo": con.execute("SELECT MAX(ts) FROM movimenti").fetchone()[0],
    }
    con.close()
    return riassunto


def ripristina(percorso, conferma=False):
    """Sostituisce il database dell'app con un backup .db (cambio di provider o database rovinato).
    Prima salva una copia di sicurezza di quello attuale, se contiene dati; dopo aggiorna le tabelle
    alla versione dell'app, come fa un riavvio."""
    db_path = Path(modulo_app.DB_PATH)
    if Path(percorso).resolve() == db_path.resolve():
        raise SystemExit("Questo è già il database in uso: indica il file del backup.")
    r = controlla_backup(percorso)
    ultimo = ora_locale(r["ultimo"]) if r["ultimo"] else "nessuno"
    print(f"Backup: {percorso}")
    print(f"  {r['persone']} persone ({r['admin']} amministratori), {r['movimenti']} movimenti, ultimo movimento: {ultimo}")
    attuale = connetti()
    persone_ora = attuale.execute("SELECT COUNT(*) FROM persone WHERE speciale=0").fetchone()[0]
    if persone_ora:
        print(f"ATTENZIONE: il database attuale ({db_path}) ha già {persone_ora} persone: verrà sostituito.")
    if not conferma and input("Scrivi SI per sostituire i dati con quelli del backup: ").strip().upper() != "SI":
        attuale.close()
        raise SystemExit("Annullato: non è cambiato niente.")
    if persone_ora:      # copia di sicurezza di quello che c'era, nella stessa cartella dati/
        copia = db_path.with_name(f"caffe_prima_del_ripristino_{datetime.now():%Y-%m-%d_%H%M%S}.db")
        dest = sqlite3.connect(copia)
        attuale.backup(dest)
        dest.close()
        print(f"Copia di sicurezza del database di prima: {copia}")
    sorgente = sqlite3.connect(Path(percorso).resolve().as_uri() + "?mode=ro", uri=True)
    sorgente.backup(attuale)          # copia pagina per pagina, anche se l'app è accesa
    sorgente.close()
    attuale.close()
    modulo_app.inizializza_db()       # un backup vecchio prende le tabelle e le colonne nuove
    print("Fatto: dati ripristinati. Ora riavvia la web app (su PythonAnywhere: touch /var/www/*_wsgi.py).")


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
        elif args == ["avvisi-prova"]:
            prova_avvisi()
        elif len(args) == 2 and args[0] == "avvisi-prova" and "@" in args[1]:
            prova_avvisi(args[1])
        elif len(args) in (2, 3) and args[0] == "ripristina" and args[2:] in ([], ["--si"]):
            ripristina(args[1], conferma=args[2:] == ["--si"])
        else:
            print(__doc__)
