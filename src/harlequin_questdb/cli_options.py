from __future__ import annotations

from harlequin.options import HarlequinAdapterOption, TextOption

host = TextOption(
    name="host",
    description="The QuestDB host name or IP address.",
    short_decls=["-h"],
    default="localhost",
)
port = TextOption(
    name="port",
    description="The port for QuestDB's PostgreSQL wire protocol.",
    short_decls=["-p"],
    default="8812",
)
username = TextOption(
    name="username",
    description="The QuestDB username.",
    short_decls=["-u"],
    default="admin",
)
password = TextOption(
    name="password",
    description="The QuestDB password. Omitted values use quest.",
    default="quest",
)
dbname = TextOption(
    name="dbname",
    description=(
        "Libpq database field. QuestDB ignores logical database names; "
        "qdb is the usual placeholder."
    ),
    short_decls=["-d"],
    default="qdb",
)
connect_timeout = TextOption(
    name="connect-timeout",
    description="Seconds before connect fails.",
)
sslmode = TextOption(
    name="sslmode",
    description=(
        "PGWire SSL mode. The runtime default is disable when no connection "
        "string is given. Local QuestDB usually has SSL off."
    ),
    default="disable",
)

QUESTDB_OPTIONS: list[HarlequinAdapterOption] = [
    host,
    port,
    username,
    password,
    dbname,
    connect_timeout,
    sslmode,
]
