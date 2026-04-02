import logging
import time

from web.logging import DatadogHandler, setup_logging


def test_datadog_handler_queues_and_sends(mocker):
    mocker.patch("web.config.HOST", "test-host")

    mock_post = mocker.patch("httpx.Client.post")

    handler = DatadogHandler("fake-key", flush_interval=0.1)
    handler.setFormatter(logging.Formatter("%(message)s"))

    record = logging.LogRecord("mylogger", logging.WARNING, "", 0, "test message", (), None)
    handler.emit(record)

    time.sleep(0.3)
    handler.close()

    assert mock_post.call_count >= 1
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["headers"]["DD-API-KEY"] == "fake-key"


def test_datadog_handler_survives_network_error(mocker):
    mocker.patch("web.config.HOST", "test-host")
    mocker.patch("httpx.Client.post", side_effect=ConnectionError("down"))

    handler = DatadogHandler("fake-key", flush_interval=0.1)
    handler.setFormatter(logging.Formatter("%(message)s"))

    record = logging.LogRecord("test", logging.ERROR, "", 0, "boom", (), None)
    handler.emit(record)

    time.sleep(0.3)
    handler.close()


def test_setup_logging_adds_datadog_handler_when_configured(mocker):
    mocker.patch("web.config.DATADOG_API_KEY", "test-key")
    mocker.patch("web.config.HOST", "test-host")
    mocker.patch("httpx.Client.post")

    setup_logging(level=logging.INFO)

    handler_types = [type(h).__name__ for h in logging.root.handlers]
    assert "StreamHandler" in handler_types
    assert "DatadogHandler" in handler_types

    # Cleanup
    for h in logging.root.handlers[:]:
        if isinstance(h, DatadogHandler):
            h.close()
            logging.root.removeHandler(h)


def test_setup_logging_no_datadog_without_key(mocker):
    mocker.patch("web.config.DATADOG_API_KEY", "")

    setup_logging(level=logging.INFO)

    handler_types = [type(h).__name__ for h in logging.root.handlers]
    assert "StreamHandler" in handler_types
    assert "DatadogHandler" not in handler_types
