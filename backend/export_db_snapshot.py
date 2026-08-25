import json
import sqlite3
from pathlib import Path

DB_PATH = Path("complaints.db")
OUT_PATH = Path("complaints_snapshot.json")

# Columns that should never be exported.
SENSITIVE_COLUMN_NAMES = {
    "password",
    "password_hash",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "reset_token",
}

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

tables = [
    row[0]
    for row in conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
]

snapshot = {
    "database": str(DB_PATH),
    "tables": {},
}

for table in tables:
    columns_info = conn.execute(
        f"PRAGMA table_info([{table}])"
    ).fetchall()

    columns = [
        row["name"]
        for row in columns_info
        if row["name"].lower() not in SENSITIVE_COLUMN_NAMES
    ]

    rows = conn.execute(
        f"SELECT * FROM [{table}]"
    ).fetchall()

    cleaned_rows = []

    for row in rows:
        cleaned_rows.append(
            {
                column: row[column]
                for column in columns
            }
        )

    snapshot["tables"][table] = {
        "columns": columns,
        "row_count": len(cleaned_rows),
        "rows": cleaned_rows,
    }

conn.close()

OUT_PATH.write_text(
    json.dumps(
        snapshot,
        indent=2,
        default=str,
    ),
    encoding="utf-8",
)

print("=" * 60)
print("DATABASE SNAPSHOT CREATED")
print("=" * 60)

for table, data in snapshot["tables"].items():
    print(
        f"{table}: "
        f"{data['row_count']} rows, "
        f"{len(data['columns'])} columns"
    )

print()
print(f"Output: {OUT_PATH.resolve()}")