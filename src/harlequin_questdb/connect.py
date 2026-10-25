"""Connection decisions that do not open a socket."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from harlequin.exception import HarlequinConnectionError
from psycopg import conninfo

DEFAULT_HOST = "localhost"
DEFAULT_PORT = "8812"
DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "quest"
DEFAULT_DBNAME = "qdb"
DEFAULT_SSLMODE = "disable"
DEFAULT_POOL_TIMEOUT = 30.0

# psycopg keyword arguments override the same keys inside a connection string.
# These keys are therefore filled only when the caller did not pass a string.
IDENTITY_KEYS = ("host", "port", "user", "password", "dbname", "sslmode")

KEEPALIVE_DEFAULTS: dict[str, str] = {
    "keepalives": "1",
    "keepalives_idle": "30",
    "keepalives_interval": "10",
    "keepalives_count": "6",
}

_CONNECTION_ID_OMIT = frozenset(
    {"password", *KEEPALIVE_DEFAULTS.keys(), "connect_timeout"}
)


@dataclass(frozen=True, repr=False)
class ConnectConfig:
    """What `ConnectionPool` will receive.

    `conninfo` is the raw connection string, or empty when options built the
    connection. `pool_kwargs` must not contain identity defaults when
    `conninfo` is non-empty.
    """

    conninfo: str
    pool_kwargs: dict[str, str]
    logical_database: str
    pool_timeout: float

    def resolved_params(self) -> dict[str, str]:
        """Parameters psycopg will use: string first, then kwargs overrides."""
        merged = conninfo.conninfo_to_dict(self.conninfo, **self.pool_kwargs)
        return {key: str(value) for key, value in merged.items()}

    def connection_id(self) -> str:
        params = self.resolved_params()
        for key in list(params):
            if key in _CONNECTION_ID_OMIT or "password" in key.lower():
                params.pop(key, None)
        if not params:
            return ""
        return str(conninfo.make_conninfo(**params))

    def __repr__(self) -> str:
        safe_kwargs = {
            key: ("***" if "password" in key.lower() else value)
            for key, value in self.pool_kwargs.items()
        }
        return (
            f"ConnectConfig(conninfo={redact_conninfo(self.conninfo)!r}, "
            f"pool_kwargs={safe_kwargs!r}, "
            f"logical_database={self.logical_database!r})"
        )


def resolve_connect_config(
    conn_str: Sequence[str],
    *,
    host: str | None = None,
    port: str | int | None = None,
    user: str | None = None,
    username: str | None = None,
    password: str | None = None,
    dbname: str | None = None,
    connect_timeout: str | int | float | None = None,
    sslmode: str | None = None,
) -> ConnectConfig:
    """Build pool inputs. Identity defaults apply only when `conn_str` is empty."""
    if len(conn_str) > 1:
        raise HarlequinConnectionError(
            msg=(
                "The QuestDB adapter accepts a single connection string; "
                f"received {len(conn_str)}."
            ),
            title="Too many connection strings for QuestDB.",
        )
    raw = conn_str[0].strip() if conn_str else ""
    timeout = _pool_timeout(connect_timeout)
    if raw:
        return _from_conninfo(
            raw, connect_timeout=connect_timeout, pool_timeout=timeout
        )
    effective_user = user if user is not None else username
    kwargs: dict[str, str] = {
        "host": host if host is not None else DEFAULT_HOST,
        "port": str(port) if port is not None else DEFAULT_PORT,
        "user": effective_user if effective_user is not None else DEFAULT_USER,
        "password": password if password is not None else DEFAULT_PASSWORD,
        "dbname": dbname if dbname is not None else DEFAULT_DBNAME,
        "sslmode": sslmode if sslmode is not None else DEFAULT_SSLMODE,
        **KEEPALIVE_DEFAULTS,
    }
    kwargs["connect_timeout"] = _libpq_timeout(
        float(connect_timeout) if connect_timeout is not None else timeout
    )
    return ConnectConfig(
        conninfo="",
        pool_kwargs=kwargs,
        logical_database=kwargs["dbname"],
        pool_timeout=timeout,
    )


def _from_conninfo(
    raw: str,
    *,
    connect_timeout: str | int | float | None,
    pool_timeout: float,
) -> ConnectConfig:
    try:
        parsed = conninfo.conninfo_to_dict(raw)
    except Exception as exc:
        raise HarlequinConnectionError(
            msg=redact_password(str(exc), _password_in_conninfo(raw)),
            title="QuestDB adapter could not read the connection string.",
        ) from exc
    kwargs: dict[str, str] = {}
    for key, value in KEEPALIVE_DEFAULTS.items():
        if key not in parsed:
            kwargs[key] = value
    string_timeout = parsed.get("connect_timeout")
    if connect_timeout is None and string_timeout is not None:
        pool_timeout = _pool_timeout(string_timeout)
    if "connect_timeout" not in parsed:
        kwargs["connect_timeout"] = _libpq_timeout(pool_timeout)
    logical = parsed.get("dbname") or DEFAULT_DBNAME
    return ConnectConfig(
        conninfo=raw,
        pool_kwargs=kwargs,
        logical_database=str(logical),
        pool_timeout=pool_timeout,
    )


def _libpq_timeout(seconds: float) -> str:
    """Libpq wants whole seconds. A zero would wait forever on some builds."""
    whole = int(seconds)
    if whole < 1:
        whole = 1
    return str(whole)


def _pool_timeout(connect_timeout: str | int | float | None) -> float:
    if connect_timeout is None:
        return DEFAULT_POOL_TIMEOUT
    try:
        return float(connect_timeout)
    except (TypeError, ValueError) as exc:
        raise HarlequinConnectionError(
            msg=str(exc),
            title="QuestDB adapter could not read connect_timeout.",
        ) from exc


def _password_in_conninfo(raw: str) -> str | None:
    if not raw:
        return None
    try:
        parsed: Mapping[str, Any] = conninfo.conninfo_to_dict(raw)
    except Exception:
        return None
    password = parsed.get("password")
    if password is None:
        return None
    return str(password)


def redact_conninfo(raw: str) -> str:
    """Rebuild a conninfo with password-bearing keys replaced.

    Parsing first covers URI userinfo, spaces around ``=``, and libpq
    backslash escapes. An unparseable string is dropped entirely.
    """
    if not raw:
        return raw
    try:
        parsed = dict(conninfo.conninfo_to_dict(raw))
    except Exception:
        return "***"
    secret = False
    for key, value in list(parsed.items()):
        if "password" in key.lower() and value not in (None, ""):
            parsed[key] = "***"
            secret = True
    if not secret:
        return raw
    rendered = conninfo.make_conninfo(
        **{key: str(value) for key, value in parsed.items()}
    )
    return str(rendered)


def redact_password(
    text: str,
    password: str | None,
    *,
    conninfo_text: str | None = None,
) -> str:
    """Hide a password echoed by the driver.

    The password is removed only as a conninfo token or URI userinfo, not as
    a bare substring, so ``quest`` inside ``request`` stays.
    """
    redacted = text
    if conninfo_text and conninfo_text in redacted:
        redacted = redacted.replace(conninfo_text, redact_conninfo(conninfo_text))
    if not password:
        return redacted
    escaped = re.escape(password)
    keyword = re.compile(
        "(?i)(password\\s*=\\s*)"
        f"(?:'{escaped}'|\"{escaped}\"|{escaped})"
        "(?![A-Za-z0-9_])"
    )
    redacted = keyword.sub(r"\1***", redacted)
    redacted = redacted.replace(f":{password}@", ":***@")
    encoded = quote(password, safe="")
    if encoded != password:
        redacted = redacted.replace(f":{encoded}@", ":***@")
    return redacted


# Phrases from libpq / psycopg when the TCP session is gone. A message that
# merely contains the separate words "connection" and "closed" is not enough:
# that would retry a failed statement whose text mentioned those words.
_DEAD_SESSION_PHRASES = (
    "server closed the connection",
    "connection already closed",
    "connection is closed",
    "connection was closed",
    "connection has been closed",
    "connection lost",
    "lost connection",
    "connection reset",
    "broken pipe",
    "consuming input failed",
    "ssl connection has been closed",
    "could not receive data from server",
    "could not send data to server",
    "no connection to the server",
)


def recoverable_connection_error(exc: BaseException) -> bool:
    """Errors that mean the TCP session is dead and one retry is worthwhile.

    A plain ``OperationalError`` is not enough. QuestDB can raise that class
    for a statement that did not run, and retrying it could run it twice.
    ``execute`` also retries when the connection object itself reports closed,
    which is the 0.3.0 idle-reconnect case.
    """
    if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
        return True
    message = str(exc).lower()
    return any(phrase in message for phrase in _DEAD_SESSION_PHRASES)
