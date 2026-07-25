from __future__ import annotations

import json
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from harlequin.adapter import HarlequinAdapter, HarlequinConnection
from harlequin.catalog import Catalog
from harlequin_questdb import QuestDBAdapter, QuestDBAdapter_OPTIONS
from harlequin_questdb.adapter import (
    HarlequinQuestDbAdapter,
    HarlequinQuestDbConnection,
    _escape_quest_literal,
    _quote_quest_identifier,
)
from harlequin_questdb.catalog import (
    DatabaseCatalogItem,
    MaterializedViewCatalogItem,
    TableCatalogItem,
)

DATA_DIR = Path(__file__).resolve().parent / "data"


@pytest.fixture
def pin_meta() -> dict[str, Any]:
    with open(DATA_DIR / "pin_meta.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def stubbed_connection(pin_meta: dict[str, Any]) -> HarlequinQuestDbConnection:
    conn = MagicMock(spec=HarlequinQuestDbConnection)
    type_short = HarlequinQuestDbConnection.QUEST_TYPE_SHORT

    def short_questdb_type(native: str) -> str:
        base = native.upper().split("(")[0].strip()
        return type_short.get(base, "?")

    conn.short_questdb_type = short_questdb_type

    def list_relations() -> list[tuple[str, str, str | None, str | None]]:
        rows: list[tuple[str, str, str | None, str | None]] = []
        for row in pin_meta["tables_rows"]:
            kind = "MATERIALIZED VIEW" if row["matView"] else "BASE TABLE"
            rows.append(
                (
                    row["table_name"],
                    kind,
                    row.get("partitionBy"),
                    row.get("designatedTimestamp"),
                )
            )
        return rows

    def get_relation_columns(
        relation: str,
    ) -> list[tuple[str, str, bool]]:
        cols = pin_meta["table_columns"].get(relation, [])
        return [
            (c["column"], c["type"], bool(c.get("designated", False))) for c in cols
        ]

    conn._list_relations = list_relations
    conn._get_relation_columns = get_relation_columns
    conn._list_schemas = lambda: ["public"]
    return conn


def test_plugin_discovery() -> None:
    eps = entry_points(group="harlequin.adapter")
    adapter_cls = eps["questdb"].load()
    assert issubclass(adapter_cls, HarlequinAdapter)
    assert adapter_cls is QuestDBAdapter


def test_public_api_aliases() -> None:
    assert QuestDBAdapter is HarlequinQuestDbAdapter
    assert QuestDBAdapter_OPTIONS


def test_username_kwarg_compat() -> None:
    adapter = HarlequinQuestDbAdapter(
        conn_str=tuple(),
        username="legacy_user",
    )
    assert adapter.pool_kwargs["user"] == "legacy_user"


def test_default_password_matches_0_3_x() -> None:
    adapter = HarlequinQuestDbAdapter(conn_str=tuple())
    assert adapter.pool_kwargs["password"] == "quest"


def test_contract_implements_cancel() -> None:
    assert HarlequinQuestDbAdapter.IMPLEMENTS_CANCEL is True
    assert HarlequinQuestDbConnection.cancel is not HarlequinConnection.cancel


def test_escape_quest_literal() -> None:
    assert _escape_quest_literal("tricky'name") == "tricky''name"


def test_quote_quest_identifier() -> None:
    assert _quote_quest_identifier('col"name') == '"col""name"'


def test_catalog_partition_and_designated_labels(
    stubbed_connection: HarlequinQuestDbConnection,
) -> None:
    stubbed_connection._logical_database_label = lambda: "qdb"  # type: ignore[method-assign]
    db = DatabaseCatalogItem.from_label(label="qdb", connection=stubbed_connection)
    catalog = Catalog(items=[db])
    schemas = catalog.items[0].fetch_children()
    relations = schemas[0].fetch_children()

    by_name = {r.label: r for r in relations}
    assert by_name["readings"].type_label == "t·DAY"
    assert by_name["readings_mv"].type_label == "mv·MONTH"
    assert isinstance(by_name["readings_mv"], MaterializedViewCatalogItem)
    assert isinstance(by_name["plain_table"], TableCatalogItem)

    ts_cols = by_name["readings"].fetch_children()
    ts_col = next(c for c in ts_cols if c.label == "ts")
    assert ts_col.type_label == "ts★"
