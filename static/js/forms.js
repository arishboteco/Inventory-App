// Real-time form validation
// Adds event listeners to inputs to show success/error feedback

document.addEventListener("DOMContentLoaded", () => {
  const humanizeName = (value) =>
    String(value || "This field")
      .replace(/^id_/, "")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const labelFor = (input) => {
    if (!input) return "This field";
    const explicitLabel = input.id
      ? document.querySelector(`label[for="${input.id}"]`)
      : null;
    const labelText = explicitLabel ? explicitLabel.textContent.trim() : "";
    return (
      labelText.replace(/\s*\*\s*$/, "") ||
      humanizeName(input.name || input.id)
    );
  };

  const validationMessageFor = (input) => {
    const label = labelFor(input);
    if (input.validity.valueMissing) return `${label} is required.`;
    if (input.validity.typeMismatch)
      return `Enter a valid ${label.toLowerCase()}.`;
    if (input.validity.rangeUnderflow)
      return `${label} must be at least ${input.min}.`;
    if (input.validity.rangeOverflow)
      return `${label} must be no more than ${input.max}.`;
    if (input.validity.stepMismatch)
      return `${label} must use a valid increment.`;
    if (input.validity.tooShort) return `${label} is too short.`;
    if (input.validity.tooLong) return `${label} is too long.`;
    if (input.validity.patternMismatch)
      return `${label} has an invalid format.`;
    if (input.validationMessage) return input.validationMessage;
    return `${label} is invalid.`;
  };

  const forms = document.querySelectorAll("form");
  forms.forEach((form) => {
    const inputs = form.querySelectorAll("input, select, textarea");
    inputs.forEach((input) => {
      const container = input.closest("div");
      if (!container) return;
      const success = container.querySelector('[data-feedback="success"]');
      const error = container.querySelector('[data-feedback="error"]');

      const validate = () => {
        if (input.checkValidity()) {
          if (success) {
            success.textContent = "Looks good!";
            success.classList.remove("hidden");
          }
          if (error) {
            error.textContent = "";
            error.classList.add("hidden");
          }
        } else {
          if (success) {
            success.textContent = "";
            success.classList.add("hidden");
          }
          if (error) {
            error.textContent = validationMessageFor(input);
            error.classList.remove("hidden");
          }
        }
      };

      input.addEventListener("input", validate);
      input.addEventListener("blur", validate);
    });
  });
});
