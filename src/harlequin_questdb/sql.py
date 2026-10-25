"""QuestDB introspection SQL. User-supplied names are escaped before interpolation."""

from __future__ import annotations


def escape_quest_literal(value: str) -> str:
    """Double single quotes inside a QuestDB string literal."""
    return value.replace("'", "''")


def quote_quest_identifier(label: str) -> str:
    """Quote an identifier, doubling embedded double quotes."""
    return '"' + label.replace('"', '""') + '"'


def table_columns_sql(relation: str, *, include_designated: bool) -> str:
    """SQL for one relation's columns. `relation` is escaped, not a bound parameter.

    QuestDB's `table_columns` takes a SQL string literal. A placeholder would
    not be a substitute for that literal on the PGWire path we use.
    """
    literal = escape_quest_literal(relation)
    if include_designated:
        selected = '"column", type, designated'
    else:
        selected = '"column", type'
    return f"select {selected} from table_columns('{literal}')"


RELATION_SQL_MATVIEW = """
select
    table_name,
    case
        when matView then 'MATERIALIZED VIEW'
        else 'BASE TABLE'
    end as harlequin_kind,
    "partitionBy",
    "designatedTimestamp"
from tables()
order by table_name asc
""".strip()

RELATION_SQL_LEGACY = """
select
    table_name,
    'BASE TABLE' as harlequin_kind,
    "partitionBy",
    "designatedTimestamp"
from tables()
order by table_name asc
""".strip()
