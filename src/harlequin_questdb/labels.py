"""Short labels for the catalog and the results grid.

Keys that 0.3.x already assigned keep those labels. New keys only add types
the 0.3.x maps did not name.
"""

from __future__ import annotations

# QuestDB native type names from table_columns() → short display labels.
QUESTDB_TYPE_LABELS: dict[str, str] = {
    "BOOLEAN": "t/f",
    "BYTE": "#",
    "SHORT": "#",
    "INT": "##",
    "LONG": "##",
    "LONG128": "##",
    "LONG256": "##",
    "FLOAT": "#.#",
    "DOUBLE": "#.#",
    "REAL": "#.#",
    "NUMBER": "#.#",
    "DECIMAL": "#.#",
    "CHAR": "s",
    "CHARACTER": "s",
    "STRING": "s",
    "VARCHAR": "s",
    "SYMBOL": "sym",
    "DATE": "dt",
    "TIMESTAMP": "ts",
    "BINARY": "bin",
    "UUID": "uid",
    "GEOHASH": "geo",
    "GEOINT": "geo",
    "IPv4": "ip",
    "IP": "ip",
    "INTERVAL": "|-|",
    "RECORD": "{}",
    "CURSOR": "cur",
    "VARIANT": "?",
    "UNKNOWN": "?",
}

# PostgreSQL wire OIDs → short display labels. The 0.3.x set is intact.
OID_TYPE_LABELS: dict[int, str] = {
    16: "t/f",  # bool
    21: "#",  # int2
    23: "##",  # int4
    20: "##",  # int8
    700: "#.#",  # float4
    701: "#.#",  # float8
    1700: "#.#",  # numeric
    25: "s",  # text
    1043: "s",  # varchar
    18: "s",  # char
    1082: "dt",  # date
    1114: "ts",  # timestamp
    1184: "tstz",  # timestamptz
    2950: "uid",  # uuid
    17: "bin",  # bytea
    114: "{}",  # json
    3802: "{}",  # jsonb
}


# Lookup is case-insensitive. The published key stays "IPv4"; "IPv4".upper()
# is "IPV4", so a direct uppercased dict get would miss that 0.3.x label.
_NATIVE_LOOKUP = {key.upper(): label for key, label in QUESTDB_TYPE_LABELS.items()}


def short_native_type(native: str) -> str:
    base = native.split("(", 1)[0].strip()
    return _NATIVE_LOOKUP.get(base.upper(), "?")


def short_oid_type(oid: int) -> str:
    return OID_TYPE_LABELS.get(oid, "?")


def column_type_label(native: str, *, designated: bool) -> str:
    short = short_native_type(native)
    if designated:
        return f"{short}★"
    return short


def relation_type_label(kind_code: str, partition_by: str | None) -> str:
    if partition_by and partition_by.upper() != "NONE":
        return f"{kind_code}·{partition_by}"
    return kind_code
