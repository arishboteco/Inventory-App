// Real-time form validation
// Adds event listeners to inputs to show success/error feedback

document.addEventListener("DOMContentLoaded", () => {
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
            error.textContent = input.validationMessage;
            error.classList.remove("hidden");
          }
        }
      };

      input.addEventListener("input", validate);
      input.addEventListener("blur", validate);
    });
  });
});
