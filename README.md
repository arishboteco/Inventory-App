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

Create a user account and log in to access the dashboard:

```bash
python manage.py createsuperuser
```

Visit `http://localhost:8000/accounts/login/` to sign in. After a successful
login you will be redirected to the dashboard at `/dashboard/`.

## Docker Deployment

The project includes a production-ready deployment using Docker and
Docker Compose. It sets up three services:

- **web** – the Django application served by Gunicorn
- **nginx** – reverse proxy serving static files
- **db** – PostgreSQL database

### Setup

1. Ensure Docker and Docker Compose are installed.
2. Copy `.env.example` to `.env` and provide values, including a
   `DATABASE_URL` that points to the `db` service and credentials for the
   Postgres container:

   ```env
   DATABASE_URL=postgres://postgres:postgres@db:5432/postgres
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   ```

3. Build and start the stack:

   ```bash
   docker-compose up --build
   ```

   The web container automatically applies database migrations and
   collects static files before launching Gunicorn. Visit
   `http://localhost/` to access the application.

## Purchase Order Tables

The project defines four tables used for purchasing and goods receiving workflows:

- `purchase_orders`
- `purchase_order_items`
- `goods_received_notes`
- `grn_items`

These tables are created via Django migrations in `inventory/migrations/0001_initial.py`.
Run `python manage.py migrate` against your Supabase database to ensure they are
present. If the tables already exist, the models map to them via the `db_table`
option.

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

## API Endpoints

The application exposes the following REST endpoints under `/api/`:

- `/api/items/` – manage items.
- `/api/suppliers/` – manage suppliers.
- `/api/stock-transactions/` – record stock movements.
- `/api/indents/` – manage indents.
- `/api/indent-items/` – manage indent items.
- `/api/recipes/` – manage recipes.
- `/api/recipe-components/` – manage recipe components.
- `/api/purchase-orders/` – create and track purchase orders.
- `/api/purchase-order-items/` – line items within a purchase order.
- `/api/goods-received-notes/` – log received goods.
- `/api/grn-items/` – items contained in a goods received note.

