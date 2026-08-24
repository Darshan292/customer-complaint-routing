from datetime import datetime, time
from zoneinfo import ZoneInfo


class WorkforceService:
    """
    Workforce eligibility engine.

    All shift calculations are performed using an
    aware datetime converted into the agent's timezone.
    """

    VALID_STATUSES = {
        "AVAILABLE",
        "BUSY",
        "AWAY",
        "OFFLINE",
        "ON_LEAVE",
    }

    ASSIGNABLE_STATUSES = {
        "AVAILABLE",
    }

    @classmethod
    def get_timezone(
        cls,
        timezone_name: str | None,
    ) -> ZoneInfo:

        try:
            return ZoneInfo(
                timezone_name or "UTC"
            )
        except Exception:
            return ZoneInfo("UTC")

    @classmethod
    def get_local_now(
        cls,
        timezone_name: str | None,
        now: datetime | None = None,
    ) -> datetime:

        timezone = cls.get_timezone(
            timezone_name
        )

        # No datetime supplied:
        # generate an aware UTC timestamp first.
        if now is None:
            return datetime.now(
                timezone
            )

        # If datetime is naive, assume UTC.
        if now.tzinfo is None:
            now = now.replace(
                tzinfo=ZoneInfo("UTC")
            )

        return now.astimezone(
            timezone
        )

    @classmethod
    def parse_days(
        cls,
        work_days: str | None,
    ) -> set[int]:

        if not work_days:
            return {
                0,
                1,
                2,
                3,
                4,
            }

        days = set()

        for value in work_days.split(","):

            value = value.strip()

            if not value:
                continue

            try:
                day = int(value)
            except ValueError:
                continue

            if 0 <= day <= 6:
                days.add(day)

        return days or {
            0,
            1,
            2,
            3,
            4,
        }

    @classmethod
    def parse_time(
        cls,
        value: str | None,
        default: str,
    ) -> time:

        raw = value or default

        try:
            hour, minute = raw.split(":")

            return time(
                hour=int(hour),
                minute=int(minute),
            )

        except (
            ValueError,
            TypeError,
        ):
            hour, minute = default.split(":")

            return time(
                hour=int(hour),
                minute=int(minute),
            )

    @classmethod
    def is_within_shift(
        cls,
        agent,
        now: datetime | None = None,
    ) -> bool:

        local_now = cls.get_local_now(
            agent.timezone,
            now,
        )

        work_days = cls.parse_days(
            agent.work_days
        )

        if local_now.weekday() not in work_days:
            return False

        shift_start = cls.parse_time(
            agent.shift_start,
            "09:00",
        )

        shift_end = cls.parse_time(
            agent.shift_end,
            "18:00",
        )

        current = local_now.time()

        # Normal daytime shift.
        if shift_start < shift_end:

            return (
                shift_start
                <= current
                < shift_end
            )

        # Overnight shift.
        return (
            current >= shift_start
            or current < shift_end
        )

    @classmethod
    def get_current_capacity(
        cls,
        agent,
    ) -> int:

        return max(
            (
                agent.max_concurrent_tickets
                or agent.capacity
                or 1
            ),
            1,
        )

    @classmethod
    def evaluate(
        cls,
        agent,
        active_ticket_count: int,
        now: datetime | None = None,
    ) -> dict:

        local_now = cls.get_local_now(
            agent.timezone,
            now,
        )

        shift_active = cls.is_within_shift(
            agent,
            now,
        )

        status_eligible = (
            agent.availability_status
            in cls.ASSIGNABLE_STATUSES
        )

        max_capacity = (
            cls.get_current_capacity(agent)
        )

        capacity_available = (
            active_ticket_count
            < max_capacity
        )

        eligible = (
            bool(agent.active)
            and bool(
                agent.auto_assignment_enabled
            )
            and status_eligible
            and shift_active
            and capacity_available
        )

        utilization = (
            active_ticket_count
            / max_capacity
        )

        reasons = []

        if not agent.active:
            reasons.append(
                "Agent account inactive"
            )

        if not agent.auto_assignment_enabled:
            reasons.append(
                "Automatic assignment disabled"
            )

        if not status_eligible:
            reasons.append(
                f"Status={agent.availability_status}"
            )

        if not shift_active:
            reasons.append(
                "Outside working shift"
            )

        if not capacity_available:
            reasons.append(
                "Concurrent ticket capacity reached"
            )

        if eligible:
            reasons.append(
                "Eligible for automatic assignment"
            )

        return {
            "eligible": eligible,
            "shift_active": shift_active,
            "status_eligible": status_eligible,
            "capacity_available": (
                capacity_available
            ),
            "active_ticket_count": (
                active_ticket_count
            ),
            "max_concurrent_tickets": (
                max_capacity
            ),
            "utilization": round(
                utilization,
                3,
            ),
            "availability_status": (
                agent.availability_status
            ),
            "timezone": agent.timezone,
            "local_time": local_now.isoformat(),
            "local_day": local_now.strftime(
                "%A"
            ),
            "shift_start": agent.shift_start,
            "shift_end": agent.shift_end,
            "work_days": agent.work_days,
            "reasons": reasons,
        }