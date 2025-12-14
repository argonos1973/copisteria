(function () {
  const LETTERS = 'TRWAGMYFPDXBNJZSQVHLCKE';
  const CIF_CONTROL_LETTERS = 'JABCDEFGHI';

  function normalize(value) {
    return String(value || '')
      .toUpperCase()
      .replace(/\s+/g, '')
      .replace(/-/g, '');
  }

  function validateNIF(value) {
    const v = normalize(value);
    if (!/^[0-9]{8}[A-Z]$/.test(v)) return { valid: false, type: 'NIF', normalized: v };
    const num = parseInt(v.slice(0, 8), 10);
    const expected = LETTERS[num % 23];
    return { valid: v[8] === expected, type: 'NIF', normalized: v };
  }

  function validateNIE(value) {
    const v = normalize(value);
    if (!/^[XYZ][0-9]{7}[A-Z]$/.test(v)) return { valid: false, type: 'NIE', normalized: v };
    const prefix = v[0] === 'X' ? '0' : v[0] === 'Y' ? '1' : '2';
    const num = parseInt(prefix + v.slice(1, 8), 10);
    const expected = LETTERS[num % 23];
    return { valid: v[8] === expected, type: 'NIE', normalized: v };
  }

  function validateSpecialNIF(value) {
    const v = normalize(value);
    if (!/^[KLM][0-9]{7}[A-Z]$/.test(v)) return { valid: false, type: 'NIF', normalized: v };
    const num = parseInt(v.slice(1, 8), 10);
    const expected = LETTERS[num % 23];
    return { valid: v[8] === expected, type: 'NIF', normalized: v };
  }

  function validateCIF(value) {
    const v = normalize(value);
    if (!/^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J]$/.test(v)) return { valid: false, type: 'CIF', normalized: v };

    const letter = v[0];
    const digits = v.slice(1, 8);
    const control = v[8];

    let sum = 0;
    for (let i = 0; i < digits.length; i++) {
      const n = parseInt(digits[i], 10);
      if (i % 2 === 0) {
        const p = n * 2;
        sum += Math.floor(p / 10) + (p % 10);
      } else {
        sum += n;
      }
    }

    const controlDigit = (10 - (sum % 10)) % 10;
    const controlLetter = CIF_CONTROL_LETTERS[controlDigit];

    const mustBeLetter = 'PQSKW'.includes(letter);
    const mustBeDigit = 'ABEH'.includes(letter);

    let ok;
    if (mustBeLetter) ok = control === controlLetter;
    else if (mustBeDigit) ok = control === String(controlDigit);
    else ok = control === String(controlDigit) || control === controlLetter;

    return { valid: ok, type: 'CIF', normalized: v };
  }

  function validate(value) {
    const v = normalize(value);
    if (!v) return { valid: true, type: 'EMPTY', normalized: v };

    if (/^[0-9]{8}[A-Z]$/.test(v)) return validateNIF(v);
    if (/^[XYZ][0-9]{7}[A-Z]$/.test(v)) return validateNIE(v);
    if (/^[KLM][0-9]{7}[A-Z]$/.test(v)) return validateSpecialNIF(v);
    if (/^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J]$/.test(v)) return validateCIF(v);

    return { valid: false, type: 'UNKNOWN', normalized: v };
  }

  function isValid(value) {
    return validate(value).valid;
  }

  function applyInputState(input, iconEl, state) {
    if (!input) return;

    if (state.valid) {
      input.style.borderColor = '';
      input.classList.remove('nifcif-invalid');
      input.classList.add('nifcif-valid');
      input.setCustomValidity('');
      if (iconEl) {
        iconEl.className = 'validation-icon fas fa-check';
        iconEl.style.color = 'var(--success, #27ae60)';
      }
    } else {
      input.style.borderColor = '#dc3545';
      input.classList.add('nifcif-invalid');
      input.classList.remove('nifcif-valid');
      input.setCustomValidity('NIF/NIE/CIF no válido');
      if (iconEl) {
        iconEl.className = 'validation-icon fas fa-times';
        iconEl.style.color = 'var(--danger, #e74c3c)';
      }
    }
  }

  function attachToInput(input, opts) {
    if (!input) return;

    const options = opts || {};
    const required = !!options.required;
    const iconEl = options.iconEl || null;

    const run = () => {
      const raw = input.value;
      const v = normalize(raw);
      input.value = v;

      if (!v) {
        if (required) {
          applyInputState(input, iconEl, { valid: false });
          return false;
        }
        input.style.borderColor = '';
        input.classList.remove('nifcif-invalid');
        input.classList.remove('nifcif-valid');
        input.setCustomValidity('');
        if (iconEl) {
          iconEl.className = 'validation-icon';
          iconEl.style.color = '';
        }
        return true;
      }

      const res = validate(v);
      applyInputState(input, iconEl, res);
      return res.valid;
    };

    input.addEventListener('blur', run);
    input.addEventListener('input', () => {
      input.setCustomValidity('');
      if (iconEl) {
        iconEl.className = 'validation-icon';
        iconEl.style.color = '';
      }
    });

    return run;
  }

  function autoAttach() {
    const inputs = Array.from(document.querySelectorAll('input[data-validate-nifcif="1"]'));
    inputs.forEach((input) => {
      const required = input.hasAttribute('required') || input.dataset.nifcifRequired === '1';
      const iconId = input.dataset.nifcifIcon;
      const iconEl = iconId ? document.getElementById(iconId) : null;
      const runner = attachToInput(input, { required, iconEl });

      const form = input.form;
      if (form) {
        form.addEventListener('submit', (e) => {
          const ok = runner ? runner() : isValid(input.value);
          if (!ok) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof window.mostrarNotificacion === 'function') {
              window.mostrarNotificacion('El NIF/NIE/CIF introducido no es válido', 'error');
            } else {
              alert('El NIF/NIE/CIF introducido no es válido');
            }
          }
        }, true);
      }
    });
  }

  window.NifCifValidator = {
    normalize,
    validate,
    isValid,
    attachToInput,
    autoAttach
  };

  document.addEventListener('DOMContentLoaded', () => {
    try {
      autoAttach();
    } catch (_) {}
  });
})();
