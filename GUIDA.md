# Caffè Lab: guida all'installazione

Web app per segnare caffè e acqua con il telefono. Si scansiona il QR, si tocca **+** su quello che si è preso (anche più cose insieme, per esempio 2 caffè e 1 acqua) e poi **Conferma**: il saldo si aggiorna. Ogni persona ha **un solo saldo** per caffè e acqua. Ogni operazione resta registrata, e l'Excel con saldi e movimenti si scarica con un clic.

Prodotti di partenza (prezzi e nomi si cambiano da *Amministrazione*):

| Prodotto | Prezzo | Chi paga |
|---|---|---|
| ☕ Caffè | 0,30 € | chi lo prende |
| 💧 Acqua | 0,25 € | chi la prende |
| 🫗 Acqua macchinetta | 0,25 € | la **Macchinetta del caffè** (conto comune creato in automatico) |
| 🥤 Bicchierino vuoto | gratis | nessuno (serve solo a contare i bicchierini) |

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
Acqua e Cassa sono conti comuni: compaiono nei saldi ma nessuno ci entra con il PIN. La **Macchinetta del caffè** (il conto comune che paga l'acqua per la macchinetta; prima si chiamava *Conto Caffè* e l'app lo rinomina da sola) la crea l'app da sola.

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

**Da chi arriva.** Il mittente è l'account Gmail di `CAFFE_SMTP_USER`, con il nome dell'app: per esempio `Caffè Lab <caffelab.unipg@gmail.com>`. Lo vedi anche in **Amministrazione → Avviso del lunedì** alla voce *Email*. Se qualcuno non la trova, deve cercarla nello spam, con l'oggetto *Caffè Lab: il tuo saldo è …*.

**Come provarla senza disturbare nessuno.** Segui questi passi, in ordine:

1. **Prova a secco.** In **Amministrazione → Avviso del lunedì** apri *Prova a secco*. La pagina mostra il mittente e chi è in negativo adesso. Per ognuno dice se riceverebbe l'email, oppure perché no: non ha l'email, o ha tolto la spunta nel Profilo. Con *Vedi il testo* leggi l'email esatta che riceverebbe. **Non viene spedito nulla** e l'invio automatico del lunedì non cambia. Funziona anche prima di configurare l'email.
2. **Email di prova a te.** Con il pulsante *Email di prova a me* arriva solo a te un avviso con oggetto *[PROVA]*. Se il tuo saldo non è negativo, l'app finge un saldo di −4,20 €. Se arriva, mittente e password sono giusti. Se non arriva, il messaggio in alto dice l'errore (di solito la password per le app).
3. **Invio vero, solo se serve.** *Invia adesso a tutti* manda subito l'avviso a tutti quelli che la prova a secco segna come *riceve l'email*. Non sposta l'invio automatico del lunedì: chi è ancora in negativo lo riceve di nuovo lunedì.

Le stesse prove si fanno anche dalla console Bash. La console non legge il file WSGI: per spedire la copia di prova scrivi prima le due variabili `export`, con gli stessi valori del WSGI.

```bash
cd ~/caffe-lab
export CAFFE_SMTP_USER="caffelab.unipg@gmail.com" CAFFE_SMTP_PASSWORD="abcd efgh ijkl mnop"
python3.12 gestione.py avvisi-prova                  # prova a secco: elenco e testo, non spedisce nulla
python3.12 gestione.py avvisi-prova tu@esempio.it    # una sola copia [PROVA] a quell'indirizzo
```

## 5. Primo avvio

1. Apri `https://INDIRIZZO` dal telefono (se vedi "Coming Soon!" l'indirizzo non è quello della scheda Web: controlla il `.eu`).
2. Scegli il tuo nome, lascia vuoto il PIN e premi *Entra*: completi nome e cognome e scegli il PIN.
3. Vai su **Amministrazione → QR code**, stampa la pagina e attaccala vicino alla macchinetta.
4. Avvisa il gruppo: la prima volta ognuno sceglie il proprio nome dall'elenco e imposta un PIN; da lì in poi basta scansionare e toccare il pulsante.

## 6. Il proprio profilo: email e metodo di pagamento

Ognuno lo imposta dal telefono, quando vuole (anche più volte):

1. Nella pagina principale tocca **👤 Profilo ed email**.
2. **Email**: scrivi il tuo indirizzo (es. `nome.cognome@studenti.unipg.it`). Serve per ricevere per email l'avviso del lunedì quando il saldo è negativo e, per gli amministratori, il backup settimanale. Se non vuoi l'email, togli la spunta *Mandami per email l'avviso del lunedì…*: l'avviso lo vedi comunque nell'app.
3. **Come vuoi essere pagato** (facoltativo): serve a chi deve darti dei soldi.
   - **PayPal**: il tuo nome di paypal.me, cioè quello dopo `paypal.me/` (es. `mariorossi`). Va bene anche incollare il link intero (`https://paypal.me/mariorossi`) oppure scrivere l'email del conto PayPal. Con il nome, nella tua scheda compare il link diretto per pagarti.
   - **IBAN**: anche con spazi e lettere minuscole. L'app controlla le cifre di controllo: se c'è un errore di battitura non lo salva e te lo dice, così nessuno fa un bonifico sbagliato.
4. Tocca **Salva**.
5. Per vedere cosa vedono gli altri, tocca **Vedi la tua scheda** in cima al profilo. Per togliere PayPal o IBAN, svuota il campo e tocca **Salva**.

PayPal e IBAN li vede solo chi ha fatto l'accesso all'app, nella tua scheda: si apre toccando il tuo nome in *Saldi di tutti* o scegliendoti in *Pagamenti tra persone*. Non compaiono nella lista dei saldi né nell'Excel. La lingua (IT / EN) si cambia in alto a destra.

## Come funziona per il gruppo

- **Acquisto**: per ogni prodotto ci sono − e +; si sceglie la quantità di ciascuno e si tocca **Conferma** una volta sola. Il pulsante mostra quanto va a proprio carico (l'acqua per la macchinetta va sulla Macchinetta del caffè). Per 10 minuti si può annullare l'intero acquisto. Sotto *Acqua macchinetta* e *Bicchierino vuoto* c'è una riga che spiega quando segnarli: l'acqua **solo quando si mette una bottiglia nuova nella macchinetta**, il bicchierino vuoto **solo se si prende un bicchierino senza caffè** (quello del caffè è già contato). Se si scelgono caffè e bicchierino vuoto insieme compare un avviso. Le spiegazioni si cambiano in *Amministrazione → Prodotti e prezzi*, nel campo *Spiegazione sotto il prodotto*.
- **Barra in basso**: in tutte le pagine tranne la principale, in fondo allo schermo restano sempre visibili **← Indietro** e **🏠 Home**, anche nelle pagine lunghe come i movimenti.
- **Pagamenti tra persone**:
  - *Ho dato dei soldi a qualcuno*: se dai 5 € a chi è in credito, il tuo saldo sale di 5 € e il suo scende di 5 €. **Conta solo quando chi ha ricevuto i soldi conferma** dalla pagina *Richieste* (per la Cassa conferma un amministratore). Vale anche quando paga un amministratore: nessuno può confermare un proprio pagamento.
  - *Mi prendo il debito di qualcuno*: ti accolli una parte del debito di un altro (come Massi con Martin sul foglio). Vale subito, perché pesa solo su di te.
- **Ho comprato per il gruppo**: chi compra caffè o cialde registra la spesa. **Il credito arriva quando un amministratore la approva.** Vale anche per gli amministratori: la spesa di un admin la approva **un altro admin**; solo se nell'app c'è un unico amministratore, può approvarla lui stesso. Per la merce del magazzino (cialde, bottiglie, bicchierini) bisogna scrivere **quanti pezzi** e quanto sono costati; tutto il resto va in *Altro* con descrizione e costo. Il totale lo calcola l'app.
- **Richieste**: qui ognuno conferma i pagamenti ricevuti e vede le proprie richieste in attesa (che può annullare). Gli amministratori vedono anche spese e nuovi accessi da approvare, e i pagamenti tra persone fermi da più di 3 giorni, che possono confermare al posto di chi doveva riceverli (tranne i propri); in cima alla pagina principale compare un avviso quando c'è qualcosa da fare.
- **Come funziona**: pagina con le regole, come rientrare dal debito e le linee guida per la pulizia. Si apre anche senza aver fatto l'accesso: puoi mandarne il link a chi deve iniziare.
- **Saldi di tutti**: visibili a tutti, con il pulsante per scaricare l'**Excel** (fogli *Saldi* e *Movimenti*).
- **Statistiche**: quanti caffè, acque e altri prodotti si consumano per giorno (ultimi 14), settimana (ultime 12), mese (ultimi 12) e anno, dal più recente, con i totali di oggi, della settimana, del mese e dell'anno e la media al giorno degli ultimi 30 giorni. Si vedono i consumi di tutti insieme, di una persona sola o di un conto comune: sono visibili a chiunque abbia fatto l'accesso. Contano solo gli acquisti segnati nell'app (non il foglio cartaceo). Come nel saldo, l'acqua per la macchinetta conta sulla **Macchinetta del caffè** (si può scegliere in «Consumi di»), non su chi l'ha presa.
- **Avviso del lunedì**: se il saldo è negativo, dal lunedì compare il riquadro rosso con tre pulsanti:
  - *Salda il debito*: apre «Pagamenti tra persone» già compilato con l'importo del debito e la Cassa;
  - *Compra il credito di un altro*: stesso modulo con l'importo, scegli tu la persona in credito (sono elencate nel riquadro);
  - *Compra uno dei beni*: apre «Ho comprato per il gruppo».
  Si può nascondere fino al lunedì successivo con «Ho capito».
- **Profilo ed email**: la propria email per ricevere l'avviso anche per posta, e (facoltativi) **PayPal** e **IBAN** per dire come si vuole essere pagati. Come si imposta: vedi il passo 6 qui sopra.
- **Novità e comunicazioni**: dopo ogni aggiornamento in home compare il riquadro blu **«Novità dell'aggiornamento»** con le novità in breve: si spunta **Ho letto** e sparisce fino all'aggiornamento successivo. Le comunicazioni degli amministratori compaiono allo stesso modo in un riquadro viola 📣, una per volta, ognuna con la sua spunta.
- **Scheda della persona**: toccando un nome in *Saldi di tutti* (o tra chi è in credito nell'avviso del lunedì) si apre la sua scheda con nome, cognome, saldo e come vuole essere pagato. In *Pagamenti tra persone* la scheda compare da sola appena si sceglie la persona. PayPal e IBAN li vede solo chi ha fatto l'accesso all'app, e non finiscono nell'Excel.
- **Lingua**: in alto a destra ci sono **IT / EN**. La scelta resta salvata per ogni persona (anche le email del lunedì arrivano nella sua lingua); al primo accesso l'app usa la lingua del telefono. Il cartello con il QR è in italiano e in inglese.
- **Dopo ogni caffè** compare: «Ricorda di lasciare pulito dopo aver consumato il caffè!».
- Chi ha dimenticato il PIN o ha cambiato telefono: l'amministratore lo azzera dalla sua scheda.

Per l'amministratore:

- **Nuovi accessi**: il primo accesso di ogni persona (e ogni nuova registrazione) resta in attesa finché un amministratore non lo approva da *Richieste*. Se qualcuno attiva l'account di un altro, rifiutalo: l'account torna libero per il vero proprietario. Chi era già entrato prima di questo aggiornamento resta attivo.
- **Comunicazioni e messaggi** (*Amministrazione*, in alto): scrivi il testo, scegli **A tutti** oppure **Solo a persone scelte** (spunti i nomi dall'elenco, con la ricerca) e premi **Pubblica**. Compare in home come notifica finché ognuno non spunta *Ho letto*: i messaggi personali li vedono solo i destinatari, con la scritta ✉️ *Messaggio per te*. Nell'elenco vedi a chi l'hai mandata e da quante persone è stata letta; con **Ritira** sparisce per tutti. Per scrivere a una persona sola si fa prima dalla sua scheda (tocca il nome in *Saldi di tutti*): *✉️ Scrivi un messaggio a …*.
- **Registro approvazioni** (*Amministrazione → Registro approvazioni*, solo admin): per ogni accesso, spesa e pagamento approvato, rifiutato o annullato mostra chi l'ha chiesto, chi ha deciso e quando. Lo storico completo è anche nel foglio *Approvazioni* dell'Excel, che compare solo quando lo scarica un admin. I versamenti di un admin ai conti comuni (che valgono subito) compaiono come "registrata direttamente dall'admin"; le spese approvate da chi le aveva registrate (unico admin, o spese di prima di questo aggiornamento) come "l'admin che l'ha registrata". Gli accessi approvati prima di questo aggiornamento non sono nel registro.
- **Limite di debito**: in *Amministrazione* scegli l'importo (0 = nessun limite) e cosa succede oltre il limite: *avvisa e chiedi conferma* (consigliato) oppure *blocca gli acquisti*. Chi è oltre il limite vede un avviso rosso fisso.
- **Magazzino** (*Amministrazione → Magazzino*): per ogni articolo (cialde, bottiglie, bicchierini, e altri che puoi aggiungere) la quantità scende da sola a ogni acquisto e sale quando approvi una spesa con la merce. Ogni caffè scala 1 cialda e 1 bicchierino, ogni acqua (anche quella per la macchinetta) 1 bottiglia, ogni bicchierino vuoto 1 bicchierino: si cambia nella tabella *Cosa consuma ogni prodotto*. Quando conti i pezzi veri scrivili in *Pezzi contati*: la differenza resta nel registro. Quando un articolo arriva alla **soglia**, gli amministratori e chi è in debito vedono in home il riquadro «Sta finendo la merce» con il pulsante per registrare l'acquisto. Finché un articolo non è stato contato almeno una volta l'avviso non compare.
- **Bilancio** (*Amministrazione → Bilancio*, solo admin): per ogni articolo mette in fila, in pezzi e in euro, *iniziale (prima conta) + comprati − consumati ± differenze delle conte = in magazzino*. Gli euro sono al **costo medio** di un pezzo nelle spese approvate (finché non c'è una spesa con quell'articolo il costo è «—»). Le **differenze delle conte** sono i pezzi spariti tra il calcolo dell'app e la conta vera: di solito caffè non segnati. Per ogni prodotto mostra quanto ha incassato, quanto è costata la sua merce e il margine, anche per pezzo (prezzo − costo della ricetta): se il margine è negativo il prezzo non copre i costi.
- **Manutenzione della macchinetta**: in *Amministrazione* ci sono i promemoria (all'inizio due esempi, *Pulizia della macchinetta* ogni 7 giorni e *Decalcificazione* ogni 30: cambiali, eliminali o aggiungine altri). Si imposta ogni quanti giorni e quando è stata fatta l'ultima volta. Quando scade, **solo gli amministratori** vedono un riquadro giallo in cima alla pagina principale; chi la fa tocca **Fatta** e il conteggio riparte. Resta lo storico di chi l'ha fatta e quando.
- **Backup settimanale**: ogni lunedì dalle 8:00 gli amministratori che hanno l'email nel *Profilo* ricevono un'email con due allegati: l'**Excel** (saldi, movimenti, approvazioni) e il **database completo** (`caffe_backup_AAAA-MM-GG.db`), che serve per il ripristino. Il primo parte subito dopo l'aggiornamento che lo introduce. In *Amministrazione → Backup settimanale* vedi chi lo riceve, l'esito dell'ultimo invio e il pulsante **Invia il backup adesso**. Serve che le email siano configurate (passo 4). L'email contiene i dati del gruppo e i PIN cifrati: non inoltrarla.
- Inoltre si possono cambiare prezzi e nomi dei prodotti, aggiungerne di nuovi o disattivarli, scegliere se un prodotto lo paga chi lo prende o un conto comune, segnare acquisti per conto di qualcuno, fare rettifiche e versamenti, aggiungere persone e scaricare il backup.

## Manutenzione

- **Ogni mese**: il piano gratuito spegne la web app se non viene rinnovata. Entra nella scheda **Web** e premi il pulsante per estenderla (*Run until 1 month from today*). Conviene mettersi un promemoria.
- **Backup**: arriva da solo ogni lunedì per email agli amministratori (vedi sopra). Conserva quelle email, magari in una cartella apposta. In qualsiasi momento puoi anche scaricarlo da *Amministrazione → Backup*.
- **Aggiornare l'app** (nuova versione dello zip) senza perdere niente: persone, saldi e movimenti stanno solo in `dati/`, che lo zip non contiene mai.
  1. **Prepara lo zip**, in uno di questi due modi:
     - **Da GitHub (consigliato).** Prima fai il push delle modifiche. Poi sul repository: scheda **Actions** → a sinistra **Zip per PythonAnywhere** → **Run workflow** (branch `main`; le note sono facoltative) → **Run workflow**. In un paio di minuti esegue i test e, solo se passano tutti, crea una **Release** con lo zip `caffe-lab_AAAA-MM-GG.zip`. La trovi nella pagina **Releases** del repository (colonna a destra della pagina principale): scarica lo zip da *Assets*. Le versioni vecchie restano lì: se un aggiornamento dà problemi, ricarica lo zip della release precedente.
     - **Dal PC**, dalla cartella della repository (dopo il commit):
       `git -c core.autocrlf=false archive --format=zip --prefix=caffe-lab/ -o ../caffe-lab_AAAA-MM-GG.zip HEAD`.

     Non usare «Download ZIP» di GitHub: dentro la cartella si chiamerebbe `CaffeLabCosmac-main` e sul server resterebbe la versione vecchia. Va bene invece lo zip in *Assets* della release, non i «Source code» accanto.
     Se l'aggiornamento cambia qualcosa che si vede, prima aggiungi due righe in cima a `novita.py`: compaiono a tutti nel riquadro «Novità dell'aggiornamento» (e nelle note della release).
  2. scheda **Files** → carica lo zip nella cartella principale;
  3. **Consoles → Bash**, un comando alla volta (backup del database, scompatta lo zip più recente sopra il codice, riavvia):
     ```bash
     cd ~
     python3.12 -c "import sqlite3,datetime; s=sqlite3.connect('caffe-lab/dati/caffe.db'); n=f'caffe_backup_{datetime.datetime.now():%Y-%m-%d_%H%M}.db'; d=sqlite3.connect(n); s.backup(d); d.close(); print('Backup OK:', n)"
     ZIP=$(ls -t caffe-lab*.zip | head -1); echo "Uso: $ZIP"
     unzip -o "$ZIP"
     touch /var/www/*_wsgi.py && echo "OK: aggiornato e riavviato"
     ```
     Se lo zip contiene un `requirements.txt` cambiato, prima del riavvio: `pip3.12 install --user -r caffe-lab/requirements.txt`.
  Al riavvio l'app aggiunge da sola le tabelle e le colonne nuove al database. **Non** rilanciare `gestione.py importa`. Il file WSGI non viene toccato.
  Dopo l'aggiornamento che introduce il magazzino: vai in *Amministrazione → Magazzino*, conta cialde, bottiglie e bicchierini e scrivi le quantità in *Pezzi contati*, poi controlla le soglie.
  Se avevi già installato una versione precedente, i saldi del nuovo file aggiungili da *Amministrazione → Rettifica*, oppure ricomincia da zero: cancella la cartella `dati/` **solo se** nell'app non c'è ancora niente di importante, poi rifai l'import.
- Se qualcosa non va: nella scheda Web c'è il link all'**error log**.

### Ripristino da un backup

Serve solo se l'account PythonAnywhere si perde o il database si rovina.

1. Se l'account è nuovo, rifai i passi 1, 2 e 3 (account, file, web app e file WSGI), ma **non** fare il passo 0 (`gestione.py importa`).
2. Prendi il file `.db` più recente dalle email del backup e caricalo dalla scheda **Files** nella cartella principale.
3. **Consoles → Bash** (cambia la data con quella del tuo file):

```bash
mkdir -p ~/caffe-lab/dati
mv ~/caffe_backup_2026-11-16.db ~/caffe-lab/dati/caffe.db
touch /var/www/*_wsgi.py && echo "OK: ripristinato"
```

4. Apri l'app: saldi, movimenti, persone, PIN e amministratori sono come al momento del backup. Se l'account è nuovo, ognuno rientra una volta con nome e PIN.
5. Se l'indirizzo è cambiato (nuovo nome utente), aggiorna `CAFFE_URL` nel file WSGI e ristampa il QR.

## Provarla sul proprio PC (facoltativo)

```bash
pip install -r requirements.txt
python3 gestione.py importa saldi_iniziali.csv
python3 app.py
```

Poi apri http://localhost:5000. Per i test automatici: `pip install pytest` e `python3 -m pytest -q`.

Per non dover attivare un account e farlo approvare, `python3 app.py` crea da solo l'utente **root**, amministratore già approvato, con PIN **0000**: sceglilo nell'elenco di *Accedi*. Per un altro PIN: `CAFFE_ROOT_PIN=1234 python3 app.py`; per non crearlo: `CAFFE_ROOT=0 python3 app.py`. Sul server l'app parte dal file WSGI e root non viene mai creato. Però, se l'hai creato sul PC, **non caricare quel `caffe.db` sul server**: root resterebbe amministratore con PIN 0000.
