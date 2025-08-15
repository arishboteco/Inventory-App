# Inventory-App

Inventory-App is a Django application for managing restaurant inventory with a PostgreSQL database.

## Features

- Item and supplier management
- Stock movement logging and history reports
- Indent and purchase order tracking
- Dashboard showing key metrics such as low-stock items
- Automatic unit inference so new items get sensible base and purchase units
- Bulk upload items and stock transactions from CSV files

## Installation

Install dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Configuration

Configuration is controlled via environment variables. Copy `.env.example` to `.env` and set values for your database and other settings:

```bash
cp .env.example .env
# edit .env with your configuration
```

You can also set these values directly in the environment instead of using a `.env` file.

## Running

Apply database migrations and launch the Django development server:

```bash
python manage.py migrate
python manage.py runserver
```

## Unit Inference

The project includes a lightweight **unit inference module** that guesses an item's base unit (e.g. `kg`, `ltr`, `pcs`) and optional purchase unit from its name or category. This removes the need for a separate database table of units – when a new item is added, the service automatically assigns sensible defaults so users don't have to enter them manually.

You can override or extend these heuristics without touching the code by creating a `units.yaml` file in the project root. The file accepts two sections – `name_keywords` and `categories` – whose entries override the default mappings:

```yaml
name_keywords:
  tofu: ["pcs", "block"]
categories:
  spices: ["g", "jar"]
```

To extend the behaviour programmatically, edit `inventory/unit_inference.py`:

* Add keywords to the `_NAME_KEYWORD_MAP` for name-based matches.
* Add categories to `_CATEGORY_DEFAULT_MAP` for category-based defaults.
* Modify or replace the `infer_units` function if more advanced heuristics are needed.

### Example

```python
from inventory.services.item_service import add_new_item

# base_unit becomes 'ltr' and purchase_unit 'carton'
success, msg = add_new_item(engine, {"name": "Whole Milk", "category": "Dairy"})
```

