# AbaInvest – Personal Portfolio Dashboard

A simple, modern single-page dashboard for visualising a personal equity portfolio.
Built as static HTML/CSS/JS so you can open it directly in your browser and easily
adapt it to your own holdings.

## Files

- `index.html` – main page layout
- `styles.css` – visual design (dark, glassmorphism-inspired UI)
- `script.js` – portfolio data, calculations, and chart logic

## How to run

1. Open this folder in your file explorer:
   `c:\Users\aleks\OneDrive\Dokumenter\prompt`
2. Double-click `index.html` to open it in your browser (Chrome, Edge, etc.).

No build step or server is required.

## Editing your portfolio

Open `script.js` and look for the `holdings` array:

```js
const holdings = [
  {
    ticker: 'EQNR',
    company: 'Equinor ASA',
    shares: 120,
    price: 320.5,
    costBasis: 280.0
  },
  // ...
];
```

- **ticker** – stock ticker symbol
- **company** – company name
- **shares** – number of shares you own
- **price** – current price per share (NOK)
- **costBasis** – your average purchase price per share (NOK)

The dashboard will automatically recompute:

- Total portfolio value
- Profit/loss in NOK and %
- Position weights
- Allocation list

## Portfolio vs Oslo Børs chart

The chart uses static, illustrative data defined in `script.js`:

- `performanceLabels` – labels on the x-axis (e.g. months)
- `portfolioIndexed` – indexed values for AbaInvest
- `osloBorsIndexed` – indexed values for the Oslo Børs proxy

You can replace these arrays with your own series from a spreadsheet or an API later.

