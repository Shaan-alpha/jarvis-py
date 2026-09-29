import logging

import core.utils.logger as lg


def test_log_file_handler_is_utf8():
    # Windows FileHandlers default to the locale codepage (cp1252 here), which
    # cannot encode non-Latin-1 text. A transcript or reply containing any such
    # character then raises inside logging and the whole line is dropped.
    assert (lg._file_handler.encoding or "").lower().replace("-", "") == "utf8"


def test_non_ascii_log_line_is_written(tmp_path):
    path = tmp_path / "probe.log"

    handler = logging.FileHandler(path, encoding=lg._file_handler.encoding)

    handler.setFormatter(logging.Formatter("%(message)s"))

    record = logging.LogRecord(
        "Jarvis", logging.INFO, __file__, 1, "User Query: café ☕", None, None
    )

    # emit() swallows encoding failures (it routes them to handleError), so the
    # file contents — not an exception — are what prove the line survived.
    handler.emit(record)

    handler.close()

    assert "café ☕" in path.read_text(encoding="utf-8")


def test_log_file_rotates_instead_of_growing_forever():
    from logging.handlers import RotatingFileHandler
    assert isinstance(lg._file_handler, RotatingFileHandler)
    assert lg._file_handler.maxBytes == 2 * 1024 * 1024
    assert lg._file_handler.backupCount == 3


def test_the_test_suite_does_not_write_the_real_log():
    # Test runs used to write thousands of lines into the user's jarvis.log and
    # rotate it three times in one day, pushing out their real history.
    import logging
    assert lg._file_handler not in logging.getLogger().handlers
