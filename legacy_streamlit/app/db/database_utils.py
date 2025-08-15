"""Database utility helpers.

This module provides helper functions to connect to the database and execute
queries. Logging guidelines:

* Routine success messages should not be logged. Use ``DEBUG`` for optional
  diagnostic information.
* Reserve ``WARNING`` and ``ERROR`` levels for exceptional or unexpected
  conditions.
"""

import streamlit as st
from sqlalchemy import create_engine, text

# Corrected import from sqlalchemy.exc
from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
    SQLAlchemyError,
    IntegrityError,
)
from sqlalchemy.engine import Engine, Connection
import pandas as pd
from typing import Any, Optional, Dict, Tuple

from ..core.logging import get_logger
from ..config import load_db_config

logger = get_logger(__name__)


@st.cache_resource(show_spinner="Connecting to database…")
def connect_db() -> Optional[Engine]:
    """Establish a connection to the database."""
    try:
        db_config = load_db_config()
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not db_config or not all(db_config.get(k) for k in required_keys):
            st.error(
                "Database configuration missing. Set environment variables or provide .streamlit/secrets.toml."
            )
            return None

        db_user = db_config.get("user", "")
        db_password = db_config.get("password", "")
        db_host = db_config.get("host", "")
        db_port = db_config.get("port", "5432")
        db_name = db_config.get("dbname", "")
        db_engine_type = db_config.get("engine", "postgresql")

        connection_url = (
            f"{db_engine_type}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        engine = create_engine(connection_url, pool_pre_ping=True, echo=False)

        with engine.connect():
            logger.debug("Database connection established using connect_db().")
            return engine

    except OperationalError as e:
        st.error(
            f"Database connection failed: Check host, port, credentials.\nError: {e}"
        )
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during DB connection: {e}")
        return None


def fetch_data(
    db_obj: Any, query: str, params: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Fetches data using a SQL query and returns a Pandas DataFrame.
    db_obj can be an SQLAlchemy Engine or an active Connection.
    """
    if db_obj is None:
        logger.error("ERROR (fetch_data): Database object (engine/connection) not provided.")
        return pd.DataFrame()

    try:
        if isinstance(db_obj, Connection):
            result = db_obj.execute(text(query), params or {})
            df = pd.DataFrame(result.mappings().all())
            return df
        elif isinstance(db_obj, Engine):
            with db_obj.connect() as conn_obj:  # Use a different variable name for the connection
                result = conn_obj.execute(text(query), params or {})
                df = pd.DataFrame(result.mappings().all())
                return df
        else:
            logger.error(
                "ERROR (fetch_data): Invalid database object type passed: %s", type(db_obj)
            )
            return pd.DataFrame()

    except (
        ProgrammingError,
        OperationalError,
        SQLAlchemyError,
    ) as e:  # IntegrityError is a subclass of SQLAlchemyError, but explicit catch is fine
        logger.error(
            "ERROR (fetch_data): Database query error: %s. Query: %s... Params: %s",
            e,
            query[:150],
            params,
        )
        return pd.DataFrame()
    except Exception as e:
        logger.error(
            "ERROR (fetch_data): Unexpected error during data fetch: %s. Query: %s... Params: %s",
            e,
            query[:150],
            params,
        )
        return pd.DataFrame()


def execute_query(
    engine: Engine, query: str, params: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[Any]]:
    """
    Executes a query that modifies data (INSERT, UPDATE, DELETE).
    Returns success status and potentially the number of affected rows or lastrowid.
    This function manages its own transaction.
    """
    if engine is None:
        logger.error("ERROR (execute_query): Database engine not available.")
        return False, None
    try:
        with engine.connect() as connection_obj:  # Use a different variable name
            with connection_obj.begin():
                result = connection_obj.execute(text(query), params or {})
            # result.rowcount is typically what you want for CUD operations
            return True, result.rowcount
    except (
        IntegrityError,
        ProgrammingError,
        OperationalError,
        SQLAlchemyError,
    ) as e:  # Catch IntegrityError here
        logger.error(
            "ERROR (execute_query): Database execution error: %s. Query: %s... Params: %s",
            e,
            query[:150],
            params,
        )
        return False, str(e)
    except Exception as e:
        logger.error(
            "ERROR (execute_query): Unexpected error: %s. Query: %s... Params: %s",
            e,
            query[:150],
            params,
        )
        return False, str(e)
