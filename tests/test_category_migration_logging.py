import logging
from unittest.mock import MagicMock, patch

from inventory.utils import category_migration


def _mock_cursor(return_fetchall=None, fetchone_side_effect=None):
    cursor = MagicMock()
    if return_fetchall is not None:
        cursor.fetchall.return_value = return_fetchall
    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    return cursor_context, cursor


def test_migrate_item_categories_logs_when_no_items(caplog):
    cursor_context, cursor = _mock_cursor(return_fetchall=[])
    with patch.object(category_migration, "connection") as conn_mock:
        conn_mock.cursor.return_value = cursor_context
        with caplog.at_level(logging.INFO):
            category_migration.migrate_item_categories(dry_run=True)
    assert "No items need category migration." in caplog.text


def test_cleanup_duplicate_category_fields_warns_when_unmigrated(caplog):
    cursor_context, cursor = _mock_cursor(fetchone_side_effect=[(1,)])
    with patch.object(category_migration, "connection") as conn_mock:
        conn_mock.cursor.return_value = cursor_context
        with caplog.at_level(logging.WARNING):
            result = category_migration.cleanup_duplicate_category_fields()
    assert result is False
    assert "Cannot cleanup: 1 items still need category_id migration" in caplog.text
