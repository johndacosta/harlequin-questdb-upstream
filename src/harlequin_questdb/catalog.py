from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from harlequin.catalog import InteractiveCatalogItem
from harlequin_questdb.adapter import _quote_quest_identifier
from harlequin_questdb.interactions import (
    insert_columns_at_cursor,
    show_questdb_columns,
    show_questdb_partitions,
    show_select_star,
)

if TYPE_CHECKING:
    from harlequin_questdb.adapter import HarlequinQuestDbConnection


def _relation_type_label(kind_code: str, partition_by: str | None) -> str:
    if partition_by and partition_by.upper() != "NONE":
        return f"{kind_code}·{partition_by}"
    return kind_code


@dataclass
class ColumnCatalogItem(InteractiveCatalogItem["HarlequinQuestDbConnection"]):
    parent: "RelationCatalogItem | None" = None

    @classmethod
    def from_parent(
        cls,
        parent: "RelationCatalogItem",
        label: str,
        type_label: str,
    ) -> ColumnCatalogItem:
        column_qualified_identifier = (
            f"{parent.qualified_identifier}.{_quote_quest_identifier(label)}"
        )
        column_query_name = _quote_quest_identifier(label)
        return cls(
            qualified_identifier=column_qualified_identifier,
            query_name=column_query_name,
            label=label,
            type_label=type_label,
            connection=parent.connection,
            parent=parent,
            loaded=True,
        )


@dataclass
class RelationCatalogItem(InteractiveCatalogItem["HarlequinQuestDbConnection"]):
    INTERACTIONS = [
        ("Insert Columns at Cursor", insert_columns_at_cursor),
        ("Preview Data", show_select_star),
        ("SHOW COLUMNS (buffer)", show_questdb_columns),
        ("SHOW PARTITIONS (buffer)", show_questdb_partitions),
    ]
    parent: SchemaCatalogItem | None = None

    def fetch_children(self) -> list[ColumnCatalogItem]:
        if self.parent is None or self.parent.parent is None or self.connection is None:
            return []
        result = self.connection._get_relation_columns(relation=self.label)
        return [
            ColumnCatalogItem.from_parent(
                parent=self,
                label=column_name,
                type_label=(
                    f"{self.connection.short_questdb_type(native_type)}★"
                    if designated
                    else self.connection.short_questdb_type(native_type)
                ),
            )
            for column_name, native_type, designated in result
        ]


class ViewCatalogItem(RelationCatalogItem):
    INTERACTIONS = RelationCatalogItem.INTERACTIONS

    @classmethod
    def from_parent(
        cls,
        parent: SchemaCatalogItem,
        label: str,
        *,
        partition_by: str | None = None,
    ) -> ViewCatalogItem:
        relation_query_name = (
            f"{_quote_quest_identifier(parent.label)}.{_quote_quest_identifier(label)}"
        )
        relation_qualified_identifier = (
            f"{parent.qualified_identifier}.{_quote_quest_identifier(label)}"
        )
        return cls(
            qualified_identifier=relation_qualified_identifier,
            query_name=relation_query_name,
            label=label,
            type_label=_relation_type_label("v", partition_by),
            connection=parent.connection,
            parent=parent,
        )


class TableCatalogItem(RelationCatalogItem):
    INTERACTIONS = RelationCatalogItem.INTERACTIONS

    @classmethod
    def from_parent(
        cls,
        parent: SchemaCatalogItem,
        label: str,
        *,
        partition_by: str | None = None,
    ) -> TableCatalogItem:
        relation_query_name = (
            f"{_quote_quest_identifier(parent.label)}.{_quote_quest_identifier(label)}"
        )
        relation_qualified_identifier = (
            f"{parent.qualified_identifier}.{_quote_quest_identifier(label)}"
        )
        return cls(
            qualified_identifier=relation_qualified_identifier,
            query_name=relation_query_name,
            label=label,
            type_label=_relation_type_label("t", partition_by),
            connection=parent.connection,
            parent=parent,
        )


class MaterializedViewCatalogItem(RelationCatalogItem):
    INTERACTIONS = RelationCatalogItem.INTERACTIONS

    @classmethod
    def from_parent(
        cls,
        parent: SchemaCatalogItem,
        label: str,
        *,
        partition_by: str | None = None,
    ) -> MaterializedViewCatalogItem:
        relation_query_name = (
            f"{_quote_quest_identifier(parent.label)}.{_quote_quest_identifier(label)}"
        )
        relation_qualified_identifier = (
            f"{parent.qualified_identifier}.{_quote_quest_identifier(label)}"
        )
        return cls(
            qualified_identifier=relation_qualified_identifier,
            query_name=relation_query_name,
            label=label,
            type_label=_relation_type_label("mv", partition_by),
            connection=parent.connection,
            parent=parent,
        )


@dataclass
class SchemaCatalogItem(InteractiveCatalogItem["HarlequinQuestDbConnection"]):
    parent: DatabaseCatalogItem | None = None

    @classmethod
    def from_parent(
        cls,
        parent: DatabaseCatalogItem,
        label: str,
    ) -> SchemaCatalogItem:
        schema_identifier = _quote_quest_identifier(label)
        return cls(
            qualified_identifier=schema_identifier,
            query_name=schema_identifier,
            label=label,
            type_label="sch",
            connection=parent.connection,
            parent=parent,
        )

    def fetch_children(self) -> list[RelationCatalogItem]:
        if self.parent is None or self.connection is None:
            return []
        children: list[RelationCatalogItem] = []
        for (
            table_label,
            table_type,
            partition_by,
            _designated_ts,
        ) in self.connection._list_relations():
            if table_type == "VIEW":
                children.append(
                    ViewCatalogItem.from_parent(
                        parent=self,
                        label=table_label,
                        partition_by=partition_by,
                    )
                )
            elif table_type == "MATERIALIZED VIEW":
                children.append(
                    MaterializedViewCatalogItem.from_parent(
                        parent=self,
                        label=table_label,
                        partition_by=partition_by,
                    )
                )
            else:
                children.append(
                    TableCatalogItem.from_parent(
                        parent=self,
                        label=table_label,
                        partition_by=partition_by,
                    )
                )
        return children


class DatabaseCatalogItem(InteractiveCatalogItem["HarlequinQuestDbConnection"]):
    @classmethod
    def from_label(
        cls, label: str, connection: "HarlequinQuestDbConnection"
    ) -> DatabaseCatalogItem:
        database_identifier = _quote_quest_identifier(label)
        return cls(
            qualified_identifier=database_identifier,
            query_name=database_identifier,
            label=label,
            type_label="db",
            connection=connection,
        )

    def fetch_children(self) -> list[SchemaCatalogItem]:
        if self.connection is None:
            return []
        schemas = self.connection._list_schemas()
        return [
            SchemaCatalogItem.from_parent(parent=self, label=schema_label)
            for schema_label in schemas
        ]
