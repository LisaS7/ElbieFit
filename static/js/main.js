// Menu toggle

document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('#app-header .menu-toggle');
  const nav = document.querySelector('#main-nav');

  if (!toggle || !nav) {
    return; // nothing to toggle
  }

  toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });
});

// Cancel form

document.closeForm = function (selector) {
  const container = document.querySelector(selector);
  if (container) container.innerHTML = '';
};

document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-cancel-target]');
  if (btn) document.closeForm(btn.dataset.cancelTarget);
});

// Inline delete confirmation
// Buttons with class "delete-btn" require a second click to confirm.
// On first click the button text changes to data-confirm-label and htmx is suspended.
// On second click htmx fires the request. Clicking elsewhere resets the button.

document.addEventListener('click', function (e) {
  const btn = e.target.closest('.delete-btn');

  if (!btn) {
    // Click was outside — reset any pending delete buttons
    document.querySelectorAll('.delete-btn[data-pending]').forEach(function (pending) {
      pending.textContent = pending.dataset.originalLabel;
      pending.removeAttribute('data-pending');
      pending.classList.remove('delete-btn--confirm');
    });
    return;
  }

  if (btn.hasAttribute('data-pending')) {
    // Second click: dispatch custom event so htmx fires (hx-trigger="confirmedDelete")
    btn.removeAttribute('data-pending');
    btn.classList.remove('delete-btn--confirm');
    btn.dispatchEvent(new Event('confirmedDelete'));
    return;
  }

  // First click: show confirmation label and block htmx
  e.preventDefault();
  e.stopPropagation();

  // Reset any other pending buttons first
  document.querySelectorAll('.delete-btn[data-pending]').forEach(function (other) {
    if (other !== btn) {
      other.textContent = other.dataset.originalLabel;
      other.removeAttribute('data-pending');
      other.classList.remove('delete-btn--confirm');
    }
  });

  btn.setAttribute('data-pending', '');
  btn.textContent = btn.dataset.confirmLabel || '✓';
  btn.classList.add('delete-btn--confirm');
});

// ─────────────────────────────────────────────────────────────
// Chart helpers
// ─────────────────────────────────────────────────────────────

function buildChartColors() {
  const s = getComputedStyle(document.documentElement);
  return {
    accent:       s.getPropertyValue('--color-accent').trim(),
    bar:          s.getPropertyValue('--chart-bar-color').trim(),
    muted:        s.getPropertyValue('--color-muted').trim(),
    borders:      s.getPropertyValue('--color-borders').trim(),
    text:         s.getPropertyValue('--color-text').trim(),
    distPalette:  s.getPropertyValue('--chart-dist-palette').trim().split(','),
  };
}

function initFrequencyChart() {
  const canvas = document.getElementById('freq-chart');
  if (!canvas) return;
  const data = JSON.parse(canvas.dataset.chart);
  const c = buildChartColors();
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Workouts',
        data: data.values,
        backgroundColor: c.bar + 'cc',
        borderColor: c.bar,
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: c.muted },
          grid: { color: c.borders + '80' },
        },
        y: {
          beginAtZero: true,
          ticks: { color: c.muted, stepSize: 1 },
          grid: { color: c.borders + '80' },
        }
      }
    }
  });
}

function initVolumeChart() {
  const canvas = document.getElementById('volume-chart');
  if (!canvas) return;
  const data = JSON.parse(canvas.dataset.chart);
  const c = buildChartColors();
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: `Total Volume (${data.unit})`,
        data: data.values,
        backgroundColor: c.bar + 'cc',
        borderColor: c.bar,
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: c.muted },
          grid: { color: c.borders + '80' },
        },
        y: {
          beginAtZero: true,
          ticks: { color: c.muted },
          grid: { color: c.borders + '80' },
          title: { display: true, text: data.unit, color: c.muted },
        }
      }
    }
  });
}

function init1RMChart() {
  const canvas = document.getElementById('one-rm-chart');
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  const data = JSON.parse(canvas.dataset.chart);
  const unit = canvas.dataset.unit;
  const c = buildChartColors();
  new Chart(canvas, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: `Est. 1RM (${unit})`,
        data: data.values,
        borderColor: c.accent,
        backgroundColor: c.accent + '22',
        pointBackgroundColor: c.accent,
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: c.muted },
          grid: { color: c.borders },
        },
        y: {
          ticks: { color: c.muted },
          grid: { color: c.borders },
          title: { display: true, text: unit, color: c.muted },
        }
      }
    }
  });
}


function initDistributionChart(view = 'by_muscle') {
  const canvas = document.getElementById('dist-chart');
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  const allData = JSON.parse(canvas.dataset.chart);
  const viewData = allData[view];
  if (!viewData || !viewData.values.length) return;
  const c = buildChartColors();
  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: viewData.labels,
      datasets: [{
        data: viewData.values,
        backgroundColor: c.distPalette.slice(0, viewData.labels.length),
        borderColor: c.borders,
        borderWidth: 2,
        hoverBorderWidth: 3,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: c.text,
            pointStyle: 'circle',
            usePointStyle: true,
            padding: 12,
            font: { size: 12 },
          },
        },
        title: {
          display: false,
        },
      }
    }
  });
}

function updateDistributionChart(view) {
  document.querySelectorAll('#dist-toggle .toggle-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });
  initDistributionChart(view);
}

function initExerciseChart() {
  const canvas = document.getElementById('exercise-chart');
  if (!canvas) return;
  // Destroy previous instance if one exists (HTMX re-injects the fragment on each select)
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  const data = JSON.parse(canvas.dataset.chart);
  const unit = canvas.dataset.unit;
  const c = buildChartColors();
  new Chart(canvas, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: `Weight (${unit})`,
        data: data.values,
        borderColor: c.accent,
        backgroundColor: c.accent + '22',
        pointBackgroundColor: c.accent,
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: c.muted },
          grid: { color: c.borders },
        },
        y: {
          ticks: { color: c.muted },
          grid: { color: c.borders },
          title: { display: true, text: unit, color: c.muted },
        }
      }
    }
  });
}


