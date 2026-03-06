// --- Configuration: portfolio & benchmark data --------------------------------

const LOCAL_STORAGE_KEY = 'abainvest_holdings';
// Edit this array to match your real holdings.
const defaultHoldings = [
  {
    ticker: 'EQNR',
    company: 'Equinor ASA',
    shares: 120,
    price: 320.5,
    costBasis: 280.0
  },
  {
    ticker: 'DNB',
    company: 'DNB Bank ASA',
    shares: 90,
    price: 210.2,
    costBasis: 190.0
  },
  {
    ticker: 'YAR',
    company: 'Yara International ASA',
    shares: 65,
    price: 390.0,
    costBasis: 360.0
  },
  {
    ticker: 'NHY',
    company: 'Norsk Hydro ASA',
    shares: 200,
    price: 82.3,
    costBasis: 75.0
  },
  {
    ticker: 'ORK',
    company: 'Orkla ASA',
    shares: 160,
    price: 85.4,
    costBasis: 80.0
  }
];

let currentHoldings = [];
let currentSortBy = 'value';

// Static, illustrative performance series (indexed to 100).
// Replace these arrays with real data later if you want.
const performanceLabels = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec'
];

const portfolioIndexed = [100, 102, 105, 103, 108, 111, 116, 118, 120, 124, 129, 132];
const osloBorsIndexed = [100, 101, 102, 101, 103, 104, 106, 107, 109, 111, 112, 114];

// --- Helper functions ---------------------------------------------------------

function formatCurrencyNOK(value) {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'NOK',
    maximumFractionDigits: 0
  }).format(value);
}

function formatPercent(value) {
  const sign = value > 0 ? '+' : value < 0 ? '' : '';
  return `${sign}${value.toFixed(1)}%`;
}

function loadHoldings() {
  try {
    const raw = window.localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return parsed;
  } catch (e) {
    return null;
  }
}

function saveHoldings(holdings) {
  try {
    window.localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(holdings));
  } catch (e) {
    // ignore storage errors
  }
}

function calculatePortfolioStats(holdings) {
  const enriched = holdings.map((h) => {
    const value = h.shares * h.price;
    const invested = h.shares * h.costBasis;
    const pl = value - invested;
    const plPct = invested !== 0 ? (pl / invested) * 100 : 0;
    return { ...h, value, invested, pl, plPct };
  });

  const totalValue = enriched.reduce((sum, h) => sum + h.value, 0);
  const totalInvested = enriched.reduce((sum, h) => sum + h.invested, 0);
  const totalPL = totalValue - totalInvested;
  const totalPLPct = totalInvested !== 0 ? (totalPL / totalInvested) * 100 : 0;

  const withWeights = enriched.map((h) => ({
    ...h,
    weight: totalValue !== 0 ? (h.value / totalValue) * 100 : 0
  }));

  return {
    holdings: withWeights,
    totalValue,
    totalInvested,
    totalPL,
    totalPLPct
  };
}

// --- DOM rendering ------------------------------------------------------------

function renderOverview(stats) {
  const totalValueEl = document.getElementById('total-value');
  const totalChangeEl = document.getElementById('total-change');
  const benchmarkDiffEl = document.getElementById('benchmark-diff');

  totalValueEl.textContent = formatCurrencyNOK(stats.totalValue);

  const changeText = `${formatCurrencyNOK(stats.totalPL)} (${formatPercent(
    stats.totalPLPct
  )}) since inception`;
  totalChangeEl.textContent = changeText;
  totalChangeEl.classList.toggle('pl-positive', stats.totalPL >= 0);
  totalChangeEl.classList.toggle('pl-negative', stats.totalPL < 0);

  // Compare final indexed values of portfolio vs Oslo Børs.
  const lastPortfolio = portfolioIndexed[portfolioIndexed.length - 1];
  const lastBenchmark = osloBorsIndexed[osloBorsIndexed.length - 1];
  const rel = ((lastPortfolio - lastBenchmark) / lastBenchmark) * 100;

  benchmarkDiffEl.textContent = formatPercent(rel);
  benchmarkDiffEl.classList.toggle('pl-positive', rel >= 0);
  benchmarkDiffEl.classList.toggle('pl-negative', rel < 0);
}

function renderHoldingsTable(stats, sortBy = 'value') {
  const tbody = document.getElementById('holdings-body');
  if (!tbody) return;

  const sorted = [...stats.holdings].sort((a, b) => {
    if (sortBy === 'value') return b.value - a.value;
    if (sortBy === 'weight') return b.weight - a.weight;
    if (sortBy === 'pl') return b.pl - a.pl;
    return 0;
  });

  tbody.innerHTML = '';

  sorted.forEach((h) => {
    const tr = document.createElement('tr');

    tr.innerHTML = `
      <td><span class="ticker">${h.ticker}</span></td>
      <td><span class="company">${h.company}</span></td>
      <td class="numeric">${h.shares.toLocaleString('en-GB')}</td>
      <td class="numeric">${formatCurrencyNOK(h.price)}</td>
      <td class="numeric">${formatCurrencyNOK(h.value)}</td>
      <td class="numeric">
        <span class="weight-pill">${h.weight.toFixed(1)}%</span>
      </td>
      <td class="numeric ${h.pl >= 0 ? 'pl-positive' : 'pl-negative'}">
        ${formatCurrencyNOK(h.pl)} (${formatPercent(h.plPct)})
      </td>
    `;

    tbody.appendChild(tr);
  });
}

function renderAllocationList(stats) {
  const list = document.getElementById('allocation-list');
  if (!list) return;

  const sorted = [...stats.holdings].sort((a, b) => b.weight - a.weight);
  const maxWeight = sorted[0]?.weight ?? 0;

  list.innerHTML = '';

  sorted.forEach((h, index) => {
    const li = document.createElement('li');
    li.className = 'allocation-item';

    const relativeWidth = maxWeight > 0 ? (h.weight / maxWeight) * 100 : 0;

    li.innerHTML = `
      <div class="allocation-left">
        <span class="allocation-dot" style="background: ${
          index === 0
            ? 'var(--accent)'
            : index === 1
            ? 'var(--accent-alt)'
            : 'rgba(148, 163, 184, 1)'
        };"></span>
        <div>
          <div class="allocation-label">${h.ticker}</div>
          <div class="allocation-company">${h.company}</div>
        </div>
      </div>
      <div class="allocation-bar">
        <div class="allocation-bar-fill" style="width: ${relativeWidth}%;"></div>
      </div>
      <div class="allocation-value">${h.weight.toFixed(1)}%</div>
    `;

    list.appendChild(li);
  });
}

function populateRemoveSelect(stats) {
  const select = document.getElementById('remove-ticker');
  if (!select) return;

  const sorted = [...stats.holdings].sort((a, b) => a.ticker.localeCompare(b.ticker));

  const previous = select.value;
  select.innerHTML = '';

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Select ticker';
  select.appendChild(placeholder);

  sorted.forEach((h) => {
    const option = document.createElement('option');
    option.value = h.ticker;
    option.textContent = `${h.ticker} – ${h.company}`;
    select.appendChild(option);
  });

  if (previous) {
    const stillExists = sorted.some((h) => h.ticker === previous);
    if (stillExists) {
      select.value = previous;
    }
  }
}

function recalculateAndRender() {
  const stats = calculatePortfolioStats(currentHoldings);
  renderOverview(stats);
  renderHoldingsTable(stats, currentSortBy);
  renderAllocationList(stats);
  populateRemoveSelect(stats);
}

function setupSorting() {
  const buttons = document.querySelectorAll('.sort-button');
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      buttons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      const sortBy = btn.getAttribute('data-sort');
      currentSortBy = sortBy || 'value';
      recalculateAndRender();
    });
  });
}

function renderChart() {
  const ctx = document.getElementById('performance-chart');
  if (!ctx) return;

  const gradientPortfolio = ctx.getContext('2d').createLinearGradient(0, 0, 0, 220);
  gradientPortfolio.addColorStop(0, 'rgba(250, 204, 21, 0.4)');
  gradientPortfolio.addColorStop(1, 'rgba(0, 0, 0, 0)');

  const gradientBenchmark = ctx.getContext('2d').createLinearGradient(0, 0, 0, 220);
  gradientBenchmark.addColorStop(0, 'rgba(148, 163, 184, 0.32)');
  gradientBenchmark.addColorStop(1, 'rgba(15, 23, 42, 0)');

  // eslint-disable-next-line no-undef
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: performanceLabels,
      datasets: [
        {
          label: 'AbaInvest portfolio',
          data: portfolioIndexed,
          borderColor: 'rgba(250, 204, 21, 1)',
          backgroundColor: gradientPortfolio,
          borderWidth: 2.5,
          pointRadius: 0,
          tension: 0.3,
          fill: true
        },
        {
          label: 'Oslo Børs (proxy)',
          data: osloBorsIndexed,
          borderColor: 'rgba(148, 163, 184, 1)',
          backgroundColor: gradientBenchmark,
          borderWidth: 1.8,
          pointRadius: 0,
          borderDash: [4, 4],
          tension: 0.3,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: {
            color: 'rgba(30, 64, 175, 0.3)'
          },
          ticks: {
            color: 'rgba(148, 163, 184, 0.9)',
            font: { size: 10 }
          }
        },
        y: {
          grid: {
            color: 'rgba(15, 23, 42, 0.8)'
          },
          ticks: {
            color: 'rgba(148, 163, 184, 0.9)',
            font: { size: 10 },
            callback: (value) => `${value}`
          }
        }
      },
      plugins: {
        legend: {
          labels: {
            color: 'rgba(209, 213, 219, 1)',
            font: { size: 11 }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          borderColor: 'rgba(30, 64, 175, 0.9)',
          borderWidth: 1,
          titleFont: { size: 12 },
          bodyFont: { size: 11 },
          padding: 8
        }
      }
    }
  });
}

function setupFormHandlers() {
  const addForm = document.getElementById('add-holding-form');
  const removeForm = document.getElementById('remove-holding-form');

  if (addForm) {
    addForm.addEventListener('submit', (event) => {
      event.preventDefault();

      const formData = new FormData(addForm);

      const tickerRaw = (formData.get('ticker') || '').toString();
      const companyRaw = (formData.get('company') || '').toString();
      const sharesRaw = formData.get('shares');
      const priceRaw = formData.get('price');
      const costBasisRaw = formData.get('costBasis');

      const ticker = tickerRaw.trim().toUpperCase();
      const company = companyRaw.trim();
      const shares = Number(sharesRaw);
      const price = Number(priceRaw);
      const costBasis = Number(costBasisRaw);

      if (!ticker || !company || !Number.isFinite(shares) || shares <= 0) {
        return;
      }

      const cleanedPrice = Number.isFinite(price) && price > 0 ? price : 0;
      const cleanedCostBasis = Number.isFinite(costBasis) && costBasis > 0 ? costBasis : 0;

      const existingIndex = currentHoldings.findIndex(
        (h) => h.ticker.toUpperCase() === ticker
      );

      const nextHolding = {
        ticker,
        company,
        shares,
        price: cleanedPrice,
        costBasis: cleanedCostBasis
      };

      if (existingIndex >= 0) {
        currentHoldings[existingIndex] = nextHolding;
      } else {
        currentHoldings.push(nextHolding);
      }

      saveHoldings(currentHoldings);
      recalculateAndRender();
      addForm.reset();
    });
  }

  if (removeForm) {
    removeForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const select = document.getElementById('remove-ticker');
      if (!select) return;

      const tickerRaw = (select.value || '').toString();
      const ticker = tickerRaw.trim().toUpperCase();
      if (!ticker) return;

      currentHoldings = currentHoldings.filter(
        (h) => h.ticker.toUpperCase() !== ticker
      );

      saveHoldings(currentHoldings);
      recalculateAndRender();
    });
  }
}

function setYear() {
  const yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear().toString();
  }
}

// --- Init ---------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  const loaded = loadHoldings();
  if (Array.isArray(loaded) && loaded.length > 0) {
    currentHoldings = loaded;
  } else {
    currentHoldings = defaultHoldings;
  }

  currentSortBy = 'value';
  recalculateAndRender();
  setupSorting();
  setupFormHandlers();
  renderChart();
  setYear();
});

