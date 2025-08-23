function initFormset({ formsetPrefix, addButtonId, formContainer, formClass, removeButtonClass, templateId }) {
  const addBtn = document.getElementById(addButtonId);
  const container = document.querySelector(formContainer);
  if (!addBtn || !container) {
    return;
  }
  const totalForms = document.getElementById(`id_${formsetPrefix}-TOTAL_FORMS`);
  let emptyForm;
  if (templateId) {
    const tpl = document.getElementById(templateId);
    emptyForm = tpl ? tpl.content : null;
  }
  if (!emptyForm) {
    const firstForm = container.querySelector(`.${formClass}`);
    emptyForm = firstForm ? firstForm.cloneNode(true) : null;
  }
  if (!emptyForm) {
    return;
  }
  addBtn.addEventListener('click', function (e) {
    e.preventDefault();
    const formCount = parseInt(totalForms.value, 10);
    const newForm = emptyForm.cloneNode(true);
    newForm.querySelectorAll('input, select, textarea').forEach(function (el) {
      let name = el.getAttribute('name');
      if (!name) return;
      if (name.indexOf('__prefix__') !== -1) {
        name = name.replace('__prefix__', formCount);
      } else {
        name = name.replace(/-\d+-/, '-' + formCount + '-');
      }
      const id = 'id_' + name;
      el.setAttribute('name', name);
      el.setAttribute('id', id);
      if (el.type !== 'hidden') {
        el.value = '';
      }
    });
    container.appendChild(newForm);
    totalForms.value = formCount + 1;
  });
  if (removeButtonClass) {
    container.addEventListener('click', function (e) {
      if (e.target.classList.contains(removeButtonClass)) {
        const forms = container.querySelectorAll(`.${formClass}`);
        if (forms.length > 1) {
          e.target.closest(`.${formClass}`).remove();
          totalForms.value = forms.length - 1;
        }
      }
    });
  }
}
window.initFormset = initFormset;
