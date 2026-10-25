from __future__ import annotations

from unittest.mock import MagicMock

from harlequin_questdb.adapter import QuestDBConnection
from harlequin_questdb.completions import base_questdb_completions
from harlequin_questdb.connect import resolve_connect_config
from harlequin_questdb.interactions import show_select_star


def test_static_completions_include_questdb_dialect() -> None:
    labels = {item.label for item in base_questdb_completions()}
    assert "SAMPLE BY" in labels
    assert "ASOF JOIN" in labels
    assert "LATEST ON" in labels
    assert "tables()" in labels


def test_get_completions_keeps_static_list_when_functions_fail() -> None:
    class Worker:
        autocommit = False

        def cursor(self) -> Worker:
            raise RuntimeError("functions() unavailable")

    class Pool:
        def __init__(self) -> None:
            self.main = MagicMock()
            self.main.closed = False

        def getconn(self) -> object:
            return self.main if self.main is not None else Worker()

        def putconn(self, conn: object) -> None:
            return None

        def close(self) -> None:
            return None

    pool = Pool()
    # First getconn is the editor connection. Later borrows must fail introspection.
    workers = [pool.main, Worker()]

    def getconn() -> object:
        return workers.pop(0)

    pool.getconn = getconn  # type: ignore[method-assign]
    connection = QuestDBConnection(resolve_connect_config(()), pool=pool)
    labels = {item.label for item in connection.get_completions()}
    assert "SAMPLE BY" in labels


def test_preview_interaction_inserts_qualified_name() -> None:
    item = MagicMock()
    item.qualified_identifier = '"public"."readings"'
    driver = MagicMock()
    show_select_star(item, driver)
    text = driver.insert_text_in_new_buffer.call_args.args[0]
    assert '"public"."readings"' in text
    assert "limit 100" in text
