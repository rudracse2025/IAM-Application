(() => {
  const BULK_OPEN_CONFIRM_THRESHOLD = 5;

  const onReady = () => {
    initDropdowns();
    initToasts();
    initValidation();
    initPasswordToggle();
    initDomainFeedback();
    initPasswordStrength();
    initLoadingStates();
    initConfirmations();
    initTabs();
    initSearchFilter();
    initStepper();
    initSecurityGroups();
    initBulkActions();
    initShortcuts();
  };

  const initDropdowns = () => {
    const profileBtn = document.querySelector('[data-profile-trigger]');
    const profileMenu = document.querySelector('[data-profile-menu]');
    const bellBtn = document.querySelector('[data-notification-trigger]');
    const bellMenu = document.querySelector('[data-notification-menu]');

    if (profileBtn && profileMenu) {
      profileBtn.addEventListener('click', () => profileMenu.classList.toggle('open'));
    }
    if (bellBtn && bellMenu) {
      bellBtn.addEventListener('click', () => bellMenu.classList.toggle('open'));
    }

    document.addEventListener('click', (event) => {
      if (profileMenu && profileBtn && !profileBtn.contains(event.target) && !profileMenu.contains(event.target)) {
        profileMenu.classList.remove('open');
      }
      if (bellMenu && bellBtn && !bellBtn.contains(event.target) && !bellMenu.contains(event.target)) {
        bellMenu.classList.remove('open');
      }
    });
  };

  const initToasts = () => {
    document.querySelectorAll('.toast').forEach((toast) => {
      const timeout = Number(toast.dataset.timeout || 4500);
      setTimeout(() => toast.remove(), timeout);
    });
  };

  const initValidation = () => {
    document.querySelectorAll('form').forEach((form) => {
      const requiredFields = form.querySelectorAll('[required]');
      requiredFields.forEach((field) => {
        field.addEventListener('input', () => validateField(field));
        field.addEventListener('blur', () => validateField(field));
      });

      form.addEventListener('submit', (event) => {
        let isValid = true;
        requiredFields.forEach((field) => {
          if (!validateField(field)) {
            isValid = false;
          }
        });
        if (!isValid) {
          event.preventDefault();
          addToast('Please complete all required fields correctly.', 'danger');
        }
      });
    });
  };

  const validateField = (field) => {
    const hint = field.closest('.field-group')?.querySelector('.validation-hint');
    let error = '';
    if (field.hasAttribute('required') && !field.value.trim()) {
      error = 'This field is required.';
    }
    if (!error && field.type === 'email') {
      const value = field.value.trim();
      const validEmail = isValidEmail(value);
      if (!validEmail) error = 'Enter a valid email address.';
    }

    field.classList.toggle('is-invalid', Boolean(error));
    if (hint) hint.textContent = error;
    return !error;
  };

  const initPasswordToggle = () => {
    document.querySelectorAll('[data-password-toggle]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.dataset.passwordToggle;
        const input = document.getElementById(targetId);
        if (!input) return;
        const visible = input.type === 'text';
        input.type = visible ? 'password' : 'text';
        btn.textContent = visible ? 'Show' : 'Hide';
      });
    });
  };

  const initDomainFeedback = () => {
    const input = document.querySelector('input[name="domain"]');
    const feedback = document.querySelector('[data-domain-feedback]');
    if (!input || !feedback) return;

    const update = () => {
      const value = input.value.trim();
      if (!value) {
        feedback.textContent = '';
        return;
      }
      const valid = /^[a-z0-9.-]+\.[a-z]{2,}$/i.test(value);
      feedback.textContent = valid ? 'Domain format looks good.' : 'Use a valid company domain (example.com).';
      feedback.style.color = valid ? 'var(--success)' : 'var(--danger)';
    };

    input.addEventListener('input', update);
    update();
  };

  const initPasswordStrength = () => {
    const input = document.querySelector('input[name="password"]');
    const meter = document.querySelector('[data-password-strength]');
    if (!input || !meter) return;

    input.addEventListener('input', () => {
      const value = input.value;
      let score = 0;
      if (value.length >= 8) score++;
      if (/[A-Z]/.test(value)) score++;
      if (/[0-9]/.test(value)) score++;
      if (/[^A-Za-z0-9]/.test(value)) score++;

      const labels = ['Very weak', 'Weak', 'Medium', 'Strong', 'Very strong'];
      meter.textContent = `Password strength: ${labels[score]}`;
      meter.style.color = score >= 3 ? 'var(--success)' : 'var(--warning)';
    });
  };

  const initLoadingStates = () => {
    document.querySelectorAll('form').forEach((form) => {
      form.addEventListener('submit', () => {
        form.querySelectorAll('button[type="submit"]').forEach((btn) => {
          if (btn.dataset.skipLoading === 'true') return;
          if (btn.disabled) return;
          btn.disabled = true;
          const label = btn.dataset.loadingText || 'Processing';
          btn.dataset.originalText = btn.textContent;
          btn.innerHTML = `<span class="loading-spinner" aria-hidden="true"></span> ${label}`;
        });
      });
    });
  };

  const initConfirmations = () => {
    const modal = document.querySelector('[data-confirm-modal]');
    const messageEl = modal?.querySelector('[data-confirm-text]');
    const yesBtn = modal?.querySelector('[data-confirm-yes]');
    const noBtn = modal?.querySelector('[data-confirm-no]');
    if (!modal || !messageEl || !yesBtn || !noBtn) return;

    let pendingForm = null;

    document.querySelectorAll('form[data-confirm-message]').forEach((form) => {
      form.addEventListener('submit', (event) => {
        if (form.dataset.confirmed === 'true') {
          form.dataset.confirmed = 'false';
          return;
        }
        event.preventDefault();
        pendingForm = form;
        messageEl.textContent = form.dataset.confirmMessage;
        modal.classList.add('open');
      });
    });

    yesBtn.addEventListener('click', () => {
      if (pendingForm) {
        pendingForm.dataset.confirmed = 'true';
        pendingForm.requestSubmit();
      }
      modal.classList.remove('open');
    });

    noBtn.addEventListener('click', () => {
      pendingForm = null;
      modal.classList.remove('open');
    });
  };

  const initTabs = () => {
    document.querySelectorAll('[data-tab-container]').forEach((container) => {
      const buttons = container.querySelectorAll('[data-tab-target]');
      const panels = container.querySelectorAll('[data-tab-panel]');

      const activate = (id) => {
        buttons.forEach((btn) => btn.classList.toggle('active', btn.dataset.tabTarget === id));
        panels.forEach((panel) => panel.classList.toggle('active', panel.dataset.tabPanel === id));
      };

      buttons.forEach((btn) => {
        btn.addEventListener('click', () => activate(btn.dataset.tabTarget));
      });

      if (buttons[0]) activate(buttons[0].dataset.tabTarget);
    });
  };

  const initSearchFilter = () => {
    document.querySelectorAll('[data-search-input]').forEach((input) => {
      const targets = document.querySelectorAll(input.dataset.searchInput);
      if (!targets.length) return;

      input.addEventListener('input', () => {
        const q = input.value.trim().toLowerCase();
        targets.forEach((target) => {
          target.querySelectorAll('[data-filter-item]').forEach((item) => {
            const text = item.textContent.toLowerCase();
            item.hidden = q && !text.includes(q);
          });
        });
      });
    });
  };

  const initStepper = () => {
    document.querySelectorAll('[data-stepper]').forEach((stepper) => {
      const panels = Array.from(stepper.querySelectorAll('[data-step-panel]'));
      const nextButtons = stepper.querySelectorAll('[data-step-next]');
      const backButtons = stepper.querySelectorAll('[data-step-back]');
      let index = 0;

      const showStep = () => {
        panels.forEach((panel, i) => {
          panel.hidden = i !== index;
        });
      };

      nextButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          if (index < panels.length - 1) index += 1;
          showStep();
        });
      });
      backButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          if (index > 0) index -= 1;
          showStep();
        });
      });

      showStep();
    });
  };

  const initSecurityGroups = () => {
    const hiddenField = document.querySelector('input[name="security_groups"][type="hidden"]');
    if (!hiddenField) return;

    const update = () => {
      const checked = Array.from(document.querySelectorAll('[data-security-group]:checked')).map((el) => el.value);
      hiddenField.value = checked.join(', ');
    };

    document.querySelectorAll('[data-security-group]').forEach((checkbox) => {
      checkbox.addEventListener('change', update);
    });

    update();
  };

  const initBulkActions = () => {
    const master = document.querySelector('[data-bulk-master]');
    const items = document.querySelectorAll('[data-bulk-item]');
    const openBtn = document.querySelector('[data-bulk-open]');
    if (!items.length || !openBtn) return;

    if (master) {
      master.addEventListener('change', () => {
        items.forEach((item) => {
          item.checked = master.checked;
        });
      });
    }

    openBtn.addEventListener('click', () => {
      const selected = Array.from(items).filter((i) => i.checked).map((i) => i.dataset.url);
      if (!selected.length) {
        addToast('Select at least one request first.', 'warning');
        return;
      }
      if (selected.length > BULK_OPEN_CONFIRM_THRESHOLD && !window.confirm(`Open ${selected.length} status pages in new tabs?`)) {
        return;
      }
      selected.forEach((url) => window.open(url, '_blank'));
      addToast(`Opened ${selected.length} status page(s) in new tabs.`, 'success');
    });
  };

  const initShortcuts = () => {
    document.addEventListener('keydown', (event) => {
      if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        const input = document.querySelector('[data-search-input]');
        if (input) {
          event.preventDefault();
          input.focus();
        }
      }
      if (event.altKey && event.shiftKey && event.key.toLowerCase() === 'd') {
        const dashboardLink = document.querySelector('a[href*="/dashboard"]');
        if (dashboardLink) window.location.href = dashboardLink.href;
      }
      if (event.key === '?') {
        addToast('Keyboard shortcuts: / (search), Alt+Shift+D (dashboard).', 'success');
      }
    });
  };

  const addToast = (message, type = 'success') => {
    const container = document.querySelector('.toast-container');
    if (!container) return;
    const div = document.createElement('div');
    div.className = `toast ${type}`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 3500);
  };

  const isValidEmail = (value) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) &&
      !value.includes('..') &&
      !value.split('@')[1]?.startsWith('.') &&
      !value.split('@')[1]?.endsWith('.');
  };

  document.addEventListener('DOMContentLoaded', onReady);
})();
