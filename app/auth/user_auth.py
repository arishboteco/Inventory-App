import traceback
from typing import Optional, Tuple

import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from app.core.logging import get_logger

logger = get_logger(__name__)


def register_user(engine: Engine, username: str, password: str, role: str = "staff") -> Tuple[bool, str]:
    """Create a new user with hashed password."""
    if engine is None:
        return False, "Database engine not available"
    if not username or not password:
        return False, "Username and password required"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r)"
                ),
                {"u": username, "p": password_hash, "r": role},
            )
        return True, "User registered"
    except IntegrityError:
        return False, "Username already exists"
    except SQLAlchemyError as e:
        logger.error("ERROR [user_auth.register_user]: %s\n%s", e, traceback.format_exc())
        return False, "Database error during registration"


def verify_login(engine: Engine, username: str, password: str) -> Tuple[bool, Optional[str]]:
    """Verify username/password, returning role if valid."""
    if engine is None:
        return False, None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT password_hash, role FROM users WHERE username=:u"),
                {"u": username},
            ).mappings().fetchone()
            if not row:
                return False, None
            stored_hash = row["password_hash"].encode()
            if bcrypt.checkpw(password.encode(), stored_hash):
                return True, row["role"]
            return False, None
    except SQLAlchemyError as e:
        logger.error("ERROR [user_auth.verify_login]: %s\n%s", e, traceback.format_exc())
        return False, None
