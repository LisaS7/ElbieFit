document.addEventListener('click', function (event) {
  const button = event.target.closest("[data-action='increment'], [data-action='decrement']");
  if (!button) return;

  const stepper = button.closest('.number-stepper');
  if (!stepper) return;

  const input = stepper.querySelector("input[type='number']");
  if (!input) return;

  const action = button.dataset.action;
  const stepAttr = stepper.dataset.step || input.step || '1';
  const minAttr = stepper.dataset.min || input.min;
  const maxAttr = stepper.dataset.max || input.max;

  const step = parseFloat(stepAttr) || 1;
  const min = minAttr === '' || minAttr == null ? null : parseFloat(minAttr);
  const max = maxAttr === '' || maxAttr == null ? null : parseFloat(maxAttr);

  let value = input.value === '' ? 0 : parseFloat(input.value);
  if (isNaN(value)) value = 0;

  if (action === 'increment') {
    value += step;
  } else if (action === 'decrement') {
    value -= step;
  }

  if (min !== null && value < min) value = min;
  if (max !== null && value > max) value = max;

  // Allow empty if optional (like weight) and we go below min 0
  if (value === 0 && (min === null || min === 0) && input.name === 'weight_kg') {
    input.value = '';
  } else {
    input.value = value.toString();
  }

  // Fire input event so anything listening (HTMX, etc.) can react
  const ev = new Event('input', { bubbles: true });
  input.dispatchEvent(ev);
});
