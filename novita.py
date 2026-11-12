"""
Novità di ogni aggiornamento: compaiono in home a tutti finché non spuntano «Ho letto».

Quando carichi una nuova versione con cambiamenti che si vedono, aggiungi una voce IN CIMA:
- "id": la data dell'aggiornamento (AAAA-MM-GG). Se ne fai due lo stesso giorno: "2026-11-20b".
- "it" e "en": poche righe brevi, una per novità, nella stessa lingua di chi legge.
Chi ha creato l'account dopo quella data non la vede (per lui non è una novità).
"""

NOVITA = [
    {
        "id": "2026-11-12b",
        "it": [
            "✉️ L'email del lunedì ora elenca tutti quelli in credito, con il link alla loro scheda per vedere come vogliono essere pagati.",
        ],
        "en": [
            "✉️ The Monday email now lists everyone in credit, with a link to their profile card to see how they want to be paid.",
        ],
    },
    {
        "id": "2026-11-12",
        "it": [
            "🫗 Il debito dell'acqua della macchinetta ora si divide tra chi prende caffè, in proporzione ai caffè presi. Quando succede ricevi un messaggio con la tua quota.",
        ],
        "en": [
            "🫗 The machine water debt is now split among coffee drinkers, in proportion to the coffees taken. When it happens you get a message with your share.",
        ],
    },
    {
        "id": "2026-11-11f",
        "it": [
            "🗑 Per gli amministratori: dalla scheda di una persona si può eliminare il suo profilo (solo con saldo a 0). Per 3 giorni si può ripristinare.",
        ],
        "en": [
            "🗑 For admins: a person's profile can now be deleted from their card (only with a zero balance). It can be restored for 3 days.",
        ],
    },
    {
        "id": "2026-11-11e",
        "it": [
            "📬 Quando un tuo pagamento o una tua spesa vengono confermati o rifiutati, ricevi un messaggio in home con chi ha deciso (e il motivo, se rifiutati).",
        ],
        "en": [
            "📬 When one of your payments or purchases is confirmed or rejected, you get a message on the home page saying who decided (and why, if rejected).",
        ],
    },
    {
        "id": "2026-11-11d",
        "it": [
            "✉️ Gli amministratori possono mandare messaggi anche a una o più persone: li vedi in home come «Messaggio per te», finché non spunti «Ho letto».",
        ],
        "en": [
            "✉️ Administrators can also send messages to one or more people: you see them on the home page as “Message for you”, until you tick “I've read it”.",
        ],
    },
    {
        "id": "2026-11-11c",
        "it": [
            "🫗 Sotto «Acqua macchinetta» e «Bicchierino vuoto» ora c'è scritto quando segnarli: l'acqua solo quando metti una bottiglia nuova nella macchinetta, il bicchierino vuoto solo se lo prendi senza caffè.",
            "⬅️ In fondo allo schermo ci sono sempre «Indietro» e «Home»: niente più scorrere fino in fondo nelle pagine lunghe.",
        ],
        "en": [
            "🫗 Under “Machine water” and “Empty cup” it now says when to record them: water only when you put a new bottle in the machine, the empty cup only if you take it without coffee.",
            "⬅️ “Back” and “Home” are always at the bottom of the screen: no more scrolling to the end of long pages.",
        ],
    },
    {
        "id": "2026-11-11b",
        "it": [
            "🛒 Anche le spese per il gruppo degli amministratori ora vanno approvate, da un altro amministratore.",
            "🧾 Tolta la foto dello scontrino dalla spesa.",
        ],
        "en": [
            "🛒 Purchases for the group made by administrators now need approval too, by another administrator.",
            "🧾 The receipt photo has been removed from purchases.",
        ],
    },
    {
        "id": "2026-11-11",
        "it": [
            "🧪 Per gli amministratori: in «Amministrazione → Avviso del lunedì» c'è la prova a secco, che mostra chi riceverebbe l'email e con quale testo, senza spedire nulla.",
        ],
        "en": [
            "🧪 For admins: “Administration → Monday reminder” now has a dry run that shows who would get the email and with what text, without sending anything.",
        ],
    },
    {
        "id": "2026-11-09b",
        "it": [
            "👤 Imposta subito il tuo profilo: tocca «Profilo ed email» e inserisci la tua email (per l'avviso del lunedì) e PayPal o IBAN (per essere pagato da chi compra il tuo credito). Le istruzioni sono in «Come funziona».",
        ],
        "en": [
            "👤 Set up your profile now: tap “Profile and email” and enter your email (for the Monday reminder) and PayPal or IBAN (to get paid by whoever buys your credit). Instructions are in “How it works”.",
        ],
    },
    {
        "id": "2026-11-09",
        "it": [
            "🤝 I pagamenti tra persone li conferma sempre chi riceve i soldi, anche quando paga un amministratore.",
            "💳 Nel Profilo puoi aggiungere PayPal e IBAN: chi deve pagarti li vede nella tua scheda (tocca un nome in «Saldi di tutti»).",
            "📈 Nuova pagina Statistiche: quanti caffè e acque si consumano per giorno, settimana, mese e anno, di tutti o di una persona.",
            "📦 Quando compri cialde, bottiglie o bicchierini per il gruppo, scrivi quanti pezzi e quanto li hai pagati. Se la merce sta finendo, chi è in debito e gli amministratori vedono un avviso.",
            "🥤 Nuovo prodotto gratuito: Bicchierino vuoto.",
            "☕ Il «Conto Caffè» ora si chiama «Macchinetta del caffè».",
            "📣 Gli amministratori possono mandare comunicazioni a tutti: compaiono qui in home finché non spunti «Ho letto».",
        ],
        "en": [
            "🤝 Payments between people are always confirmed by whoever receives the money, even when an administrator pays.",
            "💳 In your Profile you can add PayPal and IBAN: whoever owes you money sees them on your card (tap a name in “Everyone's balances”).",
            "📈 New Statistics page: how many coffees and waters are taken per day, week, month and year, for everyone or one person.",
            "📦 When you buy pods, bottles or cups for the group, enter how many pieces and how much you paid. When supplies run low, people in debt and administrators see a reminder.",
            "🥤 New free product: Empty cup.",
            "☕ The “Conto Caffè” account is now called “Coffee machine” (Macchinetta del caffè).",
            "📣 Administrators can send announcements to everyone: they appear here on the home page until you tick “I've read it”.",
        ],
    },
]
