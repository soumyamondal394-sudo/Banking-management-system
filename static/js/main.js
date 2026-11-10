// Global Apex Bank JS

document.addEventListener('DOMContentLoaded', function () {
  // 1. Sidebar Toggle on Mobile
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });

    // Close when clicking outside on mobile
    document.addEventListener('click', function (e) {
      if (window.innerWidth < 992) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target) && sidebar.classList.contains('show')) {
          sidebar.classList.remove('show');
        }
      }
    });
  }

  // 2. Auto-dismiss flash alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
      } catch (e) {
        alert.style.display = 'none';
      }
    }, 5000);
  });

  // 3. Live UTC / Local Clock Updater
  const liveClockEl = document.getElementById('liveClock');
  if (liveClockEl) {
    function updateClock() {
      const now = new Date();
      liveClockEl.textContent = now.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }
    updateClock();
    setInterval(updateClock, 1000);
  }

  // 4. Copy Account Number to Clipboard
  window.copyToClipboard = function (text, btnElement) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(function () {
      if (btnElement) {
        const originalHtml = btnElement.innerHTML;
        btnElement.innerHTML = '<i class="fa-solid fa-check text-success"></i> Copied!';
        btnElement.classList.add('btn-light');
        setTimeout(function () {
          btnElement.innerHTML = originalHtml;
          btnElement.classList.remove('btn-light');
        }, 2000);
      }
    }).catch(function (err) {
      console.error('Could not copy text: ', err);
    });
  };

  // 5. Format Currency inputs on blur
  const currencyInputs = document.querySelectorAll('.format-currency-input');
  currencyInputs.forEach(input => {
    input.addEventListener('blur', function () {
      let val = parseFloat(this.value);
      if (!isNaN(val) && val > 0) {
        this.value = val.toFixed(2);
      }
    });
  });

  // 6. Initialize Bootstrap Tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
});

