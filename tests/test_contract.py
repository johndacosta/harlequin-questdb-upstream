from __future__ import annotations

import os
import socket
import threading
import time
from importlib.metadata import entry_points
from typing import Any

import pytest
from harlequin.adapter import HarlequinAdapter
from harlequin.exception import HarlequinConnectionError, HarlequinQueryError
from psycopg import OperationalError, conninfo

from harlequin_questdb import QuestDBAdapter
from harlequin_questdb.adapter import (
    CHECK_SOCKET_TIMEOUT,
    QuestDBConnection,
    _check,
    _configure,
    _set_tcp_user_timeout,
    execute_sql,
)
from harlequin_questdb.cli_options import QUESTDB_OPTIONS
from harlequin_questdb.connect import (
    in_flight_dial_seconds,
    redact_password,
    resolve_connect_config,
)
from harlequin_questdb.labels import short_native_type, short_oid_type


def _option(name: str) -> Any:
    return next(option for option in QUESTDB_OPTIONS if option.name == name)


def test_plugin_discovery() -> None:
    loaded = entry_points(group="harlequin.adapter")["questdb"].load()
    assert loaded is QuestDBAdapter
    assert loaded.__name__ == "QuestDBAdapter"
    assert issubclass(loaded, HarlequinAdapter)
    adapter = loaded(conn_str=())
    assert adapter.config.resolved_params()["password"] == "quest"


def test_omitted_password_is_quest() -> None:
    adapter = QuestDBAdapter(conn_str=())
    assert adapter.config.resolved_params()["password"] == "quest"
    assert _option("password").default == "quest"


def test_username_is_honored_and_user_alias_wins() -> None:
    via_username = QuestDBAdapter(conn_str=(), username="legacy_user")
    assert via_username.config.resolved_params()["user"] == "legacy_user"
    both = QuestDBAdapter(conn_str=(), user="cli_user", username="legacy_user")
    assert both.config.resolved_params()["user"] == "cli_user"
    assert _option("username").name == "username"
    assert _option("username").default == "admin"


def test_host_default_is_localhost_in_help_and_runtime() -> None:
    assert _option("host").default == "localhost"
    adapter = QuestDBAdapter(conn_str=())
    assert adapter.config.resolved_params()["host"] == "localhost"


def test_connection_string_is_not_overwritten_by_defaults() -> None:
    adapter = QuestDBAdapter(
        conn_str=("host=prod user=alice password=secret dbname=qdb",),
        host="localhost",
        username="admin",
        password="quest",
        dbname="other",
        sslmode="require",
    )
    params = adapter.config.resolved_params()
    assert params["host"] == "prod"
    assert params["user"] == "alice"
    assert params["password"] == "secret"
    assert params["dbname"] == "qdb"
    for key in ("host", "port", "user", "password", "dbname", "sslmode"):
        assert key not in adapter.config.pool_kwargs
    parsed = conninfo.conninfo_to_dict(adapter.connection_id or "")
    assert parsed["user"] == "alice"
    assert parsed["host"] == "prod"
    assert "password" not in parsed
    assert "secret" not in (adapter.connection_id or "")


def test_string_connect_timeout_bounds_pool_wait() -> None:
    named = QuestDBAdapter(conn_str=("host=prod connect_timeout=2",))
    assert named.config.pool_timeout == 2.0
    assert "connect_timeout" not in named.config.pool_kwargs
    missing = QuestDBAdapter(conn_str=("host=prod",))
    assert missing.config.pool_timeout == 30.0
    assert missing.config.pool_kwargs["connect_timeout"] == "30"


def test_in_flight_dial_follows_the_string_when_the_pool_wait_is_shorter() -> None:
    config = resolve_connect_config(
        ("host=127.0.0.1 port=1 connect_timeout=8",),
        connect_timeout=1,
    )
    assert config.pool_timeout == 1.0
    assert "connect_timeout" not in config.pool_kwargs
    assert in_flight_dial_seconds(config) == 8.0


def test_in_flight_dial_is_at_least_two_seconds() -> None:
    config = resolve_connect_config((), connect_timeout=1)
    assert config.pool_kwargs["connect_timeout"] == "1"
    assert in_flight_dial_seconds(config) == 2.0


def test_failed_connect_reaps_pool_workers() -> None:
    """A blackhole dial longer than close()'s 5s default must not leave threads."""
    before = {thread.ident for thread in threading.enumerate()}
    started = time.monotonic()
    with pytest.raises(HarlequinConnectionError):
        QuestDBAdapter(
            conn_str=("host=127.0.0.1 port=1 connect_timeout=8",),
            connect_timeout=1,
        ).connect()
    elapsed = time.monotonic() - started
    leaked = [
        thread.name
        for thread in threading.enumerate()
        if thread.ident not in before and thread.is_alive() and "pool-" in thread.name
    ]
    assert leaked == []
    assert elapsed < 20.0


def test_check_runs_select_1_on_libpq_socket_fd() -> None:
    """PGconn.socket is an int fd. The probe must not call gettimeout() on it."""
    option = getattr(socket, "TCP_USER_TIMEOUT", None)
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.bind(("127.0.0.1", 0))
    fd = raw.fileno()
    assert isinstance(fd, int)
    before = (
        raw.getsockopt(socket.IPPROTO_TCP, option)
        if option is not None
        else None
    )
    seen: dict[str, Any] = {}

    class Cursor:
        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            seen["sql"] = sql
            seen["prepare"] = prepare
            if option is not None:
                seen["during"] = raw.getsockopt(socket.IPPROTO_TCP, option)
            os.fstat(fd)

    class Conn:
        closed = False
        pgconn = type("PG", (), {"socket": fd})()

        def cursor(self) -> Cursor:
            return Cursor()

    conn = Conn()
    try:
        _check(conn)  # type: ignore[arg-type]
        os.fstat(fd)
    finally:
        after = (
            raw.getsockopt(socket.IPPROTO_TCP, option)
            if option is not None
            else None
        )
        raw.close()
    assert seen["sql"] == "select 1"
    assert seen["prepare"] is False
    if option is not None:
        assert seen["during"] == int(CHECK_SOCKET_TIMEOUT * 1000)
        assert after == before
    assert conn.closed is False


def test_check_on_platform_without_tcp_user_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-Linux platforms (macOS, Windows) lack TCP_USER_TIMEOUT; probe still works."""
    monkeypatch.delattr(socket, "TCP_USER_TIMEOUT", raising=False)
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.bind(("127.0.0.1", 0))
    fd = raw.fileno()
    seen: dict[str, Any] = {}

    class Cursor:
        def __enter__(self) -> Cursor:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            seen["sql"] = sql
            seen["prepare"] = prepare
            os.fstat(fd)

    class Conn:
        closed = False
        pgconn = type("PG", (), {"socket": fd})()

        def cursor(self) -> Cursor:
            return Cursor()

    conn = Conn()
    try:
        _check(conn)  # type: ignore[arg-type]
        os.fstat(fd)
    finally:
        raw.close()
    assert seen["sql"] == "select 1"
    assert seen["prepare"] is False
    assert conn.closed is False


def test_set_tcp_user_timeout_platform_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _set_tcp_user_timeout(None, 5000) is None
    monkeypatch.delattr(socket, "TCP_USER_TIMEOUT", raising=False)
    assert _set_tcp_user_timeout(1, 5000) is None
    assert _set_tcp_user_timeout(-1, 5000) is None


def test_keepalive_in_conninfo_is_kept() -> None:
    raw = "host=prod user=alice password=secret keepalives_idle=5"
    adapter = QuestDBAdapter(conn_str=(raw,))
    assert adapter.config.resolved_params()["keepalives_idle"] == "5"
    assert "keepalives_idle" not in adapter.config.pool_kwargs
    assert adapter.config.pool_kwargs["keepalives"] == "1"


def test_connection_id_from_options_includes_user_and_omits_password() -> None:
    adapter = QuestDBAdapter(conn_str=(), username="legacy_user")
    parsed = conninfo.conninfo_to_dict(adapter.connection_id or "")
    assert parsed["user"] == "legacy_user"
    assert parsed["host"] == "localhost"
    assert "password" not in parsed


def test_too_many_connection_strings() -> None:
    with pytest.raises(HarlequinConnectionError):
        QuestDBAdapter(conn_str=("host=a", "host=b"))


def test_extra_kwargs_are_ignored() -> None:
    adapter = QuestDBAdapter(conn_str=(), foo=1, bar="baz")
    assert adapter.config.resolved_params()["password"] == "quest"


def test_repr_hides_password() -> None:
    from_options = QuestDBAdapter(conn_str=())
    assert "quest" not in repr(from_options.config)
    from_string = QuestDBAdapter(conn_str=("host=prod password=secret",))
    assert "secret" not in repr(from_string.config)


def test_repr_hides_uri_spaced_and_escaped_passwords() -> None:
    cases = (
        ("postgresql://admin:s3cret@db.example:8812/qdb", "s3cret", "s3cret"),
        ("postgresql://admin:p%40ss@h/db", "p@ss", "p%40ss"),
        ("host=prod password = s3cret", "s3cret", "s3cret"),
        ("host=prod password='s\\'ecret'", "s'ecret", "s\\'ecret"),
    )
    for raw, secret, visible in cases:
        adapter = QuestDBAdapter(conn_str=(raw,))
        assert adapter.config.resolved_params()["password"] == secret
        rendered = repr(adapter.config)
        assert secret not in rendered
        assert visible not in rendered
        echoed = redact_password(f"driver said {raw}", secret, conninfo_text=raw)
        assert secret not in echoed
        assert visible not in echoed
        assert raw not in echoed


def test_connection_id_omits_sslpassword() -> None:
    raw = "host=prod user=alice password=secret sslpassword=keysecret"
    adapter = QuestDBAdapter(conn_str=(raw,))
    identifier = adapter.connection_id or ""
    assert "keysecret" not in identifier
    assert "secret" not in identifier
    assert conninfo.conninfo_to_dict(identifier)["user"] == "alice"


def test_redact_password_token_only() -> None:
    assert redact_password("failed password=secret here", "secret") == (
        "failed password=*** here"
    )
    assert redact_password("request", "quest") == "request"


def test_connect_passes_string_and_not_identity_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakePool:
        def __init__(
            self,
            conninfo: str = "",
            kwargs: dict[str, str] | None = None,
            **rest: Any,
        ) -> None:
            captured["conninfo"] = conninfo
            captured["kwargs"] = dict(kwargs or {})
            captured["min_size"] = rest.get("min_size")
            captured["max_size"] = rest.get("max_size")
            captured["configure"] = rest.get("configure")
            captured["check"] = rest.get("check")

        def getconn(self) -> Any:
            connection = type("Conn", (), {"autocommit": False, "closed": False})()
            return connection

        def putconn(self, conn: Any) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("harlequin_questdb.adapter.ConnectionPool", FakePool)
    raw = "host=prod user=alice password=secret dbname=qdb"
    adapter = QuestDBAdapter(conn_str=(raw,), password="quest", host="localhost")
    adapter.connect()
    assert captured["conninfo"] == raw
    assert "password" not in captured["kwargs"]
    assert "host" not in captured["kwargs"]
    assert "user" not in captured["kwargs"]
    assert captured["min_size"] == 1
    assert captured["max_size"] == 5
    assert captured["configure"] is _configure
    assert captured["check"] is _check
    assert captured["kwargs"]["keepalives"] == "1"


def test_connect_passes_option_defaults_when_there_is_no_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakePool:
        def __init__(
            self,
            conninfo: str = "",
            kwargs: dict[str, str] | None = None,
            **rest: Any,
        ) -> None:
            captured["conninfo"] = conninfo
            captured["kwargs"] = dict(kwargs or {})
            captured["rest"] = rest

        def getconn(self) -> Any:
            return type("Conn", (), {"autocommit": False, "closed": False})()

        def putconn(self, conn: Any) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("harlequin_questdb.adapter.ConnectionPool", FakePool)
    QuestDBAdapter(conn_str=()).connect()
    assert captured["conninfo"] == ""
    assert captured["kwargs"]["host"] == "localhost"
    assert captured["kwargs"]["user"] == "admin"
    assert captured["kwargs"]["password"] == "quest"
    assert captured["kwargs"]["dbname"] == "qdb"
    assert captured["kwargs"]["sslmode"] == "disable"
    assert captured["kwargs"]["keepalives_idle"] == "30"
    assert captured["rest"]["max_size"] == 5
    assert captured["rest"]["min_size"] == 1
    assert captured["rest"]["num_workers"] == 1


def test_execute_sql_does_not_prepare() -> None:
    seen: dict[str, Any] = {}

    class Cursor:
        def execute(self, sql: str, prepare: bool | None = None) -> None:
            seen["sql"] = sql
            seen["prepare"] = prepare

    execute_sql(Cursor(), "select 1")
    assert seen["sql"] == "select 1"
    assert seen["prepare"] is False


def test_execute_does_not_prepare_and_retries_once() -> None:
    calls: list[bool | None] = []

    class Cursor:
        description = None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            calls.append(prepare)
            if len(calls) == 1:
                raise OperationalError("connection lost")

        def close(self) -> None:
            return None

    class Main:
        closed = False
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def __init__(self) -> None:
            self.main = Main()

        def getconn(self) -> Main:
            return self.main

        def putconn(self, conn: Main) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    assert connection.execute("select 1") is None
    assert calls == [False, False]


def test_unrelated_connection_words_are_not_retried() -> None:
    calls = {"n": 0}

    class Cursor:
        description = None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            calls["n"] += 1
            raise OperationalError("syntax error near connection closed")

        def close(self) -> None:
            return None

    class Main:
        closed = False
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Main:
            return Main()

        def putconn(self, conn: Main) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    with pytest.raises(HarlequinQueryError):
        connection.execute("insert into logs values ('connection closed')")
    assert calls["n"] == 1


def test_operational_error_without_a_dead_session_is_not_retried() -> None:
    calls = {"n": 0}

    class Cursor:
        description = None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            calls["n"] += 1
            raise OperationalError("syntax error at selec")

        def close(self) -> None:
            return None

    class Main:
        closed = False
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Main:
            return Main()

        def putconn(self, conn: Main) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    with pytest.raises(HarlequinQueryError):
        connection.execute("selec;")
    assert calls["n"] == 1


def test_query_error_is_not_retried() -> None:
    calls = {"n": 0}

    class Cursor:
        description = None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            calls["n"] += 1
            raise Exception("syntax error at selec")

        def close(self) -> None:
            return None

    class Main:
        closed = False
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def getconn(self) -> Main:
            return Main()

        def putconn(self, conn: Main) -> None:
            return None

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    with pytest.raises(HarlequinQueryError):
        connection.execute("selec;")
    assert calls["n"] == 1


def test_closed_connection_reconnects_before_execute() -> None:
    executed = {"n": 0}

    class Cursor:
        description = None

        def execute(self, sql: str, prepare: bool | None = None) -> None:
            executed["n"] += 1

        def close(self) -> None:
            return None

    class Main:
        def __init__(self, closed: bool) -> None:
            self.closed = closed
            self.autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

    class Pool:
        def __init__(self) -> None:
            self.handed = 0

        def getconn(self) -> Main:
            self.handed += 1
            return Main(closed=self.handed == 1)

        def putconn(self, conn: Main) -> None:
            return None

        def close(self) -> None:
            return None

    pool = Pool()
    connection = QuestDBConnection(resolve_connect_config(()), pool=pool)
    assert connection._main_conn.closed is True
    assert connection.execute("select 1") is None
    assert executed["n"] == 1
    assert connection._main_conn.closed is False


def test_cancel_uses_cancel_safe_and_reconnects_when_it_fails() -> None:
    events: list[str] = []

    class Main:
        def __init__(self, fail_cancel: bool) -> None:
            self.fail_cancel = fail_cancel
            self.closed = False
            self.autocommit = False

        def cancel_safe(self) -> None:
            events.append("cancel")
            if self.fail_cancel:
                raise OperationalError("cancel failed")

    class Pool:
        def __init__(self) -> None:
            self.n = 0

        def getconn(self) -> Main:
            self.n += 1
            return Main(fail_cancel=self.n == 1)

        def putconn(self, conn: Main) -> None:
            events.append("putconn")

        def close(self) -> None:
            return None

    connection = QuestDBConnection(resolve_connect_config(()), pool=Pool())
    connection.cancel()
    assert events == ["cancel", "putconn"]
    assert connection._main_conn.fail_cancel is False


def test_published_type_labels_are_unchanged() -> None:
    assert short_native_type("INT") == "##"
    assert short_native_type("DATE") == "dt"
    assert short_native_type("BYTE") == "#"
    assert short_native_type("BINARY") == "bin"
    assert short_native_type("LONG256") == "##"
    assert short_native_type("IPv4") == "ip"
    assert short_native_type("TIMESTAMP") == "ts"
    assert short_oid_type(23) == "##"
    assert short_oid_type(1184) == "tstz"
    assert short_oid_type(20) == "##"
    assert short_oid_type(16) == "t/f"
    assert short_oid_type(1700) == "#.#"
    assert QuestDBConnection._short_column_type_from_oid(23) == "##"
