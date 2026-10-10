# 🌿 Terra Mia – Strumento di Gestione Sito Web

Strumento desktop in italiano per aggiornare il sito Terra Mia su GitHub Pages in modo semplice e visivo.

## Requisiti

- **Python 3.9+** – scaricabile da [python.org](https://www.python.org/downloads/)
  - Durante l'installazione, spuntare "Add Python to PATH"
- **Git** – scaricabile da [git-scm.com](https://git-scm.com)

## Avvio

**Fai doppio clic su `Avvia Terra Mia.bat`**

Lo script installa automaticamente le dipendenze (Pillow) se non presenti.

---

## Funzionalità

### 📦 1. Tab Prodotti
- **Regioni ordinate automaticamente**: quando aggiungi una nuova regione, viene posizionata automaticamente in ordine alfabetico (A-Z).
- **Riordino manuale regioni**: usa i pulsanti **▲ Sposta Su** e **▼ Sposta Giù** per cambiare l'ordine delle regioni a tuo piacimento.
- **Pulsante "Ordina Tutte A-Z"**: riordina all'istante l'intero elenco delle regioni.
- Seleziona la regione dalla lista a sinistra per visualizzare i prodotti.
- Aggiungi, modifica o elimina prodotti con i pulsanti.
- Riordina i prodotti con i tasti ▲ ▼.
- Premi **💾 Salva Modifiche** per aggiornare `data/products.json`.

### 🖼 2. Tab Immagini Regioni
- Seleziona la regione dal menu a tendina in alto.
- **Miniature visive**: ogni riga mostra direttamente la miniatura dell'immagine a 500px.
- **Pannello Anteprima a destra**: cliccando su una foto o riga, compare l'anteprima ingrandita con dettagli (dimensioni, peso file) e pulsante **🔍 Apri a Schermo Intero**.
- **Doppio clic**: fai doppio clic su qualsiasi foto nella lista per aprirla subito nel visualizzatore di Windows.
- Premi **📥 Importa Foto da Cartella** per caricare nuove immagini:
  - Vengono create automaticamente la versione 500×500px (`n.jpeg`) e l'alta risoluzione (`n@2x.jpeg`), convertendo automaticamente qualsiasi formato originale (PNG, JPEG, WEBP, ecc.).
  - **Pulizia automatica opzionale**: al termine dell'importazione, lo strumento chiede se eliminare i file originali dalla cartella di importazione per evitare ricopie accidentali.
- Riordina o elimina le immagini con i tasti ▲ ▼ 🗑.
- Premi **💾 Applica e Rinumera Immagini** per rinumerare i file e aggiornare `js/regions.js` (l'elenco delle regioni in `regions.js` viene sempre salvato rigorosamente in **ordine alfabetico A-Z**).

### 🌐 3. Tab Anteprima Sito Web (Server Locale)
- Visualizza il sito web in locale prima di metterlo online.
- Premi il grande pulsante verde **▶ AVVIA SERVER & APRI SITO NEL BROWSER**:
  - Si apre da solo il browser (Edge, Chrome, ecc.) all'indirizzo locale.
  - Carica `data/products.json` e le immagini senza blocchi di sicurezza (CORS).
  - La cache è disabilitata automaticamente, così ogni modifica alle foto o ai testi è visibile subito premendo F5 nel browser.
- Pulsanti rapidi per aprire la **Home Page** o la **Pagina Prodotti**.
- Pulsante **⏹ Ferma Server** per fermare il servizio.

### 🚀 4. Tab Pubblica su GitHub
- Premi **🔍 Ricontrolla Modifiche** per vedere quali file sono stati aggiornati.
- Modifica la descrizione del salvataggio se lo desideri.
- Premi **🚀 Pubblica su GitHub**: con un solo clic esegue l'aggiornamento online del sito su GitHub Pages.

---

## Cartella Import Immagini

Default: `%USERPROFILE%\Pictures\import\<Regione>\`

Esempio: per Calabria → `C:\Users\TuoNome\Pictures\import\Calabria\`

La cartella è configurabile in **⚙ Impostazioni** (in alto a destra).

## File gestiti dallo strumento

| File | Descrizione |
|------|-------------|
| `data/products.json` | Lista prodotti e regioni |
| `js/regions.js` | Contatori immagini per regione |
| `images/regions/<Regione>/N.jpeg` | Immagine 500×500px (fallback .jpg) |
| `images/regions/<Regione>/N@2x.jpeg` | Immagine alta risoluzione 2x (fallback .jpg) |
| `code/config.json` | Impostazioni locali |
