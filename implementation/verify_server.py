from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

try:
    from .init_db import create_database
except ImportError:
    from init_db import create_database


async def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    python_bin = project_root / ".venv" / "bin" / "python"
    server_path = project_root / "implementation" / "mcp_server.py"

    create_database(project_root / "implementation" / "lab.db")

    server = StdioServerParameters(
        command=str(python_bin),
        args=[str(server_path)],
        cwd=str(project_root),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            print("TOOLS", json.dumps(tool_names))
            assert {"aggregate", "insert", "search"}.issubset(tool_names)

            resources = await session.list_resources()
            resource_uris = sorted(str(resource.uri) for resource in resources.resources)
            print("RESOURCES", json.dumps(resource_uris))
            assert "schema://database" in resource_uris

            templates = await session.list_resource_templates()
            template_uris = sorted(str(template.uriTemplate) for template in templates.resourceTemplates)
            print("RESOURCE_TEMPLATES", json.dumps(template_uris))
            assert "schema://table/{table_name}" in template_uris

            schema = await session.read_resource("schema://database")
            print("SCHEMA_READ", schema.contents[0].text[:120].replace("\n", " "))

            search_result = await session.call_tool(
                "search",
                {
                    "table": "students",
                    "filters": {"cohort": "A1"},
                    "columns": ["id", "name", "cohort"],
                    "limit": 5,
                    "order_by": "name",
                },
            )
            print("SEARCH_OK", json.loads(search_result.content[0].text))

            insert_result = await session.call_tool(
                "insert",
                {
                    "table": "students",
                    "values": {
                        "name": "Lan Hoang",
                        "email": "lan.hoang@example.edu",
                        "cohort": "A3",
                        "status": "active",
                    },
                },
            )
            print("INSERT_OK", json.loads(insert_result.content[0].text))

            aggregate_result = await session.call_tool(
                "aggregate",
                {"table": "students", "metric": "count", "group_by": "cohort"},
            )
            print("AGGREGATE_OK", json.loads(aggregate_result.content[0].text))

            invalid_result = await session.call_tool("search", {"table": "missing_table"})
            if invalid_result.isError:
                print("INVALID_OK", invalid_result.content[0].text.splitlines()[0])
            else:
                raise AssertionError("Invalid table call should fail.")


if __name__ == "__main__":
    asyncio.run(main())
