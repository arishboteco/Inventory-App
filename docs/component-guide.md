# Component Guide

A quick reference for common UI components used throughout the application.

## Buttons

`templates/components/button.html`

```django
{% include "components/button.html" with label="Save" type="submit" variant="primary" %}
```

Variants: `primary`, `secondary`, `danger`, `icon`, etc. Pass `href` for link-style buttons and `extra_classes` for additional styling.

## Modal

`templates/components/modal.html`

```django
{% include "components/modal.html" with id="sample-modal" open_id="open-btn" content_template="path/to/content.html" %}
```

The `content_template` is rendered inside the modal. Opening and closing behavior is wired automatically based on the IDs provided.

## Tables

`templates/components/basic_table.html`

```django
{% extends "components/basic_table.html" %}
{% block headers %}
  <th>Column A</th>
{% endblock %}
{% block rows %}
  <tr><td>Row 1</td></tr>
{% endblock %}
```

Extend this component to build simple tabular layouts.
