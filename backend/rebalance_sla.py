from __future__ import annotations

import sqlite3
from datetime import datetime

DB_PATH = "complaints.db"

# Keep at most this many breached active tickets per resolver.
MAX_BREACHED_PER_RESOLVER = 2


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # ------------------------------------------------------------
        # Get all assigned tickets that are currently active.
        # ------------------------------------------------------------
        rows = conn.execute(
            """
            SELECT
                id,
                assigned_agent_id,
                assigned_agent_name,
                status,
                priority_level,
                sla_deadline,
                resolved_at,
                updated_at
            FROM complaints
            WHERE assigned_agent_id IS NOT NULL
              AND status IN (
                    'OPEN',
                    'IN_PROGRESS',
                    'PENDING_CUSTOMER'
              )
            ORDER BY
                assigned_agent_id,
                created_at DESC
            """
        ).fetchall()

        now = datetime.now().isoformat(sep=" ")

        breached_kept = {}
        closed_count = 0
        kept_count = 0

        for ticket in rows:

            agent_id = ticket["assigned_agent_id"]

            current_count = breached_kept.get(
                agent_id,
                0,
            )

            # --------------------------------------------------------
            # Keep only 1–2 active tickets per resolver.
            #
            # We keep the first two encountered for each resolver
            # as active/breached and close the rest.
            # --------------------------------------------------------
            if current_count < MAX_BREACHED_PER_RESOLVER:

                breached_kept[agent_id] = (
                    current_count + 1
                )

                kept_count += 1

                continue

            # --------------------------------------------------------
            # Close everything beyond the allowed breached tickets.
            # --------------------------------------------------------

            conn.execute(
                """
                UPDATE complaints
                SET
                    status = 'CLOSED',
                    resolved_at = COALESCE(
                        resolved_at,
                        ?
                    ),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    now,
                    now,
                    ticket["id"],
                ),
            )

            # --------------------------------------------------------
            # Add an audit event.
            # --------------------------------------------------------

            conn.execute(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    actor_id,
                    actor_role,
                    event_type,
                    from_value,
                    to_value,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket["id"],
                    ticket["assigned_agent_id"],
                    "system",
                    "DEMO_DATA_REBALANCED",
                    ticket["status"],
                    "CLOSED",
                    (
                        "Historical demonstration ticket closed "
                        "during SLA dataset rebalancing. "
                        "This does not represent a real customer action."
                    ),
                    now,
                ),
            )

            closed_count += 1

        conn.commit()

        print("=" * 70)
        print("DEMO SLA DATA REBALANCED")
        print("=" * 70)
        print(
            f"Active breached tickets retained : {kept_count}"
        )
        print(
            f"Historical tickets closed         : {closed_count}"
        )
        print()

        # ------------------------------------------------------------
        # Show result per resolver.
        # ------------------------------------------------------------

        results = conn.execute(
            """
            SELECT
                assigned_agent_id,
                assigned_agent_name,
                COUNT(*) AS active_count
            FROM complaints
            WHERE assigned_agent_id IS NOT NULL
              AND status IN (
                    'OPEN',
                    'IN_PROGRESS',
                    'PENDING_CUSTOMER'
              )
            GROUP BY
                assigned_agent_id,
                assigned_agent_name
            ORDER BY assigned_agent_id
            """
        ).fetchall()

        print("ACTIVE TICKETS BY RESOLVER")
        print("-" * 70)

        for row in results:
            print(
                f"{row['assigned_agent_name']}: "
                f"{row['active_count']} active"
            )

        # ------------------------------------------------------------
        # Overall status distribution.
        # ------------------------------------------------------------

        print()
        print("STATUS DISTRIBUTION")
        print("-" * 70)

        status_rows = conn.execute(
            """
            SELECT
                status,
                COUNT(*) AS count
            FROM complaints
            GROUP BY status
            ORDER BY status
            """
        ).fetchall()

        for row in status_rows:
            print(
                f"{row['status']}: "
                f"{row['count']}"
            )

        print()
        print(
            "Rebuild the RAG index afterward:"
        )
        print(
            "python rebuild_resolution_index.py"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()

