# ☕ Caffè Lab

Web app per segnare caffè e acqua del laboratorio con il telefono (QR code sulla macchinetta) e tenere i saldi di tutti, al posto del foglio con le stanghette.

- Acquisti con + / − per prodotto (caffè, acqua, acqua per la macchinetta)
- Un saldo unico per persona, pagamenti tra persone, spese per il gruppo
- Avviso del lunedì per chi è in negativo (in app e per email)
- Promemoria di manutenzione della macchinetta per gli amministratori
- Controlli contro i furbi: accessi, spese e pagamenti approvati, limite di debito
- Pagina «Come funziona» con regole, pulizia e come rientrare dal debito
- Italiano e inglese, export Excel, backup del database

Python 3.10+ e Flask, database SQLite in `dati/` (escluso dal repository).
Installazione e aggiornamenti: vedi **[GUIDA.md](GUIDA.md)**.

> I dati veri (persone, saldi, email, PIN) non vanno mai su GitHub: stanno solo in `dati/` sul server.
> Per conservarli usa *Amministrazione → Backup*.
