// Dashboard Charting with Chart.js

document.addEventListener('DOMContentLoaded', function () {
  const chartCanvas = document.getElementById('transactionChart');
  if (!chartCanvas) return;

  const labels = window.chartDataLabels || ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'];
  const deposits = window.chartDataDeposits || [0, 0, 0, 0, 0, 0];
  const withdrawals = window.chartDataWithdrawals || [0, 0, 0, 0, 0, 0];

  const ctx = chartCanvas.getContext('2d');

  // Gradient for deposits
  const depGradient = ctx.createLinearGradient(0, 0, 0, 300);
  depGradient.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
  depGradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

  // Gradient for withdrawals
  const withGradient = ctx.createLinearGradient(0, 0, 0, 300);
  withGradient.addColorStop(0, 'rgba(239, 68, 68, 0.35)');
  withGradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Total Inflow / Deposits ($)',
          data: deposits,
          borderColor: '#10b981',
          backgroundColor: depGradient,
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointBackgroundColor: '#10b981',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        },
        {
          label: 'Total Outflow / Withdrawals ($)',
          data: withdrawals,
          borderColor: '#ef4444',
          backgroundColor: withGradient,
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointBackgroundColor: '#ef4444',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            usePointStyle: true,
            boxWidth: 8,
            font: {
              family: "'Inter', sans-serif",
              size: 12,
              weight: '500'
            },
            color: '#475569'
          }
        },
        tooltip: {
          backgroundColor: '#0f2b5c',
          titleColor: '#ffffff',
          bodyColor: '#e2e8f0',
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || '';
              if (label) {
                label = label.split(' (')[0] + ': ';
              }
              if (context.parsed.y !== null) {
                label += '$' + context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          },
          ticks: {
            color: '#64748b',
            font: {
              family: "'Inter', sans-serif",
              size: 11
            }
          }
        },
        y: {
          grid: {
            color: '#f1f5f9',
            borderDash: [4, 4]
          },
          ticks: {
            color: '#64748b',
            font: {
              family: "'Inter', sans-serif",
              size: 11
            },
            callback: function (value) {
              return '$' + value.toLocaleString();
            }
          }
        }
      }
    }
  });
});

