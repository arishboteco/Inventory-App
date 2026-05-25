"""Shared JSON payloads for drawer/modal form validation errors."""


def get_field_label(form_like, field_name: str) -> str:
    field = getattr(form_like, "fields", {}).get(field_name)
    if field and getattr(field, "label", None):
        return str(field.label)
    return field_name.replace("_", " ").capitalize()


def build_form_error_payload(form, formset=None) -> dict:
    """Collect validation errors into a JSON-serializable dict for JsonResponse."""

    form_non_field_errors = [str(error) for error in form.non_field_errors()]
    formset_non_form_errors = (
        [str(error) for error in formset.non_form_errors()] if formset else []
    )

    form_errors: dict[str, list[str]] = {}
    first_form_field_error = None
    for field_name, errors in form.errors.items():
        error_texts = [str(error) for error in errors]
        if not error_texts:
            continue
        form_errors[field_name] = error_texts
        if first_form_field_error is None:
            label = get_field_label(form, field_name)
            first_form_field_error = f"{label}: {error_texts[0]}"

    formset_errors: list[dict] = []
    first_formset_field_error = None
    forms = list(formset.forms) if formset else []
    total_forms = len(forms)
    for index, form_instance in enumerate(forms):
        child_errors: dict[str, list[str]] = {}
        for field_name, errors in form_instance.errors.items():
            error_texts = [str(error) for error in errors]
            if not error_texts:
                continue
            child_errors[field_name] = error_texts
            if first_formset_field_error is None:
                label = get_field_label(form_instance, field_name)
                prefix = f"Row {index + 1} - " if total_forms > 1 else ""
                first_formset_field_error = f"{prefix}{label}: {error_texts[0]}"
        if child_errors:
            formset_errors.append({"index": index, "errors": child_errors})

    message_parts: list[str] = []
    message_parts.extend(form_non_field_errors)
    message_parts.extend(formset_non_form_errors)
    if first_form_field_error:
        message_parts.append(first_form_field_error)
    if first_formset_field_error:
        message_parts.append(first_formset_field_error)

    if not message_parts:
        message_parts.append("Please correct the highlighted errors and try again.")

    message = " ".join(part.strip() for part in message_parts if part)

    return {
        "ok": False,
        "message": message,
        "errors": {
            "form": form_errors,
            "form_non_field": form_non_field_errors,
            "formset_non_form": formset_non_form_errors,
            "formset": formset_errors,
        },
    }
