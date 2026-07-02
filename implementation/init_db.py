from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("lab.db")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    cohort TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE (student_id, course_id)
);
"""


SEED_SQL = """
INSERT INTO students (name, email, cohort, status) VALUES
    ('An Nguyen', 'an.nguyen@example.edu', 'A1', 'active'),
    ('Binh Tran', 'binh.tran@example.edu', 'A1', 'active'),
    ('Chi Le', 'chi.le@example.edu', 'B1', 'active'),
    ('Dung Pham', 'dung.pham@example.edu', 'B1', 'inactive'),
    ('Ha Vo', 'ha.vo@example.edu', 'A2', 'active');

INSERT INTO courses (code, title, credits) VALUES
    ('AI101', 'Introduction to AI', 3),
    ('DB201', 'Databases for Applications', 4),
    ('MCP301', 'Model Context Protocol Integration', 3);

INSERT INTO enrollments (student_id, course_id, score) VALUES
    (1, 1, 88.5),
    (1, 2, 91.0),
    (2, 1, 76.0),
    (2, 3, 84.5),
    (3, 2, 93.0),
    (3, 3, 89.0),
    (4, 1, 67.5),
    (5, 3, 95.0);
"""


def create_database(db_path: Path | str = DB_PATH) -> Path:
    """Create a fresh SQLite database with deterministic schema and seed data."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()

    return path


def ensure_database(db_path: Path | str = DB_PATH) -> Path:
    """Create the lab database if it does not already exist."""
    path = Path(db_path)
    if not path.exists():
        create_database(path)
    return path


if __name__ == "__main__":
    created = create_database()
    print(f"Created SQLite lab database at {created}")
