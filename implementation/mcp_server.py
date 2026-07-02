from __future__ import annotations

import json
import queue
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import anyio
import mcp.types as mcp_types
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.server.lowlevel.server import NotificationOptions
from mcp.shared.message import SessionMessage

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import DB_PATH, ensure_database
except ImportError:
    from db import SQLiteAdapter, ValidationError
    from init_db import DB_PATH, ensure_database


SERVER_NAME = "SQLite Lab MCP Server"

ensure_database(DB_PATH)
adapter = SQLiteAdapter(Path(DB_PATH))
mcp = FastMCP(SERVER_NAME)


def _tool_error(exc: ValidationError) -> ToolError:
    return ToolError(str(exc))


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | dict[str, Any] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a validated table with optional filters, ordering, and pagination."""
    try:
        return adapter.search(
            table=table,
            filters=filters,
            columns=columns,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except ValidationError as exc:
        raise _tool_error(exc) from exc


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a validated table and return the inserted payload."""
    try:
        return adapter.insert(table=table, values=values)
    except ValidationError as exc:
        raise _tool_error(exc) from exc


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | dict[str, Any] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Run count, avg, sum, min, or max over a validated table."""
    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except ValidationError as exc:
        raise _tool_error(exc) from exc


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full database schema as JSON text."""
    return json.dumps(adapter.get_database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""
    try:
        schema = {table_name: adapter.get_table_schema(table_name)}
    except ValidationError as exc:
        raise _tool_error(exc) from exc
    return json.dumps(schema, indent=2)


@asynccontextmanager
async def _threaded_stdio_server():
    """Stdio transport that avoids AnyIO stdin thread hangs in this lab environment."""
    read_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_reader = anyio.create_memory_object_stream(0)
    incoming: queue.Queue[SessionMessage | Exception | None] = queue.Queue()

    def read_stdin() -> None:
        try:
            for line in sys.stdin:
                try:
                    message = mcp_types.JSONRPCMessage.model_validate_json(line)
                    incoming.put(SessionMessage(message))
                except Exception as exc:
                    incoming.put(exc)
        finally:
            incoming.put(None)

    async def stdin_pump() -> None:
        async with read_writer:
            while True:
                try:
                    item = incoming.get_nowait()
                except queue.Empty:
                    await anyio.sleep(0.01)
                    continue
                if item is None:
                    break
                await read_writer.send(item)

    async def stdout_writer() -> None:
        async with write_reader:
            async for session_message in write_reader:
                payload = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                sys.stdout.write(payload + "\n")
                sys.stdout.flush()

    thread = threading.Thread(target=read_stdin, daemon=True)
    thread.start()
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(stdin_pump)
        task_group.start_soon(stdout_writer)
        yield read_stream, write_stream
        task_group.cancel_scope.cancel()


async def _run_stdio() -> None:
    from fastmcp.server.context import reset_transport, set_transport

    token = set_transport("stdio")
    try:
        async with mcp._lifespan_manager():
            async with _threaded_stdio_server() as (read_stream, write_stream):
                await mcp._mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp._mcp_server.create_initialization_options(
                        notification_options=NotificationOptions(tools_changed=True),
                    ),
                )
    finally:
        reset_transport(token)


if __name__ == "__main__":
    anyio.run(_run_stdio)
