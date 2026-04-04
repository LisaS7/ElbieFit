/**
 * CustomSelect — progressively enhances native <select> elements with a
 * cyberpunk clip-path reveal dropdown. Leaves the DOM otherwise untouched
 * so Jinja2 templates need no changes.
 *
 * Public API
 *   initCustomSelects(root?)  — initialise all <select> elements within root
 *                               (defaults to document). Called automatically
 *                               at DOMContentLoaded and safe to call again on
 *                               HTMX-injected fragments.
 */

(function () {
  'use strict';

  // ─── Helpers ────────────────────────────────────────────────────────────────

  let openInstance = null;

  function closeOpen() {
    if (openInstance) {
      openInstance.close();
      openInstance = null;
    }
  }

  // Close on outside click
  document.addEventListener('click', function (e) {
    if (openInstance && !openInstance.wrapper.contains(e.target)) {
      closeOpen();
    }
  });

  // Close on Escape globally
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && openInstance) {
      closeOpen();
    }
  });

  // ─── CustomSelect class ─────────────────────────────────────────────────────

  function CustomSelect(nativeSelect) {
    this.native = nativeSelect;
    this._build();
    this._bindEvents();
    this._syncFromNative();
  }

  CustomSelect.prototype._build = function () {
    var native = this.native;

    // Wrapper
    var wrapper = document.createElement('div');
    wrapper.className = 'cs-wrapper';
    wrapper.setAttribute('data-custom-select', '');

    // Copy any width-relevant inline styles
    if (native.style.width) wrapper.style.width = native.style.width;

    // Hidden input carries the real form value
    var hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = native.name;
    if (native.required) hidden.required = true;

    // Transfer HTMX attributes from native to hidden input
    var htmxAttrs = ['hx-get', 'hx-post', 'hx-target', 'hx-trigger', 'hx-include', 'hx-swap'];
    htmxAttrs.forEach(function (attr) {
      var val = native.getAttribute(attr);
      if (val !== null) {
        hidden.setAttribute(attr, val);
        native.removeAttribute(attr);
      }
    });

    // Trigger button
    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'cs-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    var triggerLabel = document.createElement('span');
    triggerLabel.className = 'cs-trigger-label';

    var triggerArrow = document.createElement('span');
    triggerArrow.className = 'cs-trigger-arrow';
    triggerArrow.setAttribute('aria-hidden', 'true');

    trigger.appendChild(triggerLabel);
    trigger.appendChild(triggerArrow);

    // Option panel
    var panel = document.createElement('div');
    panel.className = 'cs-panel';
    panel.setAttribute('role', 'listbox');
    panel.setAttribute('tabindex', '-1');

    // Build option items from the native select
    var items = [];
    Array.from(native.options).forEach(function (opt, index) {
      var item = document.createElement('div');
      item.className = 'cs-option';
      if (!opt.value) item.classList.add('cs-option--placeholder');
      item.setAttribute('role', 'option');
      item.setAttribute('data-value', opt.value);
      item.setAttribute('data-index', index);
      item.textContent = opt.text;
      panel.appendChild(item);
      items.push(item);
    });

    wrapper.appendChild(hidden);
    wrapper.appendChild(trigger);
    wrapper.appendChild(panel);

    // Insert wrapper before native select, then hide the native
    native.parentNode.insertBefore(wrapper, native);
    native.style.display = 'none';
    // Keep native in DOM so any server-side form fallback still works,
    // but disable it so it never submits a duplicate value
    native.disabled = true;
    wrapper.appendChild(native);

    // Re-register with HTMX if present (hidden input just appeared)
    if (typeof htmx !== 'undefined') {
      htmx.process(hidden);
    }

    this.wrapper = wrapper;
    this.hidden = hidden;
    this.trigger = trigger;
    this.triggerLabel = triggerLabel;
    this.panel = panel;
    this.items = items;
    this.focusedIndex = -1;
  };

  CustomSelect.prototype._syncFromNative = function () {
    var native = this.native;
    var selectedOpt = native.options[native.selectedIndex];
    if (selectedOpt) {
      this._select(selectedOpt.value, selectedOpt.text, false);
    }
  };

  CustomSelect.prototype._select = function (value, label, fireChange) {
    this.hidden.value = value;

    var isPlaceholder = value === '';
    this.triggerLabel.textContent = label;
    this.triggerLabel.classList.toggle('cs-trigger-label--placeholder', isPlaceholder);

    // Mark selected item
    this.items.forEach(function (item) {
      item.setAttribute('aria-selected', item.dataset.value === value ? 'true' : 'false');
      item.classList.toggle('cs-option--selected', item.dataset.value === value);
    });

    if (fireChange) {
      // Dispatch a real change event so HTMX hx-trigger="change" fires
      this.hidden.dispatchEvent(new Event('change', { bubbles: true }));
    }
  };

  CustomSelect.prototype.open = function () {
    if (openInstance && openInstance !== this) {
      openInstance.close();
    }
    openInstance = this;
    this.panel.classList.add('cs-panel--open');
    this.trigger.setAttribute('aria-expanded', 'true');

    // Focus the currently selected item, or first item
    var selectedIdx = this.items.findIndex(function (item) {
      return item.getAttribute('aria-selected') === 'true';
    });
    this.focusedIndex = selectedIdx >= 0 ? selectedIdx : 0;
    this._focusItem(this.focusedIndex);

    // Flip panel above trigger if not enough space below
    this._positionPanel();
  };

  CustomSelect.prototype.close = function () {
    this.panel.classList.remove('cs-panel--open');
    this.panel.classList.remove('cs-panel--above');
    this.trigger.setAttribute('aria-expanded', 'false');
    this.focusedIndex = -1;
    if (openInstance === this) openInstance = null;
  };

  CustomSelect.prototype._positionPanel = function () {
    var triggerRect = this.trigger.getBoundingClientRect();
    var panelHeight = this.panel.scrollHeight || 240;
    var spaceBelow = window.innerHeight - triggerRect.bottom;
    var spaceAbove = triggerRect.top;

    if (spaceBelow < panelHeight && spaceAbove > spaceBelow) {
      this.panel.classList.add('cs-panel--above');
    } else {
      this.panel.classList.remove('cs-panel--above');
    }
  };

  CustomSelect.prototype._focusItem = function (index) {
    this.items.forEach(function (item) {
      item.classList.remove('cs-option--focused');
    });
    if (index >= 0 && index < this.items.length) {
      var item = this.items[index];
      item.classList.add('cs-option--focused');
      item.scrollIntoView({ block: 'nearest' });
    }
  };

  CustomSelect.prototype._bindEvents = function () {
    var self = this;

    // Toggle open/close on trigger click
    this.trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (self.panel.classList.contains('cs-panel--open')) {
        self.close();
      } else {
        self.open();
      }
    });

    // Click on an option
    this.panel.addEventListener('click', function (e) {
      var item = e.target.closest('.cs-option');
      if (!item) return;
      e.stopPropagation();
      self._select(item.dataset.value, item.textContent, true);
      self.close();
      self.trigger.focus();
    });

    // Keyboard navigation on the trigger
    this.trigger.addEventListener('keydown', function (e) {
      var isOpen = self.panel.classList.contains('cs-panel--open');

      switch (e.key) {
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (isOpen) {
            var focused = self.items[self.focusedIndex];
            if (focused) {
              self._select(focused.dataset.value, focused.textContent, true);
              self.close();
            }
          } else {
            self.open();
          }
          break;

        case 'ArrowDown':
          e.preventDefault();
          if (!isOpen) {
            self.open();
          } else {
            self.focusedIndex = Math.min(self.focusedIndex + 1, self.items.length - 1);
            self._focusItem(self.focusedIndex);
          }
          break;

        case 'ArrowUp':
          e.preventDefault();
          if (!isOpen) {
            self.open();
          } else {
            self.focusedIndex = Math.max(self.focusedIndex - 1, 0);
            self._focusItem(self.focusedIndex);
          }
          break;

        case 'Escape':
          if (isOpen) {
            e.preventDefault();
            self.close();
          }
          break;

        case 'Tab':
          if (isOpen) self.close();
          break;
      }
    });
  };

  // ─── Public init function ────────────────────────────────────────────────────

  function initCustomSelects(root) {
    var context = root || document;
    context.querySelectorAll('select').forEach(function (select) {
      // Skip if already enhanced, or if it's inside a custom-select wrapper
      if (select.closest('[data-custom-select]')) return;
      // Skip selects with the data-no-custom attribute for opt-out
      if (select.hasAttribute('data-no-custom')) return;
      new CustomSelect(select);
    });
  }

  // Auto-init at DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initCustomSelects();
    });
  } else {
    initCustomSelects();
  }

  // Re-init inside HTMX-injected fragments
  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail && e.detail.target) {
      initCustomSelects(e.detail.target);
    }
  });

  // Expose globally for manual use
  window.initCustomSelects = initCustomSelects;
})();
