"""Compatibility wrapper for legacy recipe service.

This module re-exports the legacy ``recipe_service`` functions from the
Streamlit codebase so tests can import them via the Django application's
namespace.  The actual implementation still lives in the legacy module and
continues to rely on SQLAlchemy; migrating it to Django ORM is tracked
separately.
"""

from legacy_streamlit.app.services.recipe_service import *  # noqa: F401,F403

