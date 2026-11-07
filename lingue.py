"""
Traduzioni dell'interfaccia. La chiave è il testo italiano usato nel codice,
il valore è la traduzione inglese. Per aggiungere una frase nuova:
scrivila in italiano nel codice dentro _("..."), poi aggiungila qui sotto.
Se una traduzione manca, compare il testo italiano.
"""

LINGUE = ["it", "en"]

EN = {
    # --- accesso e account ---
    "Chi sei?": "Who are you?",
    "Lo chiediamo solo la prima volta: poi questo telefono si ricorda di te.":
        "We only ask the first time: after that this phone remembers you.",
    "Il tuo nome": "Your name",
    "— scegli —": "— choose —",
    "primo accesso": "first login",
    "Lascia vuoto se è il primo accesso": "Leave empty if this is your first login",
    "Entra": "Log in",
    "Non sei nell'elenco?": "Not on the list?",
    "Registrati": "Sign up",
    "Primo accesso": "First login",
    "Controlla nome e cognome e scegli un PIN di 4–8 cifre. Ti servirà solo se cambi telefono o esci.":
        "Check your first and last name and choose a 4–8 digit PIN. You will only need it if you change phone or log out.",
    "(facoltativa: serve per l'avviso del lunedì)": "(optional: used for the Monday reminder)",
    "Nuovo PIN": "New PIN",
    "Ripeti il PIN": "Repeat the PIN",
    "Attiva il mio account": "Activate my account",
    "Non sono {nome}": "I'm not {nome}",
    "Nuovo account": "New account",
    "Solo se il tuo nome non è già nell'elenco della pagina di accesso.":
        "Only if your name is not already on the list on the login page.",
    "PIN (4–8 cifre)": "PIN (4–8 digits)",
    "Crea account": "Create account",
    "Torna all'accesso": "Back to login",
    "Nome": "First name",
    "Cognome": "Last name",
    "Esci": "Log out",
    "Lingua": "Language",
    "Scegli il tuo nome dall'elenco.": "Choose your name from the list.",
    "Troppi tentativi sbagliati: riprova tra qualche minuto.": "Too many wrong attempts: try again in a few minutes.",
    "PIN sbagliato.": "Wrong PIN.",
    "Questo account è già stato attivato. Se non sei stato tu, avvisa l'amministratore.":
        "This account has already been activated. If it wasn't you, tell the administrator.",
    "Account attivato! Da ora questo telefono si ricorda di te.": "Account activated! From now on this phone remembers you.",
    "Benvenuto! Il tuo account è pronto.": "Welcome! Your account is ready.",
    "Sei uscito. Per rientrare scegli il tuo nome e inserisci il PIN.":
        "You are logged out. To log back in, choose your name and enter your PIN.",
    "Inserisci nome e cognome.": "Enter your first and last name.",
    "Il PIN deve avere da 4 a 8 cifre.": "The PIN must have 4 to 8 digits.",
    "I due PIN non coincidono.": "The two PINs don't match.",
    "Indirizzo email non valido (puoi anche lasciarlo vuoto).": "Invalid email address (you can also leave it empty).",
    "Esiste già una persona con questo nome: cercala nell'elenco della pagina di accesso.":
        "Someone with this name already exists: look for it in the list on the login page.",

    # --- pagina principale ---
    "Ciao {nome}": "Hi {nome}",
    "il tuo debito": "you owe",
    "il tuo credito": "your credit",
    "sei in pari": "you're even",
    "Conferma": "Confirm",
    "Scegli con il +": "Choose with +",
    "a tuo carico": "you pay",
    "conto comune": "shared account",
    "a carico del {conto}": "paid by {conto}",
    "Togli uno": "Remove one",
    "Aggiungi uno": "Add one",
    "Ultimo:": "Last:",
    "Annulla": "Undo",
    "Saldi di tutti": "Everyone's balances",
    "Pagamenti tra persone": "Payments between people",
    "Ho comprato per il gruppo": "I bought for the group",
    "I miei movimenti": "My transactions",
    "Profilo ed email": "Profile & email",
    "Amministrazione": "Administration",
    "Ultimi movimenti": "Latest transactions",
    "registrato da {nome}": "recorded by {nome}",
    "annullato": "cancelled",
    "Puoi segnare al massimo {n} pezzi per prodotto.": "You can log at most {n} items per product.",
    "Scegli almeno un prodotto con il +.": "Choose at least one product with +.",
    "{cosa} a carico del {conto}": "{cosa} paid by {conto}",
    "Segnato: {cosa}{extra}. Il tuo saldo: {saldo}": "Logged: {cosa}{extra}. Your balance: {saldo}",
    "Questo movimento non si può più annullare. Chiedi all'amministratore.":
        "This transaction can no longer be undone. Ask the administrator.",
    "Movimento annullato.": "Transaction cancelled.",
    "Ricorda di lasciare pulito dopo aver consumato il caffè!": "Remember to leave it clean after having your coffee!",

    # --- avviso del lunedì ---
    "Avviso del lunedì": "Monday reminder",
    "Avviso del lunedì · il tuo saldo è {saldo}": "Monday reminder · your balance is {saldo}",
    "SALDA IL DEBITO, COMPRA IL CREDITO DI UN ALTRO UTENTE O COMPRA UNO DEI BENI":
        "SETTLE YOUR DEBT, BUY ANOTHER USER'S CREDIT OR BUY ONE OF THE GOODS",
    "Salda il debito": "Settle your debt",
    "Compra il credito di un altro": "Buy someone else's credit",
    "Compra uno dei beni": "Buy one of the goods",
    "In credito ora:": "In credit now:",
    "Ho capito, nascondi fino a lunedì prossimo": "Got it, hide until next Monday",

    # --- manutenzione ---
    "Manutenzione della macchinetta": "Coffee machine maintenance",
    "Manutenzione della macchinetta da fare": "Coffee machine maintenance due",
    "Quando un lavoro è da fare, gli amministratori lo vedono in cima alla pagina principale. Con «Fatta» il conteggio riparte da oggi.":
        "When a job is due, administrators see it at the top of the main page. Tapping “Done” restarts the count from today.",
    "Lavoro": "Job",
    "ogni": "every",
    "Giorni": "Days",
    "giorni": "days",
    "ogni {n} giorni": "every {n} days",
    "ultima volta {n} giorni fa": "last done {n} days ago",
    "Ultima volta": "Last done",
    "Disattivato": "Disabled",
    "Da fare: scaduto da {n} giorni": "Due: overdue by {n} days",
    "Prossima: tra {n} giorni": "Next: in {n} days",
    "ultima fatta da {nome}": "last done by {nome}",
    "Eliminare questo promemoria e il suo storico?": "Delete this reminder and its history?",
    "Elimina": "Delete",
    "Fatta": "Done",
    "Fatta oggi: {nome}": "Done today: {nome}",
    "Aggiungi un promemoria": "Add a reminder",
    "es. Cambio filtro acqua": "e.g. Change water filter",
    "Ultime manutenzioni fatte": "Latest maintenance done",
    "Segnata come fatta: {nome}. Il prossimo promemoria tra {giorni} giorni.":
        "Marked as done: {nome}. Next reminder in {giorni} days.",
    "Servono un nome e un numero di giorni tra 1 e 730.": "A name and a number of days between 1 and 730 are required.",
    "Promemoria aggiunto: {nome}, ogni {giorni} giorni.": "Reminder added: {nome}, every {giorni} days.",
    "Promemoria eliminato: {nome}.": "Reminder deleted: {nome}.",
    "Data non valida (non può essere nel futuro).": "Invalid date (it can't be in the future).",
    "Promemoria aggiornato: {nome}.": "Reminder updated: {nome}.",
    "Pulizia della macchinetta": "Machine cleaning",
    "Decalcificazione": "Descaling",

    # --- amministrazione ---
    "Ogni lunedì (dalle 8:00) chi ha il saldo negativo vede in app il messaggio «{testo}».":
        "Every Monday (from 8:00) anyone with a negative balance sees the message “{testo}” in the app.",
    "Lo riceve anche per email.": "They also receive it by email.",
    "In negativo adesso:": "Negative right now:",
    "{n} senza email: vedono solo l'avviso in app": "{n} without email: they only see the in-app reminder",
    "attiva": "on",
    "mittente": "sender",
    "non configurata": "not set up",
    "vedi la guida, passo «Email del lunedì»": "see the guide, step “Monday email”",
    "Ultimo invio:": "Last sent:",
    "{n} email inviate su {tot}": "{n} of {tot} emails sent",
    "Errori: {errori}": "Errors: {errori}",
    "Email di prova a me": "Test email to me",
    "Invia adesso a tutti": "Send to everyone now",
    "Prodotti e prezzi": "Products and prices",
    "Un nuovo prezzo vale solo per gli acquisti da ora in poi. Si può scegliere se paga chi lo prende oppure un conto comune (es. l'acqua per la macchinetta la paga il Conto Caffè).":
        "A new price only applies to purchases from now on. You can choose whether the person who takes it pays, or a shared account (e.g. machine water is paid by the Coffee account).",
    "Nome prodotto": "Product name",
    "Prezzo in euro": "Price in euro",
    "Chi paga": "Who pays",
    "Paga chi lo prende": "Paid by whoever takes it",
    "Paga il {conto}": "Paid by {conto}",
    "Attivo": "Active",
    "Attivo (visibile a tutti)": "Active (visible to everyone)",
    "Aggiungi un prodotto": "Add a product",
    "Aggiungi": "Add",
    "Salva": "Save",
    "Segna un acquisto per conto di qualcuno": "Log a purchase on someone's behalf",
    "Per chi non ha il telefono, o per caricare qualcosa direttamente su un conto comune.":
        "For people without a phone, or to charge something directly to a shared account.",
    "Persona": "Person",
    "— persona o conto —": "— person or account —",
    "Prodotto": "Product",
    "Quantità": "Quantity",
    "Segna": "Log",
    "Rettifica / versamento": "Adjustment / deposit",
    "Per correggere un errore o registrare soldi versati a te o nella cassa. Importo positivo = più credito, negativo = più debito.":
        "To fix a mistake or record money paid to you or into the cash box. Positive amount = more credit, negative = more debt.",
    "es. 10 oppure -2,40": "e.g. 10 or -2.40",
    "Importo (€)": "Amount (€)",
    "Motivo (obbligatorio)": "Reason (required)",
    "Registra": "Save",
    "Persone e conti": "People and accounts",
    "conto": "account",
    "mai entrato": "never logged in",
    "non attivo": "inactive",
    "Aggiungi persona o conto": "Add person or account",
    "Saldo iniziale (facoltativo, es. -3,50)": "Starting balance (optional, e.g. -3.50)",
    "Saldo iniziale": "Starting balance",
    "Conto comune senza accesso (es. Cassa)": "Shared account without login (e.g. Cash box)",
    "Saldo attuale:": "Current balance:",
    "Email (per l'avviso del lunedì)": "Email (for the Monday reminder)",
    "Amministratore": "Administrator",
    "Conto senza accesso (es. Cassa)": "Account without login (e.g. Cash box)",
    "Se ha dimenticato il PIN o ha cambiato telefono, azzeralo: al prossimo accesso ne sceglierà uno nuovo.":
        "If they forgot the PIN or changed phone, reset it: they'll choose a new one at the next login.",
    "Non ha ancora fatto il primo accesso.": "They haven't logged in yet.",
    "Azzera PIN": "Reset PIN",
    "Email non configurata: vedi la guida (CAFFE_SMTP_USER e CAFFE_SMTP_PASSWORD).":
        "Email not set up: see the guide (CAFFE_SMTP_USER and CAFFE_SMTP_PASSWORD).",
    "Aggiungi prima la tua email nel Profilo.": "Add your email in your Profile first.",
    "Email di prova inviata a {email}.": "Test email sent to {email}.",
    "Invio non riuscito: {errore}": "Sending failed: {errore}",
    "Email non configurata: vedi la guida.": "Email not set up: see the guide.",
    "Avvisi inviati: {n} su {tot}.": "Reminders sent: {n} of {tot}.",
    "Servono un nome e un prezzo valido.": "A name and a valid price are required.",
    "{nome} aggiornato. Il prezzo vale per gli acquisti da ora in poi.":
        "{nome} updated. The price applies to purchases from now on.",
    "Prodotto aggiunto: {nome}.": "Product added: {nome}.",
    "Il nome è obbligatorio.": "The name is required.",
    "Saldo iniziale non valido.": "Invalid starting balance.",
    "Aggiunto: {nome}.": "Added: {nome}.",
    "Non puoi togliere a te stesso i permessi di amministratore o disattivarti.":
        "You can't remove your own administrator rights or deactivate yourself.",
    "Dati aggiornati.": "Details updated.",
    "PIN di {nome} azzerato: al prossimo accesso ne sceglierà uno nuovo.":
        "{nome}'s PIN reset: they'll choose a new one at the next login.",
    "Per la rettifica servono persona, importo (anche negativo) e motivo.":
        "An adjustment needs a person, an amount (negative allowed) and a reason.",
    "Rettifica registrata per {nome}: {importo}.": "Adjustment saved for {nome}: {importo}.",
    "Scegli persona, prodotto e una quantità valida.": "Choose a person, a product and a valid quantity.",
    "Segnato {cosa} a {nome}.": "Logged {cosa} for {nome}.",

    # --- saldi, movimenti, pagamenti, spese ---
    "Saldi": "Balances",
    "Debiti totali": "Total debts",
    "Crediti totali": "Total credits",
    "Ordina per:": "Sort by:",
    "nome": "name",
    "saldo": "balance",
    "nessun acquisto": "no purchases",
    "Scarica Excel": "Download Excel",
    "Movimenti": "Transactions",
    "Tutti i movimenti": "All transactions",
    "Solo i miei": "Only mine",
    "Vedi quelli di tutti": "See everyone's",
    "ultimi 300": "last 300",
    "Ancora nessun movimento.": "No transactions yet.",
    "Pagamenti": "Payments",
    "Dopo l'operazione: tu {mio}, {nome} passa da {da} a {a}.":
        "After this: you {mio}, {nome} goes from {da} to {a}.",
    "Ho dato dei soldi a qualcuno": "I gave money to someone",
    "Es. hai dato 5 € in contanti a chi è in credito: il tuo saldo sale, il suo scende.":
        "E.g. you gave €5 in cash to someone in credit: your balance goes up, theirs goes down.",
    "Mi prendo il debito di qualcuno": "I take over someone's debt",
    "Es. ti accolli i 4,18 € di un collega: il suo saldo sale, il tuo scende.":
        "E.g. you take on a colleague's €4.18: their balance goes up, yours goes down.",
    "es. 5 oppure 2,50": "e.g. 5 or 2.50",
    "Nota (facoltativa)": "Note (optional)",
    "Registrato. Il tuo saldo ora è {mio}; quello di {nome} è {suo}.":
        "Saved. Your balance is now {mio}; {nome}'s is {suo}.",
    "Scegli che tipo di operazione vuoi fare.": "Choose which kind of operation you want.",
    "Scegli la persona.": "Choose the person.",
    "Importo non valido (es. 5 oppure 2,50).": "Invalid amount (e.g. 5 or 2.50).",
    "Spesa": "Purchase",
    "Hai comprato caffè, cialde, zucchero o bicchierini per tutti? Registra la spesa: l'importo ti viene accreditato. La spesa è visibile a tutti nei movimenti.":
        "Did you buy coffee, pods, sugar or cups for everyone? Record the purchase: the amount is credited to you. Everyone can see it in the transactions.",
    "Cosa hai comprato": "What you bought",
    "es. 2 kg di caffè": "e.g. 2 kg of coffee",
    "Quanto hai speso (€)": "How much you spent (€)",
    "es. 18,90": "e.g. 18.90",
    "Registra la spesa": "Save the purchase",
    "Inserisci l'importo e cosa hai comprato.": "Enter the amount and what you bought.",
    "Spesa registrata. Nuovo saldo: {saldo}": "Purchase saved. New balance: {saldo}",
    "Profilo": "Profile",
    "Mandami per email l'avviso del lunedì quando il mio saldo è negativo":
        "Email me the Monday reminder when my balance is negative",
    "Per ora l'amministratore non ha ancora attivato le email: l'avviso lo vedi comunque qui nell'app.":
        "The administrator hasn't turned on emails yet: you'll still see the reminder here in the app.",
    "Indirizzo email non valido.": "Invalid email address.",
    "Profilo aggiornato.": "Profile updated.",
    "Torna indietro": "Back",

    # --- descrizioni dei movimenti ---
    "oggi {ora}": "today {ora}",
    "presa da {nome}": "taken by {nome}",
    "Saldo iniziale ({origine})": "Starting balance ({origine})",
    "Soldi dati a {nome}": "Money given to {nome}",
    "{nome} si è preso il tuo debito": "{nome} took over your debt",
    "Mi sono preso il debito di {nome}": "I took over {nome}'s debt",
    "Soldi ricevuti da {nome}": "Money received from {nome}",
    "Spesa per il gruppo: {cosa}": "Bought for the group: {cosa}",
    "Rettifica: {motivo}": "Adjustment: {motivo}",
    "foglio caffè": "coffee sheet",
    "foglio acqua": "water sheet",
    "foglio cartaceo": "paper sheet",
    "Caffè": "Coffee",
    "Acqua": "Water",
    "Acqua macchinetta": "Machine water",

    # --- Excel ---
    "Saldo (€)": "Balance (€)",
    "{nome} (n°)": "{nome} (qty)",
    "Tipo": "Type",
    "Ultimo movimento": "Last transaction",
    "Conto comune": "Shared account",
    "Sì": "Yes",
    "No": "No",
    "TOTALE": "TOTAL",
    "Data e ora": "Date and time",
    "Descrizione": "Description",
    "Registrato da": "Recorded by",
    "Annullato": "Cancelled",
    "acquisto": "purchase",
    "trasferimento": "transfer",
    "spesa": "group purchase",
    "rettifica": "adjustment",
    "iniziale": "starting balance",

    # --- errori ---
    "Ops": "Oops",
    "Torna alla pagina principale": "Back to the main page",
    "Sessione scaduta: ricarica la pagina e riprova.": "Session expired: reload the page and try again.",
    "Richiesta non valida.": "Invalid request.",
    "Questa pagina è riservata agli amministratori.": "This page is for administrators only.",
    "Pagina non trovata.": "Page not found.",

    # --- email del lunedì ---
    "nessuno al momento": "nobody right now",
    "{app}: il tuo saldo è {saldo}": "{app}: your balance is {saldo}",
    "Ciao {nome},": "Hi {nome},",
    "il tuo saldo su {app} è {saldo}.": "your balance on {app} is {saldo}.",
    "- Salda il debito: versa i soldi nella cassa e registralo nell'app":
        "- Settle your debt: put the money in the cash box and record it in the app",
    "  (Pagamenti tra persone → «Ho dato dei soldi a qualcuno» → Cassa).":
        "  (Payments between people → “I gave money to someone” → Cash box).",
    "- Compra il credito di un altro utente: dai i soldi a chi è in credito e registralo":
        "- Buy another user's credit: give the money to someone in credit and record it",
    "  in «Pagamenti tra persone». In credito ora: {elenco}.":
        "  in “Payments between people”. In credit now: {elenco}.",
    "- Compra uno dei beni: compra caffè, acqua o altro per il gruppo e registralo":
        "- Buy one of the goods: buy coffee, water or anything else for the group and record it",
    "  in «Ho comprato per il gruppo».": "  in “I bought for the group”.",
    "Apri l'app: {url}": "Open the app: {url}",
    "Questo avviso arriva ogni lunedì finché il saldo è negativo.":
        "This reminder arrives every Monday as long as your balance is negative.",
    "Per non riceverlo più per email: nell'app vai su Profilo e togli la spunta.":
        "To stop receiving it by email: in the app go to Profile and untick the box.",
}


def traduci(chiave, lingua, /, **valori):
    """Restituisce il testo nella lingua richiesta (l'italiano è la lingua di partenza)."""
    risultato = EN.get(chiave, chiave) if lingua == "en" else chiave
    return risultato.format(**valori) if valori else risultato
