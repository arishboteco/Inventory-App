# Inventory-App

Inventory-App is a Streamlit application for managing restaurant inventory. It helps track items, suppliers, stock movements and more using a PostgreSQL database.

## Features

- Item and supplier management
- Stock movement logging and history reports
- Indents and purchase order tracking
- Dashboard showing key metrics such as low-stock items

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
