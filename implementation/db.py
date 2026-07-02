from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    """Small validated SQLite data-access layer for the MCP tools."""

    FILTER_OPERATORS = {
        "=": "=",
        "==": "=",
        "!=": "!=",
        ">": ">",
        ">=": ">=",
        "<": "<",
        "<=": "<=",
        "like": "LIKE",
        "in": "IN",
    }
    AGGREGATES = {"count", "avg", "sum", "min", "max"}
    IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    MAX_LIMIT = 100

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({self._quote_identifier(table)})").fetchall()

        return [
            {
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]

    def get_database_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {table: self.get_table_schema(table) for table in self.list_tables()}

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self._validate_table(table)
        selected_columns = self._validate_selected_columns(table, columns)
        safe_limit = self._validate_limit(limit)
        safe_offset = self._validate_offset(offset)
        where_sql, params = self._build_where_clause(table, filters)

        order_sql = ""
        if order_by:
            self._validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {self._quote_identifier(order_by)} {direction}"

        sql = (
            f"SELECT {', '.join(self._quote_identifier(column) for column in selected_columns)} "
            f"FROM {self._quote_identifier(table)}"
            f"{where_sql}{order_sql} LIMIT ? OFFSET ?"
        )
        params.extend([safe_limit, safe_offset])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "columns": selected_columns,
            "count": len(rows),
            "limit": safe_limit,
            "offset": safe_offset,
            "rows": [dict(row) for row in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_table(table)
        if not values:
            raise ValidationError("Insert values cannot be empty.")
        if not isinstance(values, dict):
            raise ValidationError("Insert values must be an object keyed by column name.")

        columns = list(values.keys())
        for column in columns:
            self._validate_column(table, column)
            if self._is_primary_key(table, column):
                raise ValidationError(f"Column '{column}' is generated and cannot be inserted directly.")

        quoted_columns = ", ".join(self._quote_identifier(column) for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {self._quote_identifier(table)} ({quoted_columns}) VALUES ({placeholders})"

        try:
            with self.connect() as conn:
                cursor = conn.execute(sql, [values[column] for column in columns])
                inserted_id = cursor.lastrowid
                conn.commit()
                row = conn.execute(
                    f"SELECT * FROM {self._quote_identifier(table)} WHERE id = ?",
                    [inserted_id],
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValidationError(f"Insert failed: {exc}") from exc

        return {"table": table, "inserted": dict(row) if row else {**values, "id": inserted_id}}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | dict[str, Any] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self._validate_table(table)
        normalized_metric = metric.lower()
        if normalized_metric not in self.AGGREGATES:
            allowed = ", ".join(sorted(self.AGGREGATES))
            raise ValidationError(f"Unsupported aggregate metric '{metric}'. Allowed metrics: {allowed}.")

        aggregate_expr = self._build_aggregate_expression(table, normalized_metric, column)
        where_sql, params = self._build_where_clause(table, filters)

        group_select = ""
        group_sql = ""
        if group_by:
            self._validate_column(table, group_by)
            quoted_group = self._quote_identifier(group_by)
            group_select = f"{quoted_group} AS group_key, "
            group_sql = f" GROUP BY {quoted_group} ORDER BY {quoted_group}"

        sql = (
            f"SELECT {group_select}{aggregate_expr} AS value "
            f"FROM {self._quote_identifier(table)}{where_sql}{group_sql}"
        )

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "metric": normalized_metric,
            "column": column,
            "group_by": group_by,
            "rows": [dict(row) for row in rows],
        }

    def _build_aggregate_expression(self, table: str, metric: str, column: str | None) -> str:
        if metric == "count" and column is None:
            return "COUNT(*)"
        if column is None:
            raise ValidationError(f"Aggregate metric '{metric}' requires a column.")

        self._validate_column(table, column)
        column_type = self._column_type(table, column)
        if metric in {"avg", "sum"} and not self._is_numeric_type(column_type):
            raise ValidationError(f"Aggregate metric '{metric}' requires a numeric column.")

        return f"{metric.upper()}({self._quote_identifier(column)})"

    def _build_where_clause(
        self,
        table: str,
        filters: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> tuple[str, list[Any]]:
        normalized_filters = self._normalize_filters(filters)
        if not normalized_filters:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []

        for filter_item in normalized_filters:
            column = filter_item.get("column")
            operator = str(filter_item.get("operator", "=")).lower()
            value = filter_item.get("value")

            if not isinstance(column, str):
                raise ValidationError("Each filter must include a string 'column'.")
            self._validate_column(table, column)
            if operator not in self.FILTER_OPERATORS:
                allowed = ", ".join(sorted(self.FILTER_OPERATORS))
                raise ValidationError(f"Unsupported filter operator '{operator}'. Allowed operators: {allowed}.")

            sql_operator = self.FILTER_OPERATORS[operator]
            if operator == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError("The 'in' operator requires a non-empty list value.")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{self._quote_identifier(column)} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{self._quote_identifier(column)} {sql_operator} ?")
                params.append(value)

        return " WHERE " + " AND ".join(clauses), params

    def _normalize_filters(
        self,
        filters: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if filters is None:
            return []
        if isinstance(filters, list):
            return filters
        if isinstance(filters, dict):
            if {"column", "value"}.issubset(filters.keys()):
                return [filters]
            return [{"column": column, "operator": "=", "value": value} for column, value in filters.items()]
        raise ValidationError("Filters must be a list of filter objects or an object of exact matches.")

    def _validate_table(self, table: str) -> None:
        if not self._valid_identifier(table):
            raise ValidationError(f"Invalid table name '{table}'.")
        if table not in self.list_tables():
            raise ValidationError(f"Unknown table '{table}'.")

    def _validate_column(self, table: str, column: str) -> None:
        if not self._valid_identifier(column):
            raise ValidationError(f"Invalid column name '{column}'.")
        columns = {item["name"] for item in self.get_table_schema(table)}
        if column not in columns:
            raise ValidationError(f"Unknown column '{column}' for table '{table}'.")

    def _validate_selected_columns(self, table: str, columns: list[str] | None) -> list[str]:
        available = [item["name"] for item in self.get_table_schema(table)]
        if columns is None:
            return available
        if not columns:
            raise ValidationError("Selected columns cannot be empty.")
        for column in columns:
            self._validate_column(table, column)
        return columns

    def _validate_limit(self, limit: int) -> int:
        try:
            value = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Limit must be an integer.") from exc
        if value < 1 or value > self.MAX_LIMIT:
            raise ValidationError(f"Limit must be between 1 and {self.MAX_LIMIT}.")
        return value

    def _validate_offset(self, offset: int) -> int:
        try:
            value = int(offset)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Offset must be an integer.") from exc
        if value < 0:
            raise ValidationError("Offset must be zero or greater.")
        return value

    def _valid_identifier(self, identifier: str) -> bool:
        return isinstance(identifier, str) and bool(self.IDENTIFIER_RE.match(identifier))

    def _quote_identifier(self, identifier: str) -> str:
        if not self._valid_identifier(identifier):
            raise ValidationError(f"Invalid SQL identifier '{identifier}'.")
        return f'"{identifier}"'

    def _column_type(self, table: str, column: str) -> str:
        for item in self.get_table_schema(table):
            if item["name"] == column:
                return str(item["type"]).upper()
        raise ValidationError(f"Unknown column '{column}' for table '{table}'.")

    def _is_numeric_type(self, column_type: str) -> bool:
        return any(token in column_type.upper() for token in ("INT", "REAL", "NUM", "DEC", "DOUBLE", "FLOAT"))

    def _is_primary_key(self, table: str, column: str) -> bool:
        return any(item["name"] == column and item["primary_key"] for item in self.get_table_schema(table))
