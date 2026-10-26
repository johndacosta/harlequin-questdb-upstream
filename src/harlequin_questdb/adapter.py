from __future__ import annotations

import logging
import socket
from typing import Any, Protocol, Sequence

from harlequin import (
    HarlequinAdapter,
    HarlequinCompletion,
    HarlequinConnection,
    HarlequinCursor,
)
from harlequin.catalog import Catalog
from harlequin.exception import HarlequinConnectionError, HarlequinQueryError
from psycopg import Connection, OperationalError
from psycopg.errors import QueryCanceled
from psycopg_pool import ConnectionPool

from harlequin_questdb.catalog import DatabaseCatalogItem
from harlequin_questdb.cli_options import QUESTDB_OPTIONS
from harlequin_questdb.completions import FUNCTIONS_SQL, base_questdb_completions
from harlequin_questdb.connect import (
    ConnectConfig,
    in_flight_dial_seconds,
    recoverable_connection_error,
    redact_password,
    resolve_connect_config,
)
from harlequin_questdb.labels import short_native_type, short_oid_type
from harlequin_questdb.sql import (
    RELATION_SQL_LEGACY,
    RELATION_SQL_MATVIEW,
    table_columns_sql,
)

logger = logging.getLogger(__name__)


class PoolLike(Protocol):
    def getconn(self) -> Any: ...

    def putconn(self, conn: Any) -> None: ...

    def close(self) -> None: ...


def execute_sql(cur: Any, sql: str) -> None:
    """Run one statement with the simple query protocol.

    ``prepare=False`` matches the 0.3.x adapter. QuestDB PGWire is driven with
    simple queries so result values stay in text and prepared statements stay off.
    """
    cur.execute(sql, prepare=False)


def _configure(conn: Connection[Any]) -> None:
    conn.autocommit = True


# A half-open socket reports closed=False until TCP gives up. Bound the
# checkout probe so catalog and reconnect do not sit on keepalive timers.
CHECK_SOCKET_TIMEOUT = 5.0

# gather() joins each worker in series. One worker means a failed open waits
# out one dial, then the worker reads StopWorker.
_POOL_CLOSE_SLACK = 1.0


def _close_pool(pool: Any, timeout: float) -> None:
    """Stop pool threads. ``timeout`` covers one in-flight libpq connect.

    Injected test pools implement ``close()`` with no timeout argument.
    """
    try:
        pool.close(timeout)
    except TypeError:
        pool.close()


def _check(conn: Connection[Any]) -> None:
    """Probe a pooled connection before it is handed out.

    ``PGconn.socket`` is the libpq file descriptor, an ``int``, not a Python
    socket. ``TCP_USER_TIMEOUT`` bounds an unacknowledged ``select 1`` so a
    half-open connection fails this probe instead of sitting on keepalive
    timers. The descriptor stays open for libpq.
    """
    if conn.closed:
        raise OperationalError("pooled QuestDB connection is closed")
    fd = _connection_fd(conn)
    previous = _set_tcp_user_timeout(fd, int(CHECK_SOCKET_TIMEOUT * 1000))
    try:
        with conn.cursor() as cur:
            execute_sql(cur, "select 1")
    finally:
        if previous is not None:
            _set_tcp_user_timeout(fd, previous)


def _connection_fd(conn: Any) -> int | None:
    """Return the libpq socket fd. A socket object is used via its fileno."""
    pgconn = getattr(conn, "pgconn", None)
    if pgconn is None:
        return None
    sock = pgconn.socket
    if isinstance(sock, int):
        return sock if sock >= 0 else None
    fileno = getattr(sock, "fileno", None)
    if not callable(fileno):
        return None
    fd = fileno()
    if isinstance(fd, int) and fd >= 0:
        return fd
    return None


def _set_tcp_user_timeout(fd: int | None, milliseconds: int) -> int | None:
    """Set ``TCP_USER_TIMEOUT`` and return the previous value.

    A socket object built from ``fd`` would close libpq's descriptor on
    garbage collection. ``detach()`` drops that ownership. ``None`` means the
    option was not changed.
    """
    option = getattr(socket, "TCP_USER_TIMEOUT", None)
    if fd is None or option is None:
        return None
    try:
        borrowed = socket.socket(fileno=fd)
    except OSError:
        logger.debug("QuestDB checkout could not borrow the libpq socket")
        return None
    try:
        previous = borrowed.getsockopt(socket.IPPROTO_TCP, option)
        borrowed.setsockopt(socket.IPPROTO_TCP, option, milliseconds)
        return int(previous)
    except OSError:
        logger.debug("QuestDB checkout could not set TCP_USER_TIMEOUT")
        return None
    finally:
        borrowed.detach()


class QuestDBCursor(HarlequinCursor):
    def __init__(self, connection: QuestDBConnection, cur: Any) -> None:
        self.connection = connection
        self._cur = cur
        description = cur.description
        self._description = list(description) if description is not None else []
        self._limit: int | None = None

    def columns(self) -> list[tuple[str, str]]:
        return [
            (col.name, short_oid_type(col.type_code))
            for col in self._description
        ]

    def set_limit(self, limit: int) -> QuestDBCursor:
        self._limit = limit
        return self

    def fetchall(self) -> list[tuple[Any, ...]] | None:
        try:
            if self._limit is None:
                rows: list[tuple[Any, ...]] | None = self._cur.fetchall()
            else:
                rows = self._cur.fetchmany(self._limit)
            return rows
        except QueryCanceled:
            return None
        except Exception as exc:
            raise HarlequinQueryError(
                msg=_public_error(exc, self.connection),
                title="QuestDB raised an error while fetching results.",
            ) from exc
        finally:
            self._cur.close()


class QuestDBConnection(HarlequinConnection):
    """QuestDB over PGWire. Metadata comes from tables() and table_columns()."""

    def __init__(
        self,
        config: ConnectConfig,
        *,
        pool: PoolLike | None = None,
    ) -> None:
        self.config = config
        params = config.resolved_params()
        host = params.get("host", "localhost")
        port = params.get("port", "8812")
        self.init_message = f"Connected to QuestDB at {host}:{port}."
        self._relation_sql = RELATION_SQL_MATVIEW
        self._relation_columns_include_designated = True
        self.pool: PoolLike
        self._main_conn: Any
        if pool is None:
            opened: ConnectionPool[Any] | None = None
            try:
                opened = ConnectionPool(
                    conninfo=config.conninfo,
                    min_size=1,
                    max_size=5,
                    kwargs=dict(config.pool_kwargs),
                    configure=_configure,
                    check=_check,
                    open=True,
                    timeout=config.pool_timeout,
                    max_idle=86400.0,
                    max_lifetime=float(86400 * 7),
                    reconnect_timeout=120.0,
                    num_workers=1,
                )
                self.pool = opened
                self._main_conn = opened.getconn()
            except Exception as exc:
                if opened is not None:
                    try:
                        _close_pool(
                            opened,
                            in_flight_dial_seconds(config) + _POOL_CLOSE_SLACK,
                        )
                    except Exception:
                        logger.debug("QuestDB pool close failed after connect error")
                raise HarlequinConnectionError(
                    msg=_public_error(exc, config),
                    title="QuestDB adapter could not connect.",
                ) from exc
        else:
            self.pool = pool
            self._main_conn = pool.getconn()
        self._main_conn.autocommit = True

    def _reconnect_main(self) -> None:
        old = self._main_conn
        try:
            self.pool.putconn(old)
        except Exception:
            close = getattr(old, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    logger.debug(
                        "QuestDB main connection close failed during reconnect"
                    )
        self._main_conn = self.pool.getconn()
        self._main_conn.autocommit = True

    def _borrow_worker(self) -> Any:
        worker = self.pool.getconn()
        worker.autocommit = True
        return worker

    def _return_worker(self, worker: Any) -> None:
        try:
            self.pool.putconn(worker)
        except Exception:
            close = getattr(worker, "close", None)
            if close is not None:
                close()

    def execute(self, query: str) -> QuestDBCursor | None:
        for attempt in range(2):
            cur: Any | None = None
            try:
                if getattr(self._main_conn, "closed", False):
                    self._reconnect_main()
                cur = self._main_conn.cursor()
                execute_sql(cur, query)
            except QueryCanceled:
                if cur is not None:
                    cur.close()
                return None
            except Exception as exc:
                if cur is not None:
                    cur.close()
                dead = bool(getattr(self._main_conn, "closed", False))
                if attempt == 0 and (dead or recoverable_connection_error(exc)):
                    logger.debug("QuestDB reconnect after %s", type(exc).__name__)
                    self._reconnect_main()
                    continue
                raise HarlequinQueryError(
                    msg=_public_error(exc, self),
                    title="QuestDB raised an error on this query.",
                ) from exc
            else:
                if cur is not None and cur.description is not None:
                    return QuestDBCursor(self, cur)
                if cur is not None:
                    cur.close()
                return None
        return None

    def cancel(self) -> None:
        try:
            self._main_conn.cancel_safe()
        except Exception:
            logger.debug(
                "QuestDB cancel_safe failed; reconnecting the editor connection"
            )
            try:
                self._reconnect_main()
            except Exception:
                logger.debug("QuestDB reconnect after cancel failed")

    def get_catalog(self) -> Catalog:
        label = self._logical_database_label()
        return Catalog(items=[DatabaseCatalogItem.from_label(label, self)])

    def get_completions(self) -> list[HarlequinCompletion]:
        completions = base_questdb_completions()
        worker = self._borrow_worker()
        rows: list[Any] = []
        try:
            with worker.cursor() as cur:
                execute_sql(cur, FUNCTIONS_SQL)
                rows = list(cur.fetchall())
        except Exception:
            logger.debug(
                "QuestDB functions() introspection failed; using static completions"
            )
            rows = []
        finally:
            self._return_worker(worker)
        completions.extend(
            HarlequinCompletion(
                label=str(row[0]),
                type_label="fn",
                value=str(row[0]),
                priority=1000,
                context=None,
            )
            for row in rows
            if row and row[0]
        )
        return sorted(completions)

    def close(self) -> None:
        try:
            self.pool.putconn(self._main_conn)
        except Exception:
            close = getattr(self._main_conn, "close", None)
            if close is not None:
                close()
        _close_pool(
            self.pool, in_flight_dial_seconds(self.config) + _POOL_CLOSE_SLACK
        )

    def _logical_database_label(self) -> str:
        worker = self._borrow_worker()
        try:
            with worker.cursor() as cur:
                execute_sql(cur, "select current_database()")
                row = cur.fetchone()
                if row and isinstance(row[0], str):
                    return row[0]
        except Exception:
            logger.debug("QuestDB current_database() failed; using the configured name")
        finally:
            self._return_worker(worker)
        return self.config.logical_database

    def _list_schemas(self) -> list[str]:
        worker = self._borrow_worker()
        try:
            with worker.cursor() as cur:
                execute_sql(cur, "select current_schema()")
                row = cur.fetchone()
                if row and isinstance(row[0], str):
                    return [row[0]]
        except Exception:
            logger.debug("QuestDB current_schema() failed; using public")
        finally:
            self._return_worker(worker)
        return ["public"]

    def _fetch_rows(self, worker: Any, sql: str) -> list[Any]:
        with worker.cursor() as cur:
            execute_sql(cur, sql)
            return list(cur.fetchall())

    def _list_relations(self) -> list[tuple[str, str, str | None, str | None]]:
        worker = self._borrow_worker()
        try:
            try:
                rows = self._fetch_rows(worker, self._relation_sql)
            except Exception as exc:
                # A dead session is not evidence that matView is missing.
                if (
                    recoverable_connection_error(exc)
                    or self._relation_sql == RELATION_SQL_LEGACY
                    or not _metadata_shape_mismatch(exc)
                ):
                    raise HarlequinQueryError(
                        msg=_public_error(exc, self),
                        title="QuestDB raised an error loading relations.",
                    ) from exc
                self._relation_sql = RELATION_SQL_LEGACY
                try:
                    rows = self._fetch_rows(worker, self._relation_sql)
                except Exception as fallback_exc:
                    raise HarlequinQueryError(
                        msg=_public_error(fallback_exc, self),
                        title="QuestDB raised an error loading relations.",
                    ) from fallback_exc
            return [
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]) if row[2] is not None else None,
                    str(row[3]) if row[3] is not None else None,
                )
                for row in rows
            ]
        finally:
            self._return_worker(worker)

    def _get_relation_columns(self, relation: str) -> list[tuple[str, str, bool]]:
        worker = self._borrow_worker()
        try:
            if self._relation_columns_include_designated:
                try:
                    rows = self._fetch_rows(
                        worker,
                        table_columns_sql(relation, include_designated=True),
                    )
                except Exception as exc:
                    recoverable = recoverable_connection_error(exc)
                    mismatch = _metadata_shape_mismatch(exc)
                    if recoverable or not mismatch:
                        raise HarlequinQueryError(
                            msg=_public_error(exc, self),
                            title="QuestDB raised an error loading columns.",
                        ) from exc
                    self._relation_columns_include_designated = False
                    try:
                        rows = self._fetch_rows(
                            worker,
                            table_columns_sql(relation, include_designated=False),
                        )
                    except Exception as fallback_exc:
                        raise HarlequinQueryError(
                            msg=_public_error(fallback_exc, self),
                            title="QuestDB raised an error loading columns.",
                        ) from fallback_exc
                    return [(str(row[0]), str(row[1]), False) for row in rows]
                return [
                    (str(row[0]), str(row[1]), _quest_bool(row[2])) for row in rows
                ]
            rows = self._fetch_rows(
                worker,
                table_columns_sql(relation, include_designated=False),
            )
            return [(str(row[0]), str(row[1]), False) for row in rows]
        except HarlequinQueryError:
            raise
        except Exception as exc:
            raise HarlequinQueryError(
                msg=_public_error(exc, self),
                title="QuestDB raised an error loading columns.",
            ) from exc
        finally:
            self._return_worker(worker)

    def short_questdb_type(self, native: str) -> str:
        return short_native_type(native)

    @classmethod
    def _short_column_type_from_oid(cls, oid: int) -> str:
        return short_oid_type(oid)


class QuestDBAdapter(HarlequinAdapter):
    ADAPTER_OPTIONS = QUESTDB_OPTIONS
    IMPLEMENTS_CANCEL = True
    ADAPTER_DETAILS = (
        "## QuestDB (PGWire)\n\n"
        "- Connects with psycopg on port **8812**. An omitted password is **quest**.\n"
        "- The CLI user option is `--username`. A connection string's host, user, "
        "and password are used as written.\n"
        "- Metadata comes from `tables()`, `table_columns()`, and `functions()`.\n"
        "- See `docs/USER_GUIDE.md` and `docs/KNOWN_LIMITATIONS.md`.\n"
    )

    def __init__(
        self,
        conn_str: Sequence[str],
        host: str | None = None,
        port: str | int | None = None,
        username: str | None = None,
        user: str | None = None,
        password: str | None = None,
        dbname: str | None = None,
        connect_timeout: str | int | float | None = None,
        sslmode: str | None = None,
        **_ignored: Any,
    ) -> None:
        self.conn_str = conn_str
        self.config = resolve_connect_config(
            conn_str,
            host=host,
            port=port,
            user=user,
            username=username,
            password=password,
            dbname=dbname,
            connect_timeout=connect_timeout,
            sslmode=sslmode,
        )

    @property
    def connection_id(self) -> str | None:
        identifier = self.config.connection_id()
        return identifier or None

    def connect(self) -> QuestDBConnection:
        return QuestDBConnection(self.config)


def _quest_bool(value: object) -> bool:
    """QuestDB booleans arrive as bools or as ``t`` / ``f`` text."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "t", "true", "y", "yes"}
    return False


def _metadata_shape_mismatch(exc: BaseException) -> bool:
    """True when ``tables()`` / ``table_columns()`` lacks a column we asked for."""
    message = str(exc).lower()
    return "does not exist" in message or "unknown function" in message


def _public_error(exc: BaseException, source: QuestDBConnection | ConnectConfig) -> str:
    config = source.config if isinstance(source, QuestDBConnection) else source
    password = config.pool_kwargs.get("password")
    if not password:
        password = config.resolved_params().get("password")
    return redact_password(str(exc), password, conninfo_text=config.conninfo)
