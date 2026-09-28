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
