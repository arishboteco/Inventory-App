def test_import_app():
    import app
    assert hasattr(app, '__file__') or hasattr(app, '__path__')
