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

## Customizing the Sidebar Logo

To override the default sidebar image, place a file named `logo.png` in
`app/ui/`. When present, the application loads this file automatically.
If no such file exists, the built-in base64 image defined in `app/ui/logo.py`
is used instead.

Optional fallback: you can still embed a custom image by replacing the value of
`LOGO_BASE64` in `app/ui/logo.py`. Convert your PNG to a base64 string and
assign it to `LOGO_BASE64` if you prefer not to keep a separate file.
