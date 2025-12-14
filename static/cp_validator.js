(function () {
  const DEFAULT_API_BASE = '/api/contactos';

  function normalizeCp(value) {
    return String(value || '')
      .trim()
      .replace(/\s+/g, '')
      .replace(/[^0-9]/g, '')
      .slice(0, 5);
  }

  function isValidFormat(cp) {
    return /^[0-9]{5}$/.test(cp);
  }

  function debounce(fn, wait) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  }

  function applyInputState(input, iconEl, state) {
    if (!input) return;

    if (state.valid) {
      input.style.borderColor = '';
      input.classList.remove('cp-invalid');
      input.classList.add('cp-valid');
      input.setCustomValidity('');
      if (iconEl) {
        iconEl.className = 'validation-icon fas fa-check';
        iconEl.style.color = 'var(--success, #27ae60)';
      }
    } else {
      input.style.borderColor = '#dc3545';
      input.classList.add('cp-invalid');
      input.classList.remove('cp-valid');
      input.setCustomValidity(state.message || 'CP no válido');
      if (iconEl) {
        iconEl.className = 'validation-icon fas fa-times';
        iconEl.style.color = 'var(--danger, #e74c3c)';
      }
    }
  }

  function resetState(input, iconEl) {
    if (!input) return;
    input.style.borderColor = '';
    input.classList.remove('cp-invalid');
    input.classList.remove('cp-valid');
    input.setCustomValidity('');
    if (iconEl) {
      iconEl.className = 'validation-icon';
      iconEl.style.color = '';
    }
  }

  function findInScope(scopeEl, selector) {
    if (!scopeEl) return null;
    try {
      return scopeEl.querySelector(selector);
    } catch (_) {
      return null;
    }
  }

  function resolveRelatedFields(cpInput, opts) {
    const options = opts || {};
    const scope = options.scope || cpInput.form || cpInput.closest('form') || document;

    const localityId = options.localityId || cpInput.dataset.cpLocalityId;
    const provinceId = options.provinceId || cpInput.dataset.cpProvinceId;
    const localitySyncId = options.localitySyncId || cpInput.dataset.cpLocalitySyncId;

    const iconId = options.iconId || cpInput.dataset.cpIcon;

    let localityInput = null;
    let provinceInput = null;
    let localitySyncInput = null;

    if (localityId) {
      localityInput = (scope === document ? document.getElementById(localityId) : findInScope(scope, `#${CSS.escape(localityId)}`));
    } else {
      localityInput =
        findInScope(scope, '#poblacio') ||
        findInScope(scope, '#poblacion') ||
        findInScope(scope, '#localidad') ||
        findInScope(scope, '#ciudad');
    }

    if (provinceId) {
      provinceInput = (scope === document ? document.getElementById(provinceId) : findInScope(scope, `#${CSS.escape(provinceId)}`));
    } else {
      provinceInput = findInScope(scope, '#provincia');
    }

    if (localitySyncId) {
      localitySyncInput = (scope === document ? document.getElementById(localitySyncId) : findInScope(scope, `#${CSS.escape(localitySyncId)}`));
    } else {
      // Caso especial GESTION_CONTACTOS: visible #poblacio + hidden #poblacion
      const maybeVisible = localityInput;
      if (maybeVisible && maybeVisible.id === 'poblacio') {
        localitySyncInput = findInScope(scope, '#poblacion');
      }
    }

    const iconEl = iconId ? document.getElementById(iconId) : null;

    return { scope, localityInput, provinceInput, localitySyncInput, iconEl };
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function getCpData(cp, apiBase) {
    const base = apiBase || DEFAULT_API_BASE;
    const url = `${base}/get_cp?cp=${encodeURIComponent(cp)}`;
    const data = await fetchJson(url);
    if (!Array.isArray(data)) return [];
    return data;
  }

  async function searchCp(prefix, apiBase) {
    const base = apiBase || DEFAULT_API_BASE;
    const url = `${base}/search_cp?term=${encodeURIComponent(prefix)}`;
    const data = await fetchJson(url);
    if (!Array.isArray(data)) return [];
    return data;
  }

  function ensureDatalist(cpInput) {
    if (!cpInput) return null;

    const existingId = cpInput.getAttribute('list');
    if (existingId) {
      const dl = document.getElementById(existingId);
      if (dl && dl.tagName === 'DATALIST') return dl;
    }

    if (cpInput.dataset.cpDatalistId) {
      const dl = document.getElementById(cpInput.dataset.cpDatalistId);
      if (dl && dl.tagName === 'DATALIST') return dl;
    }

    const id = `cp-datalist-${Math.random().toString(36).slice(2)}`;
    const dl = document.createElement('datalist');
    dl.id = id;
    document.body.appendChild(dl);
    cpInput.setAttribute('list', id);
    cpInput.dataset.cpDatalistId = id;
    return dl;
  }

  function showNotification(msg) {
    if (typeof window.mostrarNotificacion === 'function') {
      window.mostrarNotificacion(msg, 'error');
    } else {
      alert(msg);
    }
  }

  function attachToInput(cpInput, opts) {
    if (!cpInput) return null;

    const options = opts || {};
    const apiBase = options.apiBase || cpInput.dataset.cpApiBase || DEFAULT_API_BASE;

    const noSubmitBlock =
      !!options.noSubmitBlock ||
      cpInput.dataset.cpNoSubmitBlock === '1';

    const required =
      !!options.required ||
      cpInput.hasAttribute('required') ||
      cpInput.dataset.cpRequired === '1';

    const rel = resolveRelatedFields(cpInput, options);

    let lastLookup = { cp: '', ok: null, pending: false };

    const datalist = ensureDatalist(cpInput);
    const doSearch = debounce(async (rawPrefix) => {
      const prefix = normalizeCp(rawPrefix).slice(0, 4);
      if (!datalist) return;
      if (!prefix || prefix.length < 2 || prefix.length > 4) {
        datalist.innerHTML = '';
        return;
      }
      try {
        const items = await searchCp(prefix, apiBase);
        datalist.innerHTML = '';
        items.forEach((item) => {
          const opt = document.createElement('option');
          opt.value = item.cp;
          opt.label = `${item.cp} - ${item.poblacio} (${item.provincia})`;
          datalist.appendChild(opt);
        });
      } catch (_) {
        // Silencioso
      }
    }, 300);

    const fillFields = (poblacio, provincia) => {
      if (rel.localityInput) rel.localityInput.value = poblacio || '';
      if (rel.localitySyncInput) rel.localitySyncInput.value = poblacio || '';
      if (rel.provinceInput) rel.provinceInput.value = provincia || '';
    };

    const validateAndFill = async (forceLookup) => {
      const cp = normalizeCp(cpInput.value);
      cpInput.value = cp;

      if (!cp) {
        if (required) {
          applyInputState(cpInput, rel.iconEl, { valid: false, message: 'CP obligatorio' });
          fillFields('', '');
          lastLookup = { cp: '', ok: false, pending: false };
          return { ok: false, known: true };
        }
        resetState(cpInput, rel.iconEl);
        fillFields('', '');
        lastLookup = { cp: '', ok: true, pending: false };
        return { ok: true, known: true };
      }

      if (!isValidFormat(cp)) {
        applyInputState(cpInput, rel.iconEl, { valid: false, message: 'CP no válido (5 dígitos)' });
        fillFields('', '');
        lastLookup = { cp, ok: false, pending: false };
        return { ok: false, known: true };
      }

      if (!forceLookup && lastLookup.cp === cp && lastLookup.ok !== null && !lastLookup.pending) {
        if (lastLookup.ok) {
          applyInputState(cpInput, rel.iconEl, { valid: true });
        } else {
          applyInputState(cpInput, rel.iconEl, { valid: false, message: 'CP no existe' });
        }
        return { ok: !!lastLookup.ok, known: true };
      }

      if (lastLookup.pending) {
        return { ok: false, known: false };
      }

      lastLookup = { cp, ok: null, pending: true };
      try {
        const data = await getCpData(cp, apiBase);
        const row = data && data[0] ? data[0] : null;
        if (row) {
          const poblacio = row.poblacio || '';
          const provincia = row.provincia || '';
          fillFields(poblacio, provincia);
          applyInputState(cpInput, rel.iconEl, { valid: true });
          lastLookup = { cp, ok: true, pending: false };
          return { ok: true, known: true };
        }
        fillFields('', '');
        applyInputState(cpInput, rel.iconEl, { valid: false, message: 'CP no existe' });
        lastLookup = { cp, ok: false, pending: false };
        return { ok: false, known: true };
      } catch (_) {
        // Si hay error de red, no marcamos como inválido definitivo
        applyInputState(cpInput, rel.iconEl, { valid: false, message: 'No se pudo validar el CP' });
        lastLookup = { cp, ok: false, pending: false };
        return { ok: false, known: true };
      }
    };

    cpInput.addEventListener('input', (e) => {
      const cp = normalizeCp(e.target.value);
      e.target.value = cp;
      e.target.setCustomValidity('');
      if (rel.iconEl) {
        rel.iconEl.className = 'validation-icon';
        rel.iconEl.style.color = '';
      }
      lastLookup.ok = null;
      lastLookup.pending = false;

      doSearch(cp);
      if (cp.length === 5) {
        validateAndFill(false);
      }
    });

    cpInput.addEventListener('blur', () => {
      validateAndFill(true);
    });

    const form = cpInput.form || cpInput.closest('form');
    if (form && !noSubmitBlock) {
      let bypass = false;
      form.addEventListener(
        'submit',
        async (e) => {
          if (bypass) return;

          const cp = normalizeCp(cpInput.value);

          // Si no es requerido y está vacío, no bloqueamos
          if (!required && !cp) return;

          // Si ya sabemos que es válido/no válido sin fetch, actuamos
          const res = await validateAndFill(false);
          if (res.known && res.ok) return;

          // Si no está validado o salió mal, forzamos lookup y bloqueamos el submit actual
          e.preventDefault();
          e.stopPropagation();

          const res2 = await validateAndFill(true);
          if (!res2.ok) {
            showNotification('El CP introducido no es válido');
            return;
          }

          bypass = true;
          try {
            if (typeof form.requestSubmit === 'function') form.requestSubmit();
            else form.submit();
          } finally {
            bypass = false;
          }
        },
        true
      );
    }

    return validateAndFill;
  }

  function autoAttach() {
    const inputs = Array.from(document.querySelectorAll('input[data-validate-cp="1"]'));
    inputs.forEach((input) => {
      if (input.dataset.cpAttached === '1') return;
      input.dataset.cpAttached = '1';
      attachToInput(input, {});
    });
  }

  function observe() {
    const obs = new MutationObserver(() => {
      try {
        autoAttach();
      } catch (_) {}
    });
    obs.observe(document.documentElement || document.body, { childList: true, subtree: true });
  }

  window.CpValidator = {
    normalizeCp,
    isValidFormat,
    attachToInput,
    autoAttach,
    observe,
    getCpData
  };

  document.addEventListener('DOMContentLoaded', () => {
    try {
      autoAttach();
      observe();
    } catch (_) {}
  });
})();
