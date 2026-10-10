# 🌿 Terra Mia – Strumento di Gestione Sito Web

Strumento desktop in italiano per aggiornare il sito Terra Mia su GitHub Pages.

## Requisiti

- **Python 3.9+** – scaricabile da [python.org](https://www.python.org/downloads/)
  - Durante l'installazione, spuntare "Add Python to PATH"
- **Git** – scaricabile da [git-scm.com](https://git-scm.com)

## Avvio

**Doppio clic su `Avvia Terra Mia.bat`**

Lo script installa automaticamente le dipendenze (Pillow) se non presenti.

---

## Funzionalità

### 📦 Tab Prodotti
- Seleziona la regione dalla lista a sinistra
- Aggiungi, modifica o elimina prodotti con i pulsanti
- Riordina con i tasti ▲ ▼
- Premi **💾 Salva** per aggiornare `data/products.json`

### 🖼 Tab Immagini Regioni
- Seleziona la regione dal menu a tendina
- Premi **Importa da cartella** per caricare le immagini
  - Vengono create automaticamente versione 500×500px (`n.jpeg`) e alta risoluzione (`n@2x.jpeg`)
- Riordina o elimina con i tasti ▲ ▼ 🗑
- Premi **💾 Applica modifiche** per rinumerare i file e aggiornare `regions.js`

### 🚀 Tab Pubblica su GitHub
- Premi **🔍 Verifica modifiche** per vedere cosa cambierà
- Modifica il messaggio di commit se necessario
- Premi **🚀 Pubblica su GitHub** per caricare le modifiche online

---

## Cartella Import Immagini

Default: `%USERPROFILE%\Pictures\import\<Regione>\`

Esempio: per Calabria → `C:\Users\TuoNome\Pictures\import\Calabria\`

La cartella si configura in **⚙ Impostazioni** (in alto a destra).

## File generati/modificati dallo strumento

| File | Descrizione |
|------|-------------|
| `data/products.json` | Lista prodotti per regione |
| `js/regions.js` | Contatori immagini per regione |
| `images/regions/<Regione>/N.jpeg` | Anteprima 500×500px |
| `images/regions/<Regione>/N@2x.jpeg` | Immagine alta risoluzione |
| `code/config.json` | Impostazioni locali (non sincronizzato con Git) |
