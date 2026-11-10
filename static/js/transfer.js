// Real-Time Account Verification & Transfer Validation

document.addEventListener('DOMContentLoaded', function () {
  const receiverInput = document.getElementById('receiverAccountNumber');
  const feedbackBox = document.getElementById('recipientFeedback');
  const transferAmountInput = document.getElementById('transferAmount');
  const balancePreviewEl = document.getElementById('balancePreview');
  const senderAccountSelect = document.getElementById('senderAccountSelect');
  const transferSubmitBtn = document.getElementById('transferSubmitBtn');

  let debounceTimer = null;

  function lookupRecipient(accNumber) {
    if (!accNumber || accNumber.length < 5) {
      if (feedbackBox) {
        feedbackBox.innerHTML = '';
        feedbackBox.className = 'mt-2';
      }
      return;
    }

    if (feedbackBox) {
      feedbackBox.innerHTML = '<span class="text-muted"><i class="fa-solid fa-spinner fa-spin me-1"></i> Verifying account with Apex Core Banking...</span>';
      feedbackBox.className = 'mt-2';
    }

    fetch(`/api/account/lookup?account_number=${encodeURIComponent(accNumber)}`)
      .then(res => res.json())
      .then(data => {
        if (data.found) {
          if (!data.is_active) {
            feedbackBox.innerHTML = `<div class="p-2 rounded bg-warning-subtle text-warning-emphasis small border border-warning"><i class="fa-solid fa-triangle-exclamation me-1"></i> Account found (${data.holder_name}) but it is currently <strong>${data.status}</strong> and cannot receive transfers.</div>`;
            if (transferSubmitBtn) transferSubmitBtn.disabled = true;
          } else if (data.is_own) {
            feedbackBox.innerHTML = `<div class="p-2 rounded bg-info-subtle text-info-emphasis small border border-info"><i class="fa-solid fa-user-check me-1"></i> <strong>Internal Transfer:</strong> Your own account (${data.account_type}).</div>`;
            if (transferSubmitBtn) transferSubmitBtn.disabled = false;
          } else {
            feedbackBox.innerHTML = `<div class="p-2 rounded bg-success-subtle text-success-emphasis small border border-success"><i class="fa-solid fa-circle-check me-1"></i> <strong>Verified Recipient:</strong> ${data.holder_name} (${data.account_type} Account)</div>`;
            if (transferSubmitBtn) transferSubmitBtn.disabled = false;
          }
        } else {
          feedbackBox.innerHTML = `<div class="p-2 rounded bg-danger-subtle text-danger-emphasis small border border-danger"><i class="fa-solid fa-circle-xmark me-1"></i> ${data.message || 'Account not found. Please verify the account number.'}</div>`;
          if (transferSubmitBtn) transferSubmitBtn.disabled = true;
        }
      })
      .catch(err => {
        console.error('Error looking up account:', err);
      });
  }

  if (receiverInput) {
    receiverInput.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      const val = this.value.trim();
      debounceTimer = setTimeout(() => {
        lookupRecipient(val);
      }, 350);
    });

    if (receiverInput.value) {
      lookupRecipient(receiverInput.value.trim());
    }
  }

  // Update Remaining Balance Preview
  function updateBalancePreview() {
    if (!senderAccountSelect || !transferAmountInput || !balancePreviewEl) return;

    const selectedOption = senderAccountSelect.options[senderAccountSelect.selectedIndex];
    if (!selectedOption) return;

    const currentBalance = parseFloat(selectedOption.getAttribute('data-balance') || 0);
    const transferAmt = parseFloat(transferAmountInput.value || 0);

    if (isNaN(transferAmt) || transferAmt <= 0) {
      balancePreviewEl.textContent = `$${currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      balancePreviewEl.classList.remove('text-danger');
      return;
    }

    const remaining = currentBalance - transferAmt;
    if (remaining < 0) {
      balancePreviewEl.textContent = `Insufficient Balance ($${remaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })})`;
      balancePreviewEl.classList.add('text-danger');
      if (transferSubmitBtn) transferSubmitBtn.disabled = true;
    } else {
      balancePreviewEl.textContent = `$${remaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      balancePreviewEl.classList.remove('text-danger');
      if (transferSubmitBtn && (!feedbackBox || !feedbackBox.querySelector('.bg-danger-subtle'))) {
        transferSubmitBtn.disabled = false;
      }
    }
  }

  if (senderAccountSelect) {
    senderAccountSelect.addEventListener('change', updateBalancePreview);
  }
  if (transferAmountInput) {
    transferAmountInput.addEventListener('input', updateBalancePreview);
  }
});

