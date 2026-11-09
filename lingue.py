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
    # --- come essere pagati e scheda della persona ---
    "Come vuoi essere pagato": "How you want to be paid",
    "Facoltativo. Quello che scrivi qui compare nella tua scheda, che vede chi ha fatto l'accesso all'app quando deve darti dei soldi. Lascia vuoto per non mostrarlo.":
        "Optional. What you enter here appears on your card, which anyone logged in to the app sees when they need to give you money. Leave it empty to keep it hidden.",
    "nome di paypal.me oppure email": "paypal.me name or email",
    "PayPal non valido: scrivi il tuo nome di paypal.me (es. mariorossi) oppure l'email del conto PayPal.":
        "Invalid PayPal: enter your paypal.me name (e.g. mariorossi) or the email of your PayPal account.",
    "IBAN non valido: controlla che sia completo e senza errori di battitura.":
        "Invalid IBAN: check that it is complete and has no typos.",
    "Vedi la tua scheda": "See your card",
    "Modifica nel profilo": "Edit in your profile",
    "Saldo": "Balance",
    "in debito": "in debt",
    "in credito": "in credit",
    "in pari": "even",
    "Come pagare": "How to pay",
    "Conto comune: metti i soldi nella cassa.": "Shared account: put the money in the cash box.",
    "Non ha indicato come preferisce essere pagato: chiediglielo.":
        "No preferred payment method given: ask them.",
    "Ho dato dei soldi a {nome}": "I gave money to {nome}",
    "Apri la scheda": "Open the card",
    # --- statistiche ---
    "Statistiche": "Statistics",
    "Consumi di": "Consumption of",
    "Tutti": "Everyone",
    "tu": "you",
    "Mostra": "Show",
    "Vedi i miei consumi": "See my consumption",
    "Vedi i suoi consumi": "See their consumption",
    "Oggi": "Today",
    "Questa settimana": "This week",
    "Questo mese": "This month",
    "Quest'anno": "This year",
    "Media al giorno negli ultimi 30 giorni:": "Daily average over the last 30 days:",
    "Periodo": "Period",
    "Settimane": "Weeks",
    "Mesi": "Months",
    "Anni": "Years",
    "Ancora nessun consumo segnato nell'app.": "Nothing recorded in the app yet.",
    "Contano gli acquisti segnati nell'app, non quelli del foglio cartaceo. L'acqua per la macchinetta conta per chi l'ha presa, anche se la paga il Conto Caffè.":
        "Only purchases recorded in the app count, not those from the paper sheet. Water for the machine counts for whoever took it, even though the Coffee account pays for it.",
    "oggi": "today",
    "ieri": "yesterday",
    "questa settimana": "this week",
    "dal {data}": "from {data}",
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
    "Bicchierino vuoto": "Empty cup",
    # --- magazzino ---
    "Cialde": "Coffee pods",
    "Bottiglie": "Bottles",
    "Bicchierini": "Cups",
    "Magazzino": "Stock",
    "Merce per il magazzino": "Supplies for the stock",
    "Per ogni cosa che hai comprato scrivi quanti pezzi e quanto li hai pagati in tutto: servono per sapere quanta merce c'è.":
        "For each item you bought, enter how many pieces and how much you paid in total: this keeps track of the stock.",
    "pezzi": "pieces",
    "Pezzi di {nome}": "Pieces of {nome}",
    "Costo di {nome} in euro": "Cost of {nome} in euros",
    "Altro": "Other",
    "Cos'altro hai comprato": "What else you bought",
    "Quanto hai speso per il resto (€)": "How much you spent on the rest (€)",
    "Totale: {totale}": "Total: {totale}",
    "Scrivi quanti pezzi di {nome} hai comprato.": "Enter how many pieces of {nome} you bought.",
    "Scrivi quanto hai speso per {nome} (es. 4,50).": "Enter how much you spent on {nome} (e.g. 4.50).",
    "Scrivi cos'altro hai comprato.": "Enter what else you bought.",
    "Scrivi quanto hai speso per il resto.": "Enter how much you spent on the rest.",
    "Sta finendo la merce": "Supplies are running low",
    "ne restano {n}": "{n} left",
    "Se la compri tu, registrala in «Ho comprato per il gruppo» con pezzi e costo: l'importo ti viene accreditato.":
        "If you buy it, record it in “I bought for the group” with pieces and cost: the amount is credited to you.",
    "La compro io": "I'll buy it",
    "La quantità scende da sola a ogni acquisto (secondo le ricette qui sotto) e sale quando approvi una spesa con la merce. Quando conti i pezzi veri, scrivili in «Pezzi contati»: la differenza resta nel registro.":
        "The quantity goes down by itself with every purchase (following the recipes below) and goes up when you approve a group purchase with supplies. When you count the real pieces, enter them in “Pieces counted”: the difference stays in the log.",
    "Quando un articolo arriva alla soglia, compare l'avviso di comprarlo agli amministratori e a chi è in debito.":
        "When an item reaches its threshold, administrators and people in debt see a reminder to buy it.",
    "Articoli": "Items",
    "da contare": "to count",
    "da comprare": "to buy",
    "{n} pezzi": "{n} pieces",
    "Nome articolo": "Item name",
    "Soglia": "Threshold",
    "Pezzi contati": "Pieces counted",
    "Aggiungi un articolo": "Add an item",
    "Cosa consuma ogni prodotto": "What each product uses",
    "Pezzi scalati dal magazzino per ogni prodotto preso. Vale per gli acquisti da ora in poi.":
        "Pieces taken from the stock for each product. Applies to purchases from now on.",
    "{articolo} per {prodotto}": "{articolo} per {prodotto}",
    "Salva le ricette": "Save recipes",
    "Registro del magazzino": "Stock log",
    "Ancora nessun movimento di magazzino.": "No stock movements yet.",
    "consumo": "used",
    "conta": "count",
    "acquisto annullato": "purchase undone",
    "Servono un nome e una soglia (numero di pezzi, anche 0).": "A name and a threshold (number of pieces, even 0) are required.",
    "Scrivi quanti pezzi hai contato (un numero intero, anche 0).": "Enter how many pieces you counted (a whole number, even 0).",
    "{nome}: ora ne risultano {n}.": "{nome}: now {n} in stock.",
    "{nome} aggiornato.": "{nome} updated.",
    "Articolo aggiunto: {nome}. Inserisci quanti pezzi ci sono.": "Item added: {nome}. Enter how many pieces there are.",
    "Nelle ricette scrivi un numero di pezzi da 0 a 20.": "In the recipes, enter a number of pieces from 0 to 20.",
    "Ricette salvate: valgono per gli acquisti da ora in poi.": "Recipes saved: they apply to purchases from now on.",
    # --- bilancio del magazzino ---
    "Bilancio": "Balance sheet",
    "Bilancio del magazzino": "Stock balance sheet",
    "Bilancio: merce comprata, consumata e mancante, in euro": "Balance sheet: supplies bought, used and missing, in euros",
    "Visibile solo agli amministratori.": "Visible to administrators only.",
    "Conta tutto dalla prima volta che ogni articolo è stato contato. Gli euro sono calcolati al costo medio di un pezzo, cioè quanto è costato in media nelle spese approvate.":
        "Everything counts from the first time each item was counted. Euros use the average cost of one piece, i.e. what it cost on average in the approved group purchases.",
    "Ancora niente da mostrare: conta la merce in «Magazzino» e registra le spese con pezzi e costo.":
        "Nothing to show yet: count the supplies in “Stock” and record group purchases with pieces and cost.",
    "Merce comprata": "Supplies bought",
    "Merce consumata": "Supplies used",
    "In magazzino": "In stock",
    "Differenze delle conte": "Count differences",
    "costo sconosciuto": "unknown cost",
    "Costo sconosciuto: nessuna spesa approvata con questo articolo": "Unknown cost: no approved group purchase with this item",
    "costo medio {costo} al pezzo": "average cost {costo} per piece",
    "Iniziale (prima conta)": "Starting (first count)",
    "Comprati": "Bought",
    "Consumati (segnati nell'app)": "Used (recorded in the app)",
    "Mancano {n} pezzi rispetto a quelli segnati: probabilmente consumi non registrati.":
        "{n} pieces are missing compared to what was recorded: probably unrecorded consumption.",
    "Prodotti: incassi e costi": "Products: income and costs",
    "Solo gli acquisti segnati da quando c'è il magazzino.": "Only purchases recorded since the stock was set up.",
    "Il costo di un pezzo viene dalla ricetta (es. caffè = cialda + bicchierino) al costo medio.":
        "The cost of one piece comes from the recipe (e.g. coffee = pod + cup) at average cost.",
    "prezzo {prezzo}": "price {prezzo}",
    "costo": "cost",
    "margine": "margin",
    "Pezzi presi": "Pieces taken",
    "Incassato": "Income",
    "Costo della merce": "Cost of supplies",
    "Margine": "Margin",
    "Il prezzo non copre il costo della merce: valuta di aumentarlo.": "The price doesn't cover the cost of the supplies: consider raising it.",

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

    # --- richieste, accessi, limite di debito, come funziona ---
    "in attesa di approvazione":
        "waiting for approval",
    "Come funziona":
        "How it works",
    "Richieste da approvare: {n}":
        "Requests to approve: {n}",
    "Limite di debito":
        "Debt limit",
    "Chi supera il limite vede un avviso fisso in cima alla pagina. Puoi scegliere se gli acquisti oltre il limite vengono bloccati o se basta una conferma. 0 = nessun limite.":
        "Anyone over the limit sees a permanent warning at the top of the page. You can choose whether purchases over the limit are blocked or just need a confirmation. 0 = no limit.",
    "Limite (€)":
        "Limit (€)",
    "Avvisa e chiedi conferma (consigliato: nessuno smette di segnare i caffè)":
        "Warn and ask for confirmation (recommended: nobody stops logging coffees)",
    "Blocca gli acquisti finché non salda":
        "Block purchases until they settle",
    "Oltre il limite adesso: {n}":
        "Over the limit right now: {n}",
    "Richiesta inviata":
        "Request sent",
    "Un amministratore deve approvare il tuo accesso. Appena lo fa, questa pagina ti porta dentro l'app: non serve rifare niente.":
        "An administrator has to approve your access. As soon as they do, this page takes you into the app: you don't need to do anything again.",
    "Account:":
        "Account:",
    "Controlla di nuovo":
        "Check again",
    "Intanto leggi come funziona":
        "Meanwhile, read how it works",
    "Non sono io / esci":
        "It's not me / log out",
    "In breve":
        "In short",
    "Inquadra il QR sulla macchinetta, oppure apri l'icona sulla schermata Home.":
        "Scan the QR code on the machine, or open the icon on your Home screen.",
    "Tocca + su quello che prendi e poi Conferma. Puoi segnare più cose insieme.":
        "Tap + on what you take, then Confirm. You can log several things at once.",
    "Il costo viene scalato dal tuo saldo. Se sbagli, puoi annullare entro 10 minuti.":
        "The cost is deducted from your balance. If you make a mistake, you can undo it within 10 minutes.",
    "Il tuo saldo":
        "Your balance",
    "Saldo positivo":
        "Positive balance",
    "credito: hai messo più soldi di quelli che hai consumato.":
        "credit: you have put in more money than you have used.",
    "Saldo negativo":
        "Negative balance",
    "debito: hai consumato più di quello che hai pagato.":
        "debt: you have used more than you have paid.",
    "Caffè e acqua hanno un saldo unico. L'acqua per la macchinetta la paga il conto comune del caffè.":
        "Coffee and water share one balance. Water for the machine is paid by the shared coffee account.",
    "Saldi e movimenti sono visibili a tutti, come sul foglio appeso al muro.":
        "Balances and transactions are visible to everyone, just like on the sheet on the wall.",
    "Come rientrare dal debito":
        "How to get out of debt",
    "metti i soldi nella cassa e registralo in «Pagamenti tra persone» → «Ho dato dei soldi a qualcuno» → Cassa. Conta quando un amministratore conferma.":
        "put the money in the cash box and record it in “Payments between people” → “I gave money to someone” → Cash box. It counts once an administrator confirms.",
    "dai i soldi a chi è in credito (lo vedi in «Saldi di tutti») e registralo allo stesso modo, scegliendo quella persona. Conta quando lei conferma di averli ricevuti.":
        "give the money to someone in credit (see “Everyone's balances”) and record it the same way, choosing that person. It counts once they confirm they received it.",
    "compra caffè, cialde, acqua o altro per il gruppo e registralo in «Ho comprato per il gruppo», con la foto dello scontrino. Il credito arriva quando un amministratore approva.":
        "buy coffee, pods, water or anything else for the group and record it in “I bought for the group”, with a photo of the receipt. The credit arrives once an administrator approves.",
    "Tieni basso il debito":
        "Keep your debt low",
    "Caffè e acqua li ricompra chi anticipa i soldi: ogni euro di debito è un euro che un collega ha messo di tasca sua. Salda presto!":
        "Coffee and water are bought again by whoever fronts the money: every euro of debt is a euro a colleague paid out of their own pocket. Settle soon!",
    "Non aspettare l'avviso: salda appena arrivi a qualche euro di debito.":
        "Don't wait for the reminder: settle as soon as you owe a few euros.",
    "Ogni lunedì chi è in negativo riceve un avviso nell'app, e per email se l'ha inserita nel Profilo.":
        "Every Monday anyone with a negative balance gets a reminder in the app, and by email if they added it in their Profile.",
    "Il limite di debito è {limite}.":
        "The debt limit is {limite}.",
    "Oltre il limite l'app blocca gli acquisti finché non saldi.":
        "Over the limit the app blocks purchases until you settle.",
    "Oltre il limite compare un avviso fisso e ogni acquisto va confermato.":
        "Over the limit a permanent warning appears and every purchase must be confirmed.",
    "Per ora non c'è un limite di debito, ma un amministratore può impostarlo.":
        "There is no debt limit for now, but an administrator can set one.",
    "Chi è in credito può «vendere» il suo credito: è il modo più semplice per pareggiare i conti senza passare dalla cassa.":
        "People in credit can “sell” their credit: it's the easiest way to even things out without going through the cash box.",
    "Segna sempre tutto subito: un caffè non segnato lo paga qualcun altro.":
        "Always log everything right away: an unlogged coffee is paid for by someone else.",
    "Pulizia: lascia la postazione come vorresti trovarla":
        "Cleaning: leave the coffee corner the way you'd like to find it",
    "Butta la cialda o la capsula usata, il bicchierino e la paletta nei rifiuti giusti.":
        "Throw the used pod or capsule, the cup and the stirrer into the right bin.",
    "Asciuga gocce e schizzi sul piano e sotto l'erogatore.":
        "Wipe up drips and splashes on the counter and under the spout.",
    "Lava e rimetti a posto tazzine e cucchiaini che usi.":
        "Wash and put back the cups and spoons you use.",
    "Se la vaschetta delle capsule o quella di raccolta è piena, svuotala.":
        "If the capsule container or the drip tray is full, empty it.",
    "Se il serbatoio dell'acqua è quasi vuoto, riempilo con una bottiglia e segna «Acqua macchinetta».":
        "If the water tank is almost empty, refill it with a bottle and log “Machine water”.",
    "Se manca qualcosa (caffè, zucchero, bicchierini) o la macchinetta segnala un problema, avvisa un amministratore.":
        "If something is missing (coffee, sugar, cups) or the machine shows a problem, tell an administrator.",
    "Regole per essere corretti con tutti":
        "Rules to be fair to everyone",
    "Il primo accesso di ogni persona viene approvato da un amministratore.":
        "Everyone's first login is approved by an administrator.",
    "Spese e pagamenti tra persone contano solo dopo una conferma: nessuno può cambiare da solo il saldo di un altro.":
        "Group purchases and payments between people only count after a confirmation: nobody can change someone else's balance on their own.",
    "Ogni movimento resta registrato con data e autore. Gli errori si correggono chiedendo a un amministratore.":
        "Every transaction is recorded with date and author. Mistakes are fixed by asking an administrator.",
    "Domande frequenti":
        "Frequently asked questions",
    "Ho cambiato telefono o dimenticato il PIN.":
        "I changed phone or forgot my PIN.",
    "Chiedi a un amministratore di azzerare il PIN: al prossimo accesso ne sceglierai uno nuovo.":
        "Ask an administrator to reset your PIN: you'll choose a new one at your next login.",
    "Ho segnato qualcosa per sbaglio.":
        "I logged something by mistake.",
    "Tocca «Annulla» entro 10 minuti; dopo, chiedi a un amministratore.":
        "Tap “Undo” within 10 minutes; after that, ask an administrator.",
    "Posso usare l'app in inglese?":
        "Can I use the app in English?",
    "Sì: tocca IT / EN in alto a destra.":
        "Yes: tap IT / EN at the top right.",
    "come rientrare":
        "how to get even",
    "Hai {n} richieste da confermare":
        "You have {n} requests to confirm",
    "Hai 1 richiesta da confermare":
        "You have 1 request to confirm",
    "{n} tue richieste in attesa di conferma":
        "{n} of your requests are waiting for confirmation",
    "1 tua richiesta in attesa di conferma":
        "1 of your requests is waiting for confirmation",
    "Hai superato il limite di debito di {limite} · il tuo saldo è {saldo}":
        "You are over the debt limit of {limite} · your balance is {saldo}",
    "Questo avviso resta finché non torni sotto il limite.":
        "This warning stays until you're back under the limit.",
    "Oltre il limite di debito: salda prima di prendere altro":
        "Over the debt limit: settle before taking anything else",
    "So di essere oltre il limite di debito di {limite}: segna comunque e salderò presto":
        "I know I'm over the debt limit of {limite}: log it anyway, I'll settle soon",
    "Richieste":
        "Requests",
    "Conta quando l'altra persona conferma di aver ricevuto i soldi (per la Cassa conferma un amministratore).":
        "It counts once the other person confirms they received the money (for the Cash box an administrator confirms).",
    "Conta quando l'altra persona conferma di aver ricevuto i soldi. I versamenti ai conti comuni valgono subito.":
        "It counts once the other person confirms they received the money. Payments to shared accounts count right away.",
    "Per sicurezza un amministratore deve approvare il tuo primo accesso: dopo potrai usare l'app.":
        "For security, an administrator has to approve your first login: then you can use the app.",
    "Nuovi accessi da approvare":
        "New logins to approve",
    "Approva solo se sai chi è: chi viene approvato può segnare acquisti e pagamenti.":
        "Only approve if you know who it is: approved people can log purchases and payments.",
    "nuovo account":
        "new account",
    "per l'account «{nome}»":
        "for the account “{nome}”",
    "Approva":
        "Approve",
    "Rifiutare questa richiesta di accesso?":
        "Reject this login request?",
    "Rifiuta":
        "Reject",
    "Da confermare":
        "To confirm",
    "Niente da confermare.":
        "Nothing to confirm.",
    "in attesa di {nome}":
        "waiting for {nome}",
    "ferma da più di 3 giorni":
        "pending for more than 3 days",
    "scontrino":
        "receipt",
    "Conferma solo se hai davvero ricevuto i soldi: il tuo saldo scenderà di {importo}.":
        "Only confirm if you really received the money: your balance will go down by {importo}.",
    "Rifiutare questa richiesta?":
        "Reject this request?",
    "Le mie richieste in attesa":
        "My pending requests",
    "Nessuna richiesta in attesa.":
        "No pending requests.",
    "aspetta l'ok di un amministratore":
        "waiting for an administrator's OK",
    "aspetta la conferma di {nome}":
        "waiting for {nome} to confirm",
    "Il credito arriva quando un amministratore approva la spesa: allega la foto dello scontrino per fare prima.":
        "The credit arrives once an administrator approves the purchase: attach a photo of the receipt to speed things up.",
    "Foto dello scontrino (facoltativa)":
        "Photo of the receipt (optional)",
    "Invia per approvazione":
        "Send for approval",
    "Il tuo accesso è stato approvato: benvenuto!":
        "Your access has been approved: welcome!",
    "Hai raggiunto il limite di debito di {limite}: salda il debito prima di prendere altro.":
        "You've reached the debt limit of {limite}: settle your debt before taking anything else.",
    "Sei oltre il limite di debito di {limite}: spunta la casella per confermare l'acquisto.":
        "You're over the debt limit of {limite}: tick the box to confirm the purchase.",
    "Pagamento inviato: conterà quando un amministratore confermerà di aver ricevuto i soldi.":
        "Payment sent: it will count once an administrator confirms they received the money.",
    "Pagamento inviato: conterà quando {nome} confermerà di aver ricevuto i soldi.":
        "Payment sent: it will count once {nome} confirms they received the money.",
    "La foto non è un'immagine valida o è troppo grande.":
        "The photo isn't a valid image or is too large.",
    "Spesa inviata: l'importo ti verrà accreditato quando un amministratore la approva.":
        "Purchase sent: the amount will be credited to you once an administrator approves it.",
    "{nome} ha comprato per il gruppo: {cosa}":
        "{nome} bought for the group: {cosa}",
    "{nome} dice di aver dato dei soldi a {altro}":
        "{nome} says they gave money to {altro}",
    "Richiesta annullata.":
        "Request cancelled.",
    "Approvata: {cosa}":
        "Approved: {cosa}",
    "Rifiutata: {cosa}":
        "Rejected: {cosa}",
    "Accesso approvato: {nome}.":
        "Access approved: {nome}.",
    "Accesso rifiutato: {nome}.":
        "Access rejected: {nome}.",
    "Limite non valido (es. 10 oppure 7,50; 0 = nessun limite).":
        "Invalid limit (e.g. 10 or 7.50; 0 = no limit).",
    "Limite di debito tolto.":
        "Debt limit removed.",
    "Limite di debito: {limite} ({modo}).":
        "Debt limit: {limite} ({modo}).",
    "blocca gli acquisti":
        "blocks purchases",
    "avvisa e chiede conferma":
        "warns and asks for confirmation",

    # --- registro approvazioni ---
    "Registro approvazioni: chi ha approvato cosa":
        "Approvals log: who approved what",
    "Registro approvazioni":
        "Approvals log",
    "automatico":
        "automatic",
    "annullata dal richiedente":
        "cancelled by the requester",
    "Visibile solo agli amministratori: chi ha chiesto cosa, chi ha deciso e quando. Gli ultimi 300 per sezione; tutto lo storico è nel foglio «Approvazioni» dell'Excel.":
        "Visible to administrators only: who asked for what, who decided and when. The latest 300 per section; the full history is in the “Approvals” sheet of the Excel file.",
    "Tutto":
        "All",
    "Accessi":
        "Logins",
    "Spese":
        "Purchases",
    "Ancora nessuna decisione.":
        "No decisions yet.",
    "da {nome}":
        "by {nome}",
    "da console":
        "from the console",
    "Spese per il gruppo":
        "Group purchases",
    "registrata direttamente dall'admin {nome}":
        "recorded directly by admin {nome}",
    "da {nome}, che ha ricevuto i soldi":
        "by {nome}, who received the money",
    "richiesta del {data}":
        "requested {data}",
    "Approvazioni":
        "Approvals",
    "Richiesta da":
        "Requested by",
    "Esito":
        "Outcome",
    "Deciso da":
        "Decided by",
    "Data decisione":
        "Decision date",
    "approvata":
        "approved",
    "rifiutata":
        "rejected",
    "approvato":
        "approved",
    "rifiutato":
        "rejected",
    "Pagamento":
        "Payment",
    "Accesso":
        "Login",
    "console":
        "console",

    # --- QR ---
    "Attenzione: questo QR porta a {qr}, ma tu stai usando {attuale}. Controlla CAFFE_URL nel file WSGI su PythonAnywhere, poi premi Reload.":
        "Warning: this QR code points to {qr}, but you are using {attuale}. Check CAFFE_URL in the WSGI file on PythonAnywhere, then press Reload.",
    "Scarica l'immagine del QR":
        "Download the QR image",
    "Dall'icona sulla schermata Home l'iPhone non permette di stampare: tocca «Scarica l'immagine del QR» (poi Condividi → Stampa), oppure apri questa pagina in Safari.":
        "From the Home Screen icon the iPhone can't print: tap “Download the QR image” (then Share → Print), or open this page in Safari.",

    # --- backup settimanale ---
    "Backup settimanale":
        "Weekly backup",
    "Ogni lunedì (dalle 8:00) gli amministratori con l'email nel Profilo ricevono l'Excel e il database completo. Se l'account PythonAnywhere si perde, con il database si rimette tutto com'era.":
        "Every Monday (from 8:00) admins with an email in their Profile receive the Excel file and the full database. If the PythonAnywhere account is lost, the database puts everything back as it was.",
    "Lo ricevono:":
        "Sent to:",
    "nessuno":
        "nobody",
    "aggiungi la tua email nel Profilo":
        "add your email in your Profile",
    "Amministratori senza email (non lo ricevono): {nomi}":
        "Admins without an email (they don't get it): {nomi}",
    "Invia il backup adesso":
        "Send the backup now",
    "Puoi anche scaricarli quando vuoi con i pulsanti «Excel» e «Backup» in cima alla pagina.":
        "You can also download them anytime with the “Excel” and “Backup” buttons at the top of the page.",
    "Nessun amministratore ha l'email: aggiungi la tua nel Profilo.":
        "No admin has an email: add yours in your Profile.",
    "Backup inviato a: {nomi}":
        "Backup sent to: {nomi}",
    # email del backup
    "{app}: backup del {data}":
        "{app}: backup of {data}",
    "ecco il backup settimanale di {app}, con i dati aggiornati al {quando}.":
        "here is the weekly backup of {app}, with data up to {quando}.",
    "In allegato:":
        "Attached:",
    "- {file}: saldi, movimenti e approvazioni, da aprire con Excel;":
        "- {file}: balances, transactions and approvals, to open with Excel;",
    "- {file}: il database completo, serve per rimettere in piedi l'app.":
        "- {file}: the full database, used to bring the app back up.",
    "In negativo adesso: {n} persone, per un totale di {totale}.":
        "In debt right now: {n} people, {totale} in total.",
    "Conserva questa email: se l'account PythonAnywhere si perde, con il file .db si ripristina tutto (guida, «Ripristino da un backup»).":
        "Keep this email: if the PythonAnywhere account is lost, the .db file restores everything (guide, “Ripristino da un backup”).",
    "Contiene i dati del gruppo e i PIN cifrati: non inoltrarla.":
        "It contains the group's data and the encrypted PINs: don't forward it.",
    "Arriva ogni lunedì agli amministratori che hanno l'email nel Profilo.":
        "It arrives every Monday for admins who have an email in their Profile.",
}


def traduci(chiave, lingua, /, **valori):
    """Restituisce il testo nella lingua richiesta (l'italiano è la lingua di partenza)."""
    risultato = EN.get(chiave, chiave) if lingua == "en" else chiave
    return risultato.format(**valori) if valori else risultato
