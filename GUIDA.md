# Caffè Lab: guida all'installazione

Web app per segnare caffè e acqua con il telefono. Si scansiona il QR, si tocca **+** su quello che si è preso (anche più cose insieme, per esempio 2 caffè e 1 acqua) e poi **Conferma**: il saldo si aggiorna. Ogni persona ha **un solo saldo** per caffè e acqua. Ogni operazione resta registrata, e l'Excel con saldi e movimenti si scarica con un clic.

Prodotti di partenza (prezzi e nomi si cambiano da *Amministrazione*):

| Prodotto | Prezzo | Chi paga |
|---|---|---|
| ☕ Caffè | 0,30 € | chi lo prende |
| 💧 Acqua | 0,25 € | chi la prende |
| 🫗 Acqua macchinetta | 0,25 € | il **Conto Caffè** (conto comune creato in automatico) |

## Cosa c'è nella cartella

| File | A cosa serve |
|---|---|
| `app.py` | La web app |
| `gestione.py` | Comandi da console: importare i saldi, nominare l'amministratore, azzerare un PIN, mandare gli avvisi |
| `lingue.py` | Le traduzioni in inglese (per aggiungere o correggere una frase) |
| `saldi_iniziali.csv` | I saldi del foglio cartaceo, già calcolati (vedi sotto) |
| `templates/`, `static/` | Pagine e grafica |
| `test_app.py` | Test automatici (facoltativi) |
| `dati/` | Si crea da sola al primo avvio: contiene il database. **Non cancellarla mai.** |

## 0. I saldi iniziali

`saldi_iniziali.csv` contiene i saldi del file Excel controllato (foglio *Conto completo*). Ci sono due colonne, `saldo_caffe` e `saldo_acqua`: all'import vengono sommate nel saldo unico, ma restano visibili come due movimenti separati ("Saldo iniziale (foglio caffè)" e "(foglio acqua)").
Acqua e Cassa sono conti comuni: compaiono nei saldi ma nessuno ci entra con il PIN. Il **Conto Caffè** (che paga l'acqua per la macchinetta) lo crea l'app da sola.

Se lo modifichi da Excel, salvalo come **CSV (separato da punto e virgola)**.

## 1. Crea l'account gratuito

1. Crea un account *Beginner* (gratis) su **https://www.pythonanywhere.com** oppure su **https://eu.pythonanywhere.com** (server in Europa).
2. Il nome utente finisce nell'indirizzo dell'app: `https://NOMEUTENTE.pythonanywhere.com` oppure, sul server europeo, `https://NOMEUTENTE.eu.pythonanywhere.com`. **L'indirizzo giusto è quello scritto in cima alla scheda Web**: usalo ovunque in questa guida al posto di `INDIRIZZO`.

## 2. Carica i file

1. Scheda **Files** → **Upload a file** → carica `caffe-lab.zip`.
2. Scheda **Consoles** → **Bash**. Nella console scrivi (una riga alla volta):

```bash
unzip caffe-lab.zip
cd caffe-lab
pip3.12 install --user -r requirements.txt
python3.12 gestione.py importa saldi_iniziali.csv
python3.12 gestione.py elenco
```

L'ultimo comando mostra l'elenco con un numero (id) per ogni persona. Trova il tuo e renditi amministratore, per esempio:

```bash
python3.12 gestione.py admin 22
```

> Qui uso Python **3.12**. Se nel passo 3 scegli un'altra versione, usa lo stesso numero ovunque (`pip3.13`, `python3.13`, …).

## 3. Crea la web app

1. Scheda **Web** → **Add a new web app** → *Next* → **Manual configuration** → **Python 3.12** → *Next*.
2. Nella pagina che si apre, sezione **Code**:
   - *Source code*: `/home/NOMEUTENTE/caffe-lab`
   - *Working directory*: `/home/NOMEUTENTE/caffe-lab`
   - Clicca sul link del **WSGI configuration file**, **cancella tutto** il contenuto e incolla questo (sostituendo NOMEUTENTE), poi *Save*:

```python
import os, sys
CARTELLA = "/home/NOMEUTENTE/caffe-lab"
if CARTELLA not in sys.path:
    sys.path.insert(0, CARTELLA)
os.environ["CAFFE_HTTPS"] = "1"
from app import app as application
```

3. Sezione **Static files**: aggiungi una riga con URL `/static/` e Directory `/home/NOMEUTENTE/caffe-lab/static/`.
4. Sezione **Security**: attiva **Force HTTPS**.
5. In alto premi il pulsante verde **Reload**.

## 4. Email del lunedì (consigliata)

Ogni lunedì dalle 8:00 chi ha il saldo negativo vede nell'app un riquadro rosso con il messaggio
**SALDA IL DEBITO, COMPRA IL CREDITO DI UN ALTRO UTENTE O COMPRA UNO DEI BENI** e tre pulsanti per farlo. Questo funziona subito, senza configurare nulla.

Per mandare lo stesso messaggio anche **per email** serve un account Gmail che faccia da mittente:

1. Crea (o usa) un account Gmail per il gruppo, per esempio `caffelab.unipg@gmail.com`.
2. Attiva la **verifica in due passaggi** e poi crea una **password per le app** (Account Google → Sicurezza → Password per le app). Google mostra 16 lettere: copiale.
3. Nel **WSGI configuration file** (passo 3) aggiungi queste righe **prima** di `from app import …`, poi premi **Reload**:

```python
os.environ["CAFFE_URL"] = "https://INDIRIZZO/"
os.environ["CAFFE_SMTP_USER"] = "caffelab.unipg@gmail.com"
os.environ["CAFFE_SMTP_PASSWORD"] = "abcd efgh ijkl mnop"   # la password per le app
```

4. Nell'app vai su **Profilo ed email**, inserisci la tua email, poi **Amministrazione → Avviso del lunedì → Email di prova a me**.

Ognuno inserisce la propria email al primo accesso o dal **Profilo** (e lì può anche disattivare l'avviso per email). Chi non mette l'email vede comunque l'avviso nell'app.

**Quando partono le email.** Il piano gratuito di PythonAnywhere non ha più le attività pianificate per gli account nuovi, quindi l'app manda le email da sola alla **prima pagina aperta da qualcuno dopo lunedì alle 8:00** (in pratica: il primo caffè del lunedì). Partono una sola volta a settimana.
Se vuoi un orario preciso anche quando nessuno apre l'app: aggiungi nel file WSGI `os.environ["CAFFE_CRON_TOKEN"] = "una-parola-segreta-lunga"` e fai chiamare ogni lunedì alle 8:30 l'indirizzo `https://INDIRIZZO/cron/avvisi?token=una-parola-segreta-lunga` da un servizio gratuito di cron online (per esempio cron-job.org).

## 5. Primo avvio

1. Apri `https://INDIRIZZO` dal telefono (se vedi "Coming Soon!" l'indirizzo non è quello della scheda Web: controlla il `.eu`).
2. Scegli il tuo nome, lascia vuoto il PIN e premi *Entra*: completi nome e cognome e scegli il PIN.
3. Vai su **Amministrazione → QR code**, stampa la pagina e attaccala vicino alla macchinetta.
4. Avvisa il gruppo: la prima volta ognuno sceglie il proprio nome dall'elenco e imposta un PIN; da lì in poi basta scansionare e toccare il pulsante.

## Come funziona per il gruppo

- **Acquisto**: per ogni prodotto ci sono − e +; si sceglie la quantità di ciascuno e si tocca **Conferma** una volta sola. Il pulsante mostra quanto va a proprio carico (l'acqua per la macchinetta va sul Conto Caffè). Per 10 minuti si può annullare l'intero acquisto.
- **Pagamenti tra persone**:
  - *Ho dato dei soldi a qualcuno*: se dai 5 € a chi è in credito, il tuo saldo sale di 5 € e il suo scende di 5 €.
  - *Mi prendo il debito di qualcuno*: ti accolli una parte del debito di un altro (come Massi con Martin sul foglio).
- **Ho comprato per il gruppo**: chi compra caffè o cialde registra la spesa e riceve il credito.
- **Saldi di tutti**: visibili a tutti, con il pulsante per scaricare l'**Excel** (fogli *Saldi* e *Movimenti*).
- **Avviso del lunedì**: se il saldo è negativo, dal lunedì compare il riquadro rosso con tre pulsanti:
  - *Salda il debito*: apre «Pagamenti tra persone» già compilato con l'importo del debito e la Cassa;
  - *Compra il credito di un altro*: stesso modulo con l'importo, scegli tu la persona in credito (sono elencate nel riquadro);
  - *Compra uno dei beni*: apre «Ho comprato per il gruppo».
  Si può nascondere fino al lunedì successivo con «Ho capito».
- **Profilo ed email**: la propria email per ricevere l'avviso anche per posta.
- **Lingua**: in alto a destra ci sono **IT / EN**. La scelta resta salvata per ogni persona (anche le email del lunedì arrivano nella sua lingua); al primo accesso l'app usa la lingua del telefono. Il cartello con il QR è in italiano e in inglese.
- **Dopo ogni caffè** compare: «Ricorda di lasciare pulito dopo aver consumato il caffè!».
- Chi ha dimenticato il PIN o ha cambiato telefono: l'amministratore lo azzera dalla sua scheda.

Per l'amministratore:

- **Manutenzione della macchinetta**: in *Amministrazione* ci sono i promemoria (all'inizio due esempi, *Pulizia della macchinetta* ogni 7 giorni e *Decalcificazione* ogni 30: cambiali, eliminali o aggiungine altri). Si imposta ogni quanti giorni e quando è stata fatta l'ultima volta. Quando scade, **solo gli amministratori** vedono un riquadro giallo in cima alla pagina principale; chi la fa tocca **Fatta** e il conteggio riparte. Resta lo storico di chi l'ha fatta e quando.
- Inoltre si possono cambiare prezzi e nomi dei prodotti, aggiungerne di nuovi o disattivarli, scegliere se un prodotto lo paga chi lo prende o un conto comune, segnare acquisti per conto di qualcuno, fare rettifiche e versamenti, aggiungere persone e scaricare il backup.

## Manutenzione

- **Ogni mese**: il piano gratuito spegne la web app se non viene rinnovata. Entra nella scheda **Web** e premi il pulsante per estenderla (*Run until 1 month from today*). Conviene mettersi un promemoria.
- **Backup**: ogni tanto scarica *Amministrazione → Backup* e conservalo.
- **Aggiornare l'app** (nuova versione dello zip) senza perdere niente: persone, saldi e movimenti stanno solo in `dati/`, che lo zip non contiene mai.
  1. *Amministrazione → Backup* (per prudenza);
  2. scheda **Files** → carica il nuovo `caffe-lab.zip` nella cartella principale;
  3. **Consoles → Bash**: `unzip -o caffe-lab.zip` (sovrascrive solo il codice; se lo zip contiene anche `requirements.txt` nuovo, poi `pip3.12 install --user -r caffe-lab/requirements.txt`);
  4. scheda **Web** → **Reload**.
  Al riavvio l'app aggiunge da sola le tabelle e le colonne nuove al database. **Non** rilanciare `gestione.py importa`. Il file WSGI non viene toccato.
  Se avevi già installato una versione precedente, i saldi del nuovo file aggiungili da *Amministrazione → Rettifica*, oppure ricomincia da zero: cancella la cartella `dati/` **solo se** nell'app non c'è ancora niente di importante, poi rifai l'import.
- Se qualcosa non va: nella scheda Web c'è il link all'**error log**.

## Provarla sul proprio PC (facoltativo)

```bash
pip install -r requirements.txt
python3 gestione.py importa saldi_iniziali.csv
python3 app.py
```

Poi apri http://localhost:5000. Per i test automatici: `pip install pytest` e `python3 -m pytest -q`.
