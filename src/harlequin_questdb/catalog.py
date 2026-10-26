from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Sequence, TypeVar, cast

from harlequin.catalog import Interaction, InteractiveCatalogItem

from harlequin_questdb.interactions import (
    insert_columns_at_cursor,
    show_questdb_columns,
    show_questdb_partitions,
    show_select_star,
)
from harlequin_questdb.labels import column_type_label, relation_type_label
from harlequin_questdb.sql import quote_quest_identifier

if TYPE_CHECKING:
    from harlequin_questdb.adapter import QuestDBConnection


_RELATION_INTERACTIONS: Sequence[tuple[str, Interaction[Any]]] = cast(
    Sequence[tuple[str, Interaction[Any]]],
    (
        ("Insert Columns at Cursor", insert_columns_at_cursor),
        ("Preview Data", show_select_star),
        ("SHOW COLUMNS (buffer)", show_questdb_columns),
        ("SHOW PARTITIONS (buffer)", show_questdb_partitions),
    ),
)


@dataclass
class ColumnCatalogItem(InteractiveCatalogItem["QuestDBConnection"]):
    parent: RelationCatalogItem | None = None

    @classmethod
    def from_parent(
        cls,
        parent: RelationCatalogItem,
        label: str,
        type_label: str,
    ) -> ColumnCatalogItem:
        quoted = quote_quest_identifier(label)
        return cls(
            qualified_identifier=f"{parent.qualified_identifier}.{quoted}",
            query_name=quoted,
            label=label,
            type_label=type_label,
            connection=parent.connection,
            parent=parent,
            loaded=True,
        )


@dataclass
class RelationCatalogItem(InteractiveCatalogItem["QuestDBConnection"]):
    INTERACTIONS: ClassVar[Sequence[tuple[str, Interaction[Any]]] | None] = (
        _RELATION_INTERACTIONS
    )
    parent: SchemaCatalogItem | None = None

    def fetch_children(self) -> list[ColumnCatalogItem]:
        if self.connection is None:
            return []
        rows = self.connection._get_relation_columns(relation=self.label)
        return [
            ColumnCatalogItem.from_parent(
                parent=self,
                label=column_name,
                type_label=column_type_label(native_type, designated=designated),
            )
            for column_name, native_type, designated in rows
        ]


_RelationT = TypeVar("_RelationT", bound="RelationCatalogItem")


def _new_relation(
    cls: type[_RelationT],
    parent: SchemaCatalogItem,
    label: str,
    kind_code: str,
    partition_by: str | None,
) -> _RelationT:
    quoted = quote_quest_identifier(label)
    query_name = f"{quote_quest_identifier(parent.label)}.{quoted}"
    return cls(
        qualified_identifier=f"{parent.qualified_identifier}.{quoted}",
        query_name=query_name,
        label=label,
        type_label=relation_type_label(kind_code, partition_by),
        connection=parent.connection,
        parent=parent,
    )


@dataclass
class ViewCatalogItem(RelationCatalogItem):
    """Used when `tables()` reports a view kind. Current pin SQL does not."""

    @classmethod
    def from_parent(
        cls,
        parent: SchemaCatalogItem,
        label: str,
        *,
        partition_by: str | None = None,
    ) -> ViewCatalogItem:
        return _new_relation(cls, parent, label, "v", partition_by)


@dataclass
class TableCatalogItem(RelationCatalogItem):
    @classmethod
    def from_parent(
        cls,
        parent: SchemaCatalogItem,
        label: str,
        *,
        partition_by: str | None = None,
    ) -> TableCatalogItem:
        return _new_relation(cls, parent, label, "t", partition_by)


@dataclass
class MaterializedViewCatalogItem(RelationCatalogItem):
    @classmethod
    def from_parent(
        cls,
        parent: SchemaCatalogItem,
        label: str,
        *,
        partition_by: str | None = None,
    ) -> MaterializedViewCatalogItem:
        return _new_relation(cls, parent, label, "mv", partition_by)


@dataclass
class SchemaCatalogItem(InteractiveCatalogItem["QuestDBConnection"]):
    parent: DatabaseCatalogItem | None = None

    @classmethod
    def from_parent(cls, parent: DatabaseCatalogItem, label: str) -> SchemaCatalogItem:
        identifier = quote_quest_identifier(label)
        return cls(
            qualified_identifier=identifier,
            query_name=identifier,
            label=label,
            type_label="sch",
            connection=parent.connection,
            parent=parent,
        )

    def fetch_children(self) -> list[RelationCatalogItem]:
        if self.connection is None:
            return []
        children: list[RelationCatalogItem] = []
        rows = self.connection._list_relations()
        for table_label, table_type, partition_by, _designated in rows:
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


@dataclass
class DatabaseCatalogItem(InteractiveCatalogItem["QuestDBConnection"]):
    @classmethod
    def from_label(
        cls, label: str, connection: QuestDBConnection
    ) -> DatabaseCatalogItem:
        identifier = quote_quest_identifier(label)
        return cls(
            qualified_identifier=identifier,
            query_name=identifier,
            label=label,
            type_label="db",
            connection=connection,
        )

    def fetch_children(self) -> list[SchemaCatalogItem]:
        if self.connection is None:
            return []
        return [
            SchemaCatalogItem.from_parent(parent=self, label=schema_label)
            for schema_label in self.connection._list_schemas()
        ]
