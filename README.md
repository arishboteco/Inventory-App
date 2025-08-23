# Inventory-App

Inventory-App is a Django application for managing restaurant inventory with a PostgreSQL database.

## Features

- Item and supplier management
- Stock movement logging and history reports
- Indent and purchase order tracking
- Dashboard showing key metrics such as low-stock items
- Bulk upload items and stock transactions from CSV files

## Style Guide

Refer to [STYLEGUIDE.md](STYLEGUIDE.md) for design tokens, reusable components and usage examples. When creating new templates or JavaScript-driven components, prefer Tailwind CSS utilities and the classes defined in `app.css` before adding custom styles.

## Responsive Breakpoints

This project uses a desktop-first Tailwind CSS strategy. Base styles target larger screens, while `max-*` variants provide overrides for smaller viewports. Custom `max-sm`, `max-md`, `max-lg`, and `max-xl` screens are defined in `tailwind.config.js`. Use these utilities when building templates so mobile adjustments are explicit:

```html
<div class="grid grid-cols-4 max-md:grid-cols-1"></div>
```

## Predictive Dropdowns

Any `<select>` element with the `predictive` class is automatically enhanced with a text input and datalist that filters options as you type. Django forms that use `StyledFormMixin` add this class to select widgets by default. To enable the predictive behaviour on your own dropdown, add `class="predictive"` to the `<select>` or include the class in the widget's `attrs` when defining the form field.

## Installation

Install dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Code Style and Linting

This project uses [pre-commit](https://pre-commit.com/) with `flake8` to enforce
style rules.

Install the git hooks:

```bash
pre-commit install
```

Run lint checks for all files:

```bash
pre-commit run --all-files
```

## Configuration

Configuration is controlled via environment variables. Copy `.env.example` to `.env` and set values for your database and other settings:

```bash
cp .env.example .env
# edit .env with your configuration
```

You can also set these values directly in the environment instead of using a `.env` file.

To fetch item categories and unit options from Supabase, configure:

- `SUPABASE_URL`
- `SUPABASE_KEY`

Without these variables the application will not load category or unit data from Supabase.

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

## List View Utilities

Reusable helpers for filtering, sorting, pagination and CSV export live in
`inventory/services/list_utils.py`. The Items, Suppliers, GRN and Purchase
Order list views use these functions to avoid duplicating boilerplate code.

```python
from inventory.services import list_utils

qs, params = list_utils.apply_filters_sort(
    request,
    Item.objects.all(),
    search_fields=["name"],
    filter_fields={"category": "category"},
    allowed_sorts={"name"},
    default_sort="name",
)
page_obj, _ = list_utils.paginate(request, qs)
```

`list_utils.export_as_csv` can turn any iterable into a downloadable CSV by
supplying the header row and a function that builds each data row.

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
