# Lab: FastMCP SQLite Database Server

This repository contains a working MCP server built with FastMCP and SQLite. It exposes three tools:

- `search`
- `insert`
- `aggregate`

It also exposes database schema context through MCP resources:

- `schema://database`
- `schema://table/{table_name}`

## Project Structure

```text
implementation/
  db.py                 # SQLite adapter, validation, SQL execution
  init_db.py            # reproducible schema and seed data
  mcp_server.py         # FastMCP tools and resources
  verify_server.py      # repeatable MCP smoke verification
  start_inspector.sh    # MCP Inspector launcher
  tests/
    test_db.py          # adapter and validation tests
pseudocode/             # original lab scaffold
Rubric.md
Tips.md
```

## Setup

Use Python 3.11 or newer.

```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Create a fresh SQLite database:

```bash
python implementation/init_db.py
```

Run tests:

```bash
pytest
```

Run the MCP smoke verification:

```bash
python implementation/verify_server.py
```

Start the MCP server over stdio:

```bash
python implementation/mcp_server.py
```

## Data Model

The lab database contains:

- `students`: student profile, email, cohort, and status
- `courses`: course code, title, and credits
- `enrollments`: student/course relationship with score

Seed data includes multiple cohorts and scores so searches and aggregates are easy to demonstrate.

## Tool Reference

### `search`

Search a validated table with optional filters, selected columns, ordering, limit, and offset.

Example:

```json
{
  "table": "students",
  "filters": {"cohort": "A1"},
  "columns": ["id", "name", "cohort"],
  "limit": 5,
  "order_by": "name"
}
```

Supported filter operators:

- `=`
- `==`
- `!=`
- `>`
- `>=`
- `<`
- `<=`
- `like`
- `in`

### `insert`

Insert one row and return the inserted payload.

Example:

```json
{
  "table": "students",
  "values": {
    "name": "Lan Hoang",
    "email": "lan.hoang@example.edu",
    "cohort": "A3",
    "status": "active"
  }
}
```

### `aggregate`

Run aggregate metrics over a validated table.

Supported metrics:

- `count`
- `avg`
- `sum`
- `min`
- `max`

Example:

```json
{
  "table": "enrollments",
  "metric": "avg",
  "column": "score"
}
```

Grouped example:

```json
{
  "table": "students",
  "metric": "count",
  "group_by": "cohort"
}
```

## Safety Behavior

The implementation rejects:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate metrics
- `avg` or `sum` on non-numeric columns
- empty inserts
- invalid pagination values

Values are passed through SQLite parameters. SQL identifiers are accepted only after being validated against the live database schema.

## MCP Resources

Read the full schema:

```text
schema://database
```

Read one table schema:

```text
schema://table/students
```

## MCP Inspector Demo

Launch Inspector:

```bash
chmod +x implementation/start_inspector.sh
./implementation/start_inspector.sh
```

In Inspector, verify:

- tools list includes `search`, `insert`, `aggregate`
- resources include `schema://database`
- resource templates include `schema://table/{table_name}`
- `search` with cohort `A1` returns rows
- `insert` creates a new student
- `aggregate` can count students by cohort
- invalid `search` on `missing_table` returns a clear error

## Codex Client Demo

Codex supports MCP servers through `config.toml`. A local stdio server can be configured globally in `~/.codex/config.toml` or per trusted project in `.codex/config.toml`.

Example project-scoped config:

```toml
[mcp_servers.sqlite_lab]
command = "/ABSOLUTE/PATH/TO/THIS/REPO/.venv/bin/python"
args = ["/ABSOLUTE/PATH/TO/THIS/REPO/implementation/mcp_server.py"]
cwd = "/ABSOLUTE/PATH/TO/THIS/REPO"
startup_timeout_sec = 10
tool_timeout_sec = 60
```

For this checkout, replace the paths with:

```toml
[mcp_servers.sqlite_lab]
command = "/home/n91ym1nhky/Courses/AI20K/D26_0702_T3_MCP_Tool_Integration/.venv/bin/python"
args = ["/home/n91ym1nhky/Courses/AI20K/D26_0702_T3_MCP_Tool_Integration/implementation/mcp_server.py"]
cwd = "/home/n91ym1nhky/Courses/AI20K/D26_0702_T3_MCP_Tool_Integration"
startup_timeout_sec = 10
tool_timeout_sec = 60
```

After configuring Codex, open the Codex TUI and run:

```text
/mcp
```

Then ask Codex:

```text
Use the sqlite_lab MCP server to search the top 2 students in cohort A1 by name, read schema://database, and show one invalid search against missing_table.
```

## Suggested 2-Minute Demo Flow

1. Run `python implementation/init_db.py`.
2. Run `pytest`.
3. Run `python implementation/verify_server.py`.
4. Open MCP Inspector and show the three tools.
5. Read `schema://database`.
6. Call `search` for students in cohort `A1`.
7. Call `insert` for a new student.
8. Call `aggregate` with `count` grouped by `cohort`.
9. Show invalid `search` with `table = "missing_table"`.
10. Show Codex `/mcp` with `sqlite_lab` connected and ask it to use the server.

## References

- FastMCP quickstart: https://gofastmcp.com/v2/getting-started/quickstart
- FastMCP resources: https://gofastmcp.com/v2/servers/resources
- MCP Inspector: https://modelcontextprotocol.io/docs/tools/inspector
- Codex MCP configuration: https://developers.openai.com/codex/mcp
