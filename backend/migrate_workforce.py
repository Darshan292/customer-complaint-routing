from sqlalchemy import inspect, text

from app.database.db import engine


AGENT_COLUMNS = {
    "max_concurrent_tickets": "INTEGER DEFAULT 10",
    "availability_status": "VARCHAR DEFAULT 'AVAILABLE'",
    "shift_start": "VARCHAR DEFAULT '09:00'",
    "shift_end": "VARCHAR DEFAULT '18:00'",
    "work_days": "VARCHAR DEFAULT '0,1,2,3,4'",
    "auto_assignment_enabled": "BOOLEAN DEFAULT 1",
    "last_status_change_at": "DATETIME",
    "created_at": "DATETIME",
    "updated_at": "DATETIME",
    "on_call_enabled": ("BOOLEAN DEFAULT 0"),
    
}


COMPLAINT_COLUMNS = {
    "keywords": "TEXT",
    "routing_reason": "TEXT",

    "priority_source": (
        "VARCHAR DEFAULT 'AI'"
    ),

    "priority_score": (
        "FLOAT DEFAULT 0"
    ),

    "priority_level": (
        "VARCHAR DEFAULT 'Medium'"
    ),

    "assigned_team": "VARCHAR",

    "assigned_agent_id": (
        "INTEGER"
    ),

    "assigned_agent_name": (
        "VARCHAR"
    ),

    "queue": "VARCHAR",

    "status": (
        "VARCHAR DEFAULT 'OPEN'"
    ),

    "escalation_required": (
        "BOOLEAN DEFAULT 0"
    ),

    "sla_hours": "INTEGER",

    "sla_deadline": "DATETIME",

    "first_response_at": "DATETIME",

    "resolved_at": "DATETIME",

    "first_response_sla_minutes": (
        "INTEGER DEFAULT 30"
    ),

    "first_response_deadline": (
        "DATETIME"
    ),

    "sla_paused_at": (
        "DATETIME"
    ),

    "sla_total_paused_seconds": (
        "FLOAT DEFAULT 0"
    ),

        "escalation_level": (
        "INTEGER DEFAULT 0"
    ),

    "escalated_at": (
        "DATETIME"
    ),

    "escalation_reason": (
        "VARCHAR"
    ),

    "escalation_owner": (
        "VARCHAR"
    ),

    "escalation_count": (
        "INTEGER DEFAULT 0"
    ),

    "assignment_score": "FLOAT",

    "assignment_explanation": "TEXT",

    "updated_at": "DATETIME",
}


def get_columns(
    inspector,
    table_name: str,
) -> set[str]:

    return {
        column["name"]
        for column in inspector.get_columns(
            table_name
        )
    }


def add_missing_columns(
    connection,
    table_name: str,
    existing_columns: set[str],
    columns: dict,
):

    for column_name, definition in columns.items():

        if column_name in existing_columns:
            print(
                f"[SKIP] {table_name}.{column_name} "
                "already exists"
            )
            continue

        sql = (
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} "
            f"{definition}"
        )

        connection.execute(text(sql))

        print(
            f"[ADD] {table_name}.{column_name}"
        )


def migrate():

    inspector = inspect(engine)

    tables = set(
        inspector.get_table_names()
    )

    required_tables = {
        "agents",
        "complaints",
    }

    missing_tables = (
        required_tables - tables
    )

    if missing_tables:
        raise RuntimeError(
            "Required tables are missing: "
            + ", ".join(
                sorted(missing_tables)
            )
            + ". Run `python init_db.py` first."
        )

    agent_columns = get_columns(
        inspector,
        "agents",
    )

    complaint_columns = get_columns(
        inspector,
        "complaints",
    )

    with engine.begin() as connection:

        # ---------------------------------------------
        # AGENT MIGRATION
        # ---------------------------------------------

        add_missing_columns(
            connection=connection,
            table_name="agents",
            existing_columns=agent_columns,
            columns=AGENT_COLUMNS,
        )

        # ---------------------------------------------
        # COMPLAINT MIGRATION
        # ---------------------------------------------

        add_missing_columns(
            connection=connection,
            table_name="complaints",
            existing_columns=complaint_columns,
            columns=COMPLAINT_COLUMNS,
        )

        # ---------------------------------------------
        # AGENT DEFAULTS
        # ---------------------------------------------

        connection.execute(
            text(
                """
                UPDATE agents
                SET
                    max_concurrent_tickets =
                        COALESCE(
                            max_concurrent_tickets,
                            capacity,
                            10
                        ),
                    availability_status =
                        COALESCE(
                            availability_status,
                            'AVAILABLE'
                        ),
                    shift_start =
                        COALESCE(
                            shift_start,
                            '09:00'
                        ),
                    shift_end =
                        COALESCE(
                            shift_end,
                            '18:00'
                        ),
                    work_days =
                        COALESCE(
                            work_days,
                            '0,1,2,3,4'
                        ),
                    auto_assignment_enabled =
                        COALESCE(
                            auto_assignment_enabled,
                            1
                        )
                """
            )
        )

        # ---------------------------------------------
        # COMPLAINT DEFAULTS
        # ---------------------------------------------

        connection.execute(
            text(
                """
                UPDATE complaints
                SET
                    priority_source =
                        COALESCE(
                            priority_source,
                            'AI'
                        ),
                    priority_score =
                        COALESCE(
                            priority_score,
                            0
                        ),
                    priority_level =
                        COALESCE(
                            priority_level,
                            'Medium'
                        ),
                    status =
                        COALESCE(
                            status,
                            'OPEN'
                        ),
                    escalation_required =
                        COALESCE(
                            escalation_required,
                            0
                        )
                """
            )
        )

    print()
    print(
        "======================================"
    )
    print(
        "DATABASE MIGRATION COMPLETED"
    )
    print(
        "======================================"
    )


if __name__ == "__main__":
    migrate()