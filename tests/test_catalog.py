from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from harlequin.exception import HarlequinQueryError
from psycopg import OperationalError

from harlequin_questdb.adapter import QuestDBConnection
from harlequin_questdb.catalog import (
    DatabaseCatalogItem,
    MaterializedViewCatalogItem,
    TableCatalogItem,
)
from harlequin_questdb.connect import resolve_connect_config
from harlequin_questdb.labels import column_type_label
from harlequin_questdb.sql import (
    escape_quest_literal,
    quote_quest_identifier,
    table_columns_sql,
)

DATA = Path(__file__).resolve().parent / "data" / "pin_meta.json"


def _pin() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(DATA.read_text(encoding="utf-8"))
    return loaded


def test_escape_and_quote() -> None:
    assert escape_quest_literal("tricky'name") == "tricky''name"
    assert quote_quest_identifier('col"name') == '"col""name"'
    sql = table_columns_sql("tricky'name", include_designated=True)
    assert "tricky''name" in sql
    assert "tricky'name" not in sql.replace("tricky''name", "")


def test_get_relation_columns_sends_escaped_sql() -> None:
    seen: list[str] = []

    class Cursor:
        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            seen.append(sql)
            assert prepare is False

        def fetchall(self) -> list[tuple[str, str, bool]]:
            return [("id", "INT", False)]

    class Worker:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def __init__(self) -> None:
            self.worker = Worker()

        def getconn(self) -> Worker:
            return self.worker

        def putconn(self, conn: Worker) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    rows = connection._get_relation_columns("tricky'name")
    assert rows == [("id", "INT", False)]
    assert any("tricky''name" in sql for sql in seen)
    assert all("tricky'name" not in sql.replace("tricky''name", "") for sql in seen)


def test_catalog_partition_and_designated_labels() -> None:
    pin = _pin()
    connection = QuestDBConnection.__new__(QuestDBConnection)

    def list_relations() -> list[tuple[str, str, str | None, str | None]]:
        rows: list[tuple[str, str, str | None, str | None]] = []
        for row in pin["tables_rows"]:
            kind = "MATERIALIZED VIEW" if row["matView"] else "BASE TABLE"
            rows.append(
                (
                    str(row["table_name"]),
                    kind,
                    row.get("partitionBy"),
                    row.get("designatedTimestamp"),
                )
            )
        return rows

    def get_relation_columns(relation: str) -> list[tuple[str, str, bool]]:
        columns = pin["table_columns"].get(relation, [])
        return [
            (str(column["column"]), str(column["type"]), bool(column.get("designated")))
            for column in columns
        ]

    connection._list_schemas = lambda: ["public"]  # type: ignore[method-assign]
    connection._list_relations = list_relations  # type: ignore[method-assign]
    connection._get_relation_columns = get_relation_columns  # type: ignore[method-assign]

    database = DatabaseCatalogItem.from_label("qdb", connection)
    relations = database.fetch_children()[0].fetch_children()
    by_name = {relation.label: relation for relation in relations}
    assert by_name["readings"].type_label == "t·DAY"
    assert isinstance(by_name["readings"], TableCatalogItem)
    assert by_name["readings_mv"].type_label == "mv·MONTH"
    assert isinstance(by_name["readings_mv"], MaterializedViewCatalogItem)
    assert by_name["plain_table"].type_label == "t"
    readings_columns = by_name["readings"].fetch_children()
    timestamp = next(col for col in readings_columns if col.label == "ts")
    assert timestamp.type_label == "ts★"
    plain_columns = by_name["plain_table"].fetch_children()
    identifier = next(col for col in plain_columns if col.label == "id")
    assert identifier.type_label == "##"
    assert column_type_label("DATE", designated=False) == "dt"


def test_relation_sql_falls_back_when_matview_column_is_missing() -> None:
    seen: list[str] = []

    class Cursor:
        def __init__(self) -> None:
            self.sql = ""

        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            self.sql = sql
            seen.append(sql)
            if "matView" in sql:
                raise Exception("column matView does not exist")

        def fetchall(self) -> list[tuple[str, str, str, None]]:
            return [("plain_table", "BASE TABLE", "NONE", None)]

    class Worker:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Worker:
            return Worker()

        def putconn(self, conn: Worker) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    rows = connection._list_relations()
    assert rows[0][0] == "plain_table"
    assert any("matView" in sql for sql in seen)
    assert any("BASE TABLE" in sql and "matView" not in sql for sql in seen)


def test_dead_connection_does_not_disable_designated_columns() -> None:
    class Cursor:
        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            raise OperationalError("connection lost")

        def fetchall(self) -> list[tuple[object, ...]]:
            return []

    class Worker:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Worker:
            return Worker()

        def putconn(self, conn: Worker) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    with pytest.raises(HarlequinQueryError):
        connection._get_relation_columns("readings")
    assert connection._relation_columns_include_designated is True


def test_missing_designated_column_falls_back_once() -> None:
    class Cursor:
        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            if "designated" in sql:
                raise Exception("column designated does not exist")

        def fetchall(self) -> list[tuple[str, str]]:
            return [("id", "INT")]

    class Worker:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Worker:
            return Worker()

        def putconn(self, conn: Worker) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    rows = connection._get_relation_columns("plain_table")
    assert rows == [("id", "INT", False)]
    assert connection._relation_columns_include_designated is False


def test_designated_text_flag_is_not_python_truthiness() -> None:
    class Cursor:
        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            return None

        def fetchall(self) -> list[tuple[str, str, str]]:
            return [("ts", "TIMESTAMP", "f"), ("id", "INT", "t")]

    class Worker:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Worker:
            return Worker()

        def putconn(self, conn: Worker) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    rows = connection._get_relation_columns("readings")
    assert rows == [("ts", "TIMESTAMP", False), ("id", "INT", True)]
