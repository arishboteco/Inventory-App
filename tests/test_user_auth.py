from app.auth import user_auth


def test_register_and_verify(sqlite_engine):
    ok, msg = user_auth.register_user(sqlite_engine, "alice", "secret", role="admin")
    assert ok
    success, role = user_auth.verify_login(sqlite_engine, "alice", "secret")
    assert success
    assert role == "admin"
