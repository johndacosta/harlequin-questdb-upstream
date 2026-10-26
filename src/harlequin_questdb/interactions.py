from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Sequence

from harlequin.catalog import CatalogItem
from harlequin.driver import HarlequinDriver

if TYPE_CHECKING:
    from harlequin_questdb.catalog import ColumnCatalogItem, RelationCatalogItem


def show_select_star(item: RelationCatalogItem, driver: HarlequinDriver) -> None:
    driver.insert_text_in_new_buffer(
        dedent(
            f"""
            select *
            from {item.qualified_identifier}
            limit 100
            """.strip("\n")
        )
    )


def insert_columns_at_cursor(
    item: RelationCatalogItem, driver: HarlequinDriver
) -> None:
    if item.loaded:
        cols: Sequence[CatalogItem | ColumnCatalogItem] = item.children
    else:
        cols = item.fetch_children()
    driver.insert_text_at_selection(text=",\n".join(col.query_name for col in cols))


def show_questdb_columns(item: RelationCatalogItem, driver: HarlequinDriver) -> None:
    driver.insert_text_in_new_buffer(
        dedent(
            f"""
            show columns from {item.qualified_identifier}
            ;
            """.strip("\n")
        )
    )


def show_questdb_partitions(item: RelationCatalogItem, driver: HarlequinDriver) -> None:
    """Insert a partition listing. Confirm the statement against the server version."""
    driver.insert_text_in_new_buffer(
        dedent(
            f"""
            show partitions from {item.qualified_identifier}
            ;
            """.strip("\n")
        )
    )
