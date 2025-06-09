import os
import streamlit as st

# Mapping of configuration keys to their corresponding environment variables
_DB_ENV_VARS = {
    "engine": "DB_ENGINE",
    "user": "DB_USER",
    "password": "DB_PASSWORD",
    "host": "DB_HOST",
    "port": "DB_PORT",
    "dbname": "DB_NAME",
}


def load_db_config():
    """Return database configuration from environment or Streamlit secrets."""
    # Pull values from environment variables first
    env_config = {k: os.getenv(env) for k, env in _DB_ENV_VARS.items()}
    if all(env_config.values()):
        return env_config

    # Fallback to Streamlit secrets
    if "database" in st.secrets:
        secrets_config = {k: st.secrets["database"].get(k, "") for k in _DB_ENV_VARS}
        if all(secrets_config.values()):
            return secrets_config

    return None
