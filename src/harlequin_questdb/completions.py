from __future__ import annotations

from harlequin import HarlequinCompletion

# Dialect tokens QuestDB adds beyond a typical Postgres keyword list.
_QUESTDB_SQL_SNIPPETS: list[tuple[str, str]] = [
    ("SAMPLE BY", "kw"),
    ("FILL", "kw"),
    ("ALIGN TO", "kw"),
    ("ALIGN TO CALENDAR", "kw"),
    ("LATEST ON", "kw"),
    ("LATEST BY", "kw"),
    ("ASOF JOIN", "kw"),
    ("LT JOIN", "kw"),
    ("WINDOW JOIN", "kw"),
    ("SPLICE JOIN", "kw"),
    ("INTERPOLATE", "kw"),
    ("TTL", "kw"),
    ("PARTITION BY", "kw"),
    ("TIMESTAMP", "kw"),
    ("DESIGNATED", "kw"),
    ("UPSERT KEYS", "kw"),
    ("WAL", "kw"),
]

_QUESTDB_FUNCTIONS: list[str] = [
    "first",
    "last",
    "first_value",
    "last_value",
    "count_distinct",
    "approx_percentile",
    "approx_bounded_percentile",
    "round_down",
    "round_up",
    "date_trunc",
    "cast",
    "make_timestamp",
    "to_timezone",
]

_QUESTDB_META_ALIASES: list[tuple[str, str]] = [
    ("tables()", "fn"),
    ("table_columns()", "fn"),
    ("table_partitions()", "fn"),
    ("table_storage()", "fn"),
    ("materialized_views()", "fn"),
    ("functions()", "fn"),
    ("query_activity()", "fn"),
    ("build()", "fn"),
]

FUNCTIONS_SQL = """
select distinct name as routine_name
from functions()
where
    name is not null
    and length(name) < 48
order by 1 asc
limit 4000
""".strip()


def base_questdb_completions() -> list[HarlequinCompletion]:
    completions: list[HarlequinCompletion] = []
    for label, type_label in _QUESTDB_SQL_SNIPPETS:
        completions.append(
            HarlequinCompletion(
                label=label,
                type_label=type_label,
                value=label,
                priority=900,
                context="questdb-sql",
            )
        )
    for name in _QUESTDB_FUNCTIONS:
        completions.append(
            HarlequinCompletion(
                label=name,
                type_label="fn",
                value=name,
                priority=950,
                context="questdb-sql",
            )
        )
    for label, type_label in _QUESTDB_META_ALIASES:
        completions.append(
            HarlequinCompletion(
                label=label,
                type_label=type_label,
                value=label,
                priority=800,
                context="questdb-meta",
            )
        )
    return completions
