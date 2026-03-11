// --- Chart data ---------------------------------------------------------------

const performanceLabels = ['Jan 24','Feb','Mar','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Des','Jan 25','Feb','Mar'];
const portfolioIndexed  = [100, 103, 107, 105, 110, 114, 119, 122, 118, 125, 130, 128, 132, 130, 132];
const osloBorsIndexed   = [100, 101, 103, 102, 104, 106, 107, 108, 106, 109, 112, 111, 113, 112, 114.5];

// --- Chart --------------------------------------------------------------------

function renderChart() {
  const ctx = document.getElementById('portfolio-chart');
  if (!ctx) return;

  const c2d = ctx.getContext('2d');

  const gradRed = c2d.createLinearGradient(0, 0, 0, 280);
  gradRed.addColorStop(0, 'rgba(216, 22, 28, 0.28)');
  gradRed.addColorStop(1, 'rgba(216, 22, 28, 0)');

  const gradGray = c2d.createLinearGradient(0, 0, 0, 280);
  gradGray.addColorStop(0, 'rgba(120, 120, 120, 0.15)');
  gradGray.addColorStop(1, 'rgba(120, 120, 120, 0)');

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: performanceLabels,
      datasets: [
        {
          label: 'AbaInvest',
          data: portfolioIndexed,
          borderColor: '#d8161c',
          backgroundColor: gradRed,
          borderWidth: 2.5,
          pointRadius: 0,
          tension: 0.35,
          fill: true
        },
        {
          label: 'Oslo Børs (proxy)',
          data: osloBorsIndexed,
          borderColor: '#9ca3af',
          backgroundColor: gradGray,
          borderWidth: 1.8,
          pointRadius: 0,
          borderDash: [5, 4],
          tension: 0.35,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: { color: '#6b7280', font: { size: 11 } }
        },
        y: {
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: {
            color: '#6b7280',
            font: { size: 11 },
            callback: v => v
          },
          suggestedMin: 95,
          suggestedMax: 140
        }
      },
      plugins: {
        legend: {
          labels: { color: '#374151', font: { size: 12 }, usePointStyle: true, pointStyleWidth: 16 }
        },
        tooltip: {
          backgroundColor: 'rgba(255,255,255,0.97)',
          borderColor: '#d8dde3',
          borderWidth: 1,
          titleColor: '#111',
          bodyColor: '#374151',
          padding: 10,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}`
          }
        }
      }
    }
  });
}

// --- Nav toggle ---------------------------------------------------------------

function setupNavToggle() {
  const btn = document.querySelector('.nav-toggle');
  const nav = document.getElementById('nav');
  if (!btn || !nav) return;
  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    btn.setAttribute('aria-expanded', open);
  });
}

// --- Year ---------------------------------------------------------------------

function setYear() {
  const el = document.getElementById('year');
  if (el) el.textContent = new Date().getFullYear();
}

// --- Init ---------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  renderChart();
  setupNavToggle();
  setYear();
});

// --- Pie chart ----------------------------------------------------------------

function renderPieChart() {
  const ctx = document.getElementById('pie-chart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['EQNR', 'NHY', 'ORK', 'DNB', 'YAR'],
      datasets: [{
        data: [24.6, 21.0, 19.3, 18.9, 16.2],
        backgroundColor: ['#d8161c', '#e85d5d', '#f0a0a0', '#6b7280', '#9ca3af'],
        borderColor: '#ffffff',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(255,255,255,0.97)',
          borderColor: '#d8dde3',
          borderWidth: 1,
          titleColor: '#111',
          bodyColor: '#374151',
          padding: 10,
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed}%`
          }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  renderPieChart();
});
