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
