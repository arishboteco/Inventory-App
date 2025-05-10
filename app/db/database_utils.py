# app/db/database_utils.py
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
import pandas as pd
from typing import Any, Optional, Dict

@st.cache_resource(show_spinner="Connecting to database…")
def connect_db():
    """Establishes a connection to the database using credentials from secrets."""
    try:
        if "database" not in st.secrets:
            st.error("Database configuration missing in secrets.toml!")
            st.info("Ensure `.streamlit/secrets.toml` has [database] section with keys: engine, user, host, etc.")
            return None
        db = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db for key in required_keys):
            missing = [k for k in required_keys if k not in db]
            st.error(f"Missing keys in database secrets: {', '.join(missing)}")
            st.info("Expected keys: engine, user, password, host, port, dbname.")
            return None

        db_user = db.get('user', '')
        db_password = db.get('password', '')
        db_host = db.get('host', '')
        db_port = db.get('port', '5432')
        db_name = db.get('dbname', '')
        db_engine_type = db.get('engine', 'postgresql')

        connection_url = f"{db_engine_type}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_url, pool_pre_ping=True, echo=False)

        with engine.connect() as connection:
            return engine

    except OperationalError as e:
        st.error(f"Database connection failed: Check host, port, credentials.\nError: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during DB connection: {e}")
        return None

def fetch_data(engine, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Fetches data using a SQL query and returns a Pandas DataFrame."""
    if engine is None:
        st.error("Database engine not available for fetch_data.")
        return pd.DataFrame()
    try:
        with engine.connect() as connection:
            result = connection.execute(text(query), params or {})
            df = pd.DataFrame(result.mappings().all())
            return df
    except (ProgrammingError, OperationalError, SQLAlchemyError) as e:
        st.error(f"Database query error: {e}\nQuery: {query}\nParams: {params}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred during data fetch: {e}")
        return pd.DataFrame()