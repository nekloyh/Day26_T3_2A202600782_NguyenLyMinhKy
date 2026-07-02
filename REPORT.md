# Bao cao Lab: Build a Database MCP Server with FastMCP and SQLite

**Ho ten:** Nguyễn Lý Minh Kỳ  
**MSSV:** 2A202600782  
**Lab:** MCP Tool Integration - FastMCP SQLite Database Server

## 1. Muc tieu

Lab nay yeu cau xay dung mot MCP server bang FastMCP, ket noi voi co so du lieu SQLite va expose cac chuc nang truy van du lieu thong qua MCP tools va MCP resources.

Nhung yeu cau chinh:

- Xay dung MCP server chay duoc.
- Tao SQLite database co schema va seed data reproducible.
- Implement 3 tools: `search`, `insert`, `aggregate`.
- Expose schema qua MCP resources.
- Validate input va xu ly loi an toan.
- Kiem thu bang MCP Inspector va Codex MCP client.
- Chuan bi README, screenshots va demo video.

## 2. Nhung phan da thuc hien

### 2.1. Cau truc project

Da tao thu muc implementation chinh:

```text
implementation/
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  start_inspector.sh
  tests/
    test_db.py
```

Ngoai ra, project co them:

```text
requirements.txt
pyproject.toml
.gitignore
screenshots/
README.md
```

### 2.2. SQLite database

Da xay dung database SQLite voi 3 bang:

- `students`
- `courses`
- `enrollments`

File `implementation/init_db.py` co nhiem vu:

- Tao moi database.
- Reset schema cu.
- Seed du lieu mau.
- Dam bao database co the tao lai bang mot command.

Command kiem tra:

```bash
python implementation/init_db.py
```

### 2.3. MCP Tools

Da implement du 3 MCP tools trong `implementation/mcp_server.py`.

#### `search`

Chuc nang:

- Tim kiem du lieu theo table.
- Ho tro filters.
- Ho tro chon columns.
- Ho tro ordering.
- Ho tro pagination bang `limit` va `offset`.

Vi du:

```json
{
  "table": "students",
  "filters": {"cohort": "A1"},
  "columns": ["id", "name", "cohort"],
  "limit": 5,
  "order_by": "name"
}
```

#### `insert`

Chuc nang:

- Insert mot record moi vao table hop le.
- Tra ve payload da insert, bao gom generated id.

Vi du:

```json
{
  "table": "students",
  "values": {
    "name": "Lan Hoang",
    "email": "lan.demo@example.edu",
    "cohort": "A3",
    "status": "active"
  }
}
```

#### `aggregate`

Chuc nang:

- Ho tro cac metric: `count`, `avg`, `sum`, `min`, `max`.
- Ho tro `group_by`.

Vi du:

```json
{
  "table": "students",
  "metric": "count",
  "group_by": "cohort"
}
```

## 3. MCP Resources

Da expose schema thong qua MCP resources:

```text
schema://database
schema://table/{table_name}
```

Trong MCP Inspector, resource `database_schema` da duoc hien thi va doc thanh cong.

## 4. Validation va Error Handling

Da implement validation trong `implementation/db.py`.

Server hien co the reject:

- Table khong ton tai.
- Column khong ton tai.
- Filter operator khong ho tro.
- Aggregate metric khong hop le.
- `avg` hoac `sum` tren non-numeric column.
- Insert payload rong.
- Pagination khong hop le.

SQL values duoc truyen bang parameterized query. SQL identifiers nhu table va column name duoc validate truoc khi dua vao query.

## 5. Testing va Verification

Da viet automated tests trong:

```text
implementation/tests/test_db.py
```

Ket qua test:

```text
12 passed
```

Da tao script smoke test MCP:

```bash
python implementation/verify_server.py
```

Script nay kiem tra:

- Tool discovery.
- Resource discovery.
- Resource template discovery.
- `search` thanh cong.
- `insert` thanh cong.
- `aggregate` thanh cong.
- Invalid request tra loi ro rang.

## 6. MCP Inspector Demo

Da chay MCP Inspector va verify:

- Server connected.
- Resources hien thi.
- Resource template hien thi.
- Tools hien thi du: `search`, `insert`, `aggregate`.
- Cac tool calls thanh cong.
- Invalid request tra loi ro.

Screenshots da duoc luu trong thu muc:

```text
screenshots/
```

## 7. Codex MCP Client Demo

Da cau hinh Codex MCP client voi server ten:

```text
sqlite_lab
```

Codex da nhan dien duoc MCP server thong qua `/mcp`.

Cau hinh su dung local stdio server:

```toml
[mcp_servers.sqlite_lab]
command = "/home/n91ym1nhky/Courses/AI20K/D26_0702_T3_MCP_Tool_Integration/.venv/bin/python"
args = ["/home/n91ym1nhky/Courses/AI20K/D26_0702_T3_MCP_Tool_Integration/implementation/mcp_server.py"]
``

## 8. Ket luan

Lab da hoan thien day du cac yeu cau chinh:

- FastMCP server chay duoc.
- SQLite database reproducible.
- Du 3 tools: `search`, `insert`, `aggregate`.
- Co MCP schema resources.
- Co validation va error handling an toan.
- Co automated tests va smoke verification.
- Co Inspector screenshots.
- Co Codex MCP client integration.

