"""Live QuestDB checks. Excluded from the default run by the `live` marker."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from harlequin.catalog import Catalog
from harlequin.exception import HarlequinQueryError
from textual_fastdatatable.backend import create_backend

from harlequin_questdb.adapter import QuestDBAdapter, QuestDBConnection, QuestDBCursor
from harlequin_questdb.catalog import DatabaseCatalogItem

pytestmark = pytest.mark.live


@pytest.fixture
def connection() -> Iterator[QuestDBConnection]:
    try:
        connected = QuestDBAdapter(conn_str=()).connect()
    except Exception as exc:
        pytest.skip(f"QuestDB is not reachable: {exc}")
    yield connected
    connected.close()


def test_get_catalog(connection: QuestDBConnection) -> None:
    catalog = connection.get_catalog()
    assert isinstance(catalog, Catalog)
    assert catalog.items
    top = catalog.items[0]
    assert isinstance(top, DatabaseCatalogItem)
    assert top.type_label == "db"
    assert top.fetch_children()


def test_execute_select(connection: QuestDBConnection) -> None:
    cursor = connection.execute("select 1 as a")
    assert isinstance(cursor, QuestDBCursor)
    assert cursor.columns() == [("a", "##")]
    data = cursor.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 1


def test_set_limit(connection: QuestDBConnection) -> None:
    cursor = connection.execute("select 1 as a union all select 2 union all select 3")
    assert isinstance(cursor, QuestDBCursor)
    limited = cursor.set_limit(2)
    data = limited.fetchall()
    backend = create_backend(data)
    assert backend.row_count == 2


def test_execute_raises_query_error(connection: QuestDBConnection) -> None:
    with pytest.raises(HarlequinQueryError):
        connection.execute("selec;")
