# Inventory-App

Inventory-App is a Streamlit application for managing restaurant inventory. It helps track items, suppliers, stock movements and more using a PostgreSQL database.

## Features

- Item and supplier management
- Stock movement logging and history reports
- Indents and purchase order tracking
- Dashboard showing key metrics such as low-stock items
- Unified sidebar navigation for quick access to all pages
- Automatic unit inference so new items get sensible base and purchase units

## Changelog

- Recipes editor now reuses the Indents item selector and supports selecting stock items or sub-recipes with automatic unit and category population.

## Unit Inference

The app includes a lightweight **unit inference module** that guesses an item's base unit (e.g. `kg`, `ltr`, `pcs`) and optional purchase unit from its name or category. This removes the need for a separate database table of units – when a new item is added, the service automatically assigns sensible defaults so users don't have to enter them manually.

To extend the behaviour, edit `app/core/unit_inference.py`:

* Add keywords to the `_NAME_KEYWORD_MAP` for name-based matches.
* Add categories to `_CATEGORY_DEFAULT_MAP` for category-based defaults.
* Modify or replace the `infer_units` function if more advanced heuristics are needed.

### Example

```python
from app.services.item_service import add_new_item

# base_unit becomes 'ltr' and purchase_unit 'carton'
success, msg = add_new_item(engine, {"name": "Whole Milk", "category": "Dairy"})
```

## Installation

Install dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Running

Launch the Streamlit app from the repository root:

```bash
streamlit run app/item_manager_app.py
```

## Configuration

Before running the app, create a `.streamlit/secrets.toml` file containing your database credentials. An example file can be found at `.streamlit/secrets.toml` in this repository—copy it and replace the placeholder values with your own. The committed sample uses obvious placeholders so you must supply real values.

Alternatively you can provide the database settings via environment variables. If the following variables are set, they will be used instead of the values in `secrets.toml`:

```
DB_ENGINE
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
DB_NAME
```

## Customizing the Sidebar Logo

The sidebar image displayed in the app is defined in `app/ui/logo.py` as a base64 encoded PNG. To use your own logo:

1. Convert your PNG image to a base64 string:

   ```python
   import base64

   with open("my_logo.png", "rb") as f:
       print(base64.b64encode(f.read()).decode())
   ```

2. Replace the `LOGO_BASE64` value in `app/ui/logo.py` with the string printed above.

Restart the application and your logo will appear in the sidebar.
