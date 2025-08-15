import importlib
import os
from datetime import datetime, timedelta


def test_purge_old_logs(tmp_path, monkeypatch):
    log_file = tmp_path / "test.log"
    old_file = log_file.with_name(log_file.name + ".1")
    new_file = log_file.with_name(log_file.name + ".2")

    old_file.write_text("old")
    new_file.write_text("new")

    old_time = (datetime.now() - timedelta(days=8)).timestamp()
    new_time = (datetime.now() - timedelta(days=1)).timestamp()
    os.utime(old_file, (old_time, old_time))
    os.utime(new_file, (new_time, new_time))

    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_RETENTION_DAYS", "7")

    import legacy_streamlit.app.core.logging as logging_mod
    importlib.reload(logging_mod)

    logging_mod.configure_logging()

    assert not old_file.exists()
    assert new_file.exists()

    # cleanup handlers
    import logging
    for h in logging.getLogger().handlers[:]:
        h.close()
        logging.getLogger().removeHandler(h)
