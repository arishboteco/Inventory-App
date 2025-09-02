import logging

from django.test import RequestFactory

from core.error_logging_middleware import DetailedErrorLoggingMiddleware


class DummyUser:
    def __str__(self):
        return "dummyuser"


def test_middleware_redacts_sensitive_info(caplog):
    middleware = DetailedErrorLoggingMiddleware(lambda req: None)
    rf = RequestFactory()
    request = rf.post(
        "/test/",
        {
            "username": "alice",
            "password": "topsecret",
            "csrfmiddlewaretoken": "token123",
        },
        HTTP_AUTHORIZATION="Bearer abc123",
        HTTP_COOKIE="sessionid=xyz",
    )
    request.user = DummyUser()

    with caplog.at_level(logging.ERROR):
        middleware.process_exception(request, ValueError("boom"))

    log_output = " ".join(record.getMessage() for record in caplog.records)

    assert "topsecret" not in log_output
    assert "abc123" not in log_output
    assert "sessionid=xyz" not in log_output
    assert "[REDACTED]" in log_output
    assert "Request Info" in log_output
    assert "/test/" in log_output
    assert "POST" in log_output
    assert "dummyuser" in log_output


def test_process_exception_returns_custom_500_and_logs(caplog):
    middleware = DetailedErrorLoggingMiddleware(lambda req: None)
    rf = RequestFactory()
    request = rf.get("/error/")
    request.user = DummyUser()

    with caplog.at_level(logging.ERROR):
        response = middleware.process_exception(request, ValueError("boom"))

    assert response.status_code == 500
    content = response.content.decode()
    assert "Something went wrong" in content

    log_output = " ".join(record.getMessage() for record in caplog.records)
    assert "🚨 DETAILED ERROR REPORT 🚨" in log_output
    assert "Exception Message: boom" in log_output
