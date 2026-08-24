from datetime import datetime

from app.services.business_calendar import (
    BusinessCalendar,
)


class SLAService:

    SLA_HOURS = {
        "Low": 48,
        "Medium": 24,
        "High": 8,
        "Critical": 4,
    }

    FIRST_RESPONSE_MINUTES = {
        "Low": 120,
        "Medium": 60,
        "High": 30,
        "Critical": 15,
    }

    AT_RISK_THRESHOLD = {
        "Low": 8,
        "Medium": 4,
        "High": 2,
        "Critical": 1,
    }

    @classmethod
    def get_sla_hours(
        cls,
        priority_level: str,
    ) -> int:

        return cls.SLA_HOURS.get(
            priority_level,
            24,
        )

    @classmethod
    def get_first_response_minutes(
        cls,
        priority_level: str,
    ) -> int:

        return cls.FIRST_RESPONSE_MINUTES.get(
            priority_level,
            60,
        )

    @classmethod
    def calculate_deadline(
        cls,
        priority_level: str,
        started_at: datetime,
        timezone_name: str = "Asia/Kolkata",
    ) -> datetime:

        return BusinessCalendar.add_business_hours(
            start=started_at,
            hours=cls.get_sla_hours(
                priority_level
            ),
            timezone_name=timezone_name,
        )

    @classmethod
    def calculate_first_response_deadline(
        cls,
        priority_level: str,
        started_at: datetime,
        timezone_name: str = "Asia/Kolkata",
    ) -> datetime:

        return BusinessCalendar.add_business_seconds(
            start=started_at,
            seconds=(
                cls.get_first_response_minutes(
                    priority_level
                )
                * 60
            ),
            timezone_name=timezone_name,
        )

    @classmethod
    def evaluate_first_response(
        cls,
        priority_level: str,
        deadline: datetime | None,
        responded_at: datetime | None = None,
        now: datetime | None = None,
        timezone_name: str = "Asia/Kolkata",
    ) -> dict:

        if responded_at:

            return {
                "state": "RESPONDED",
                "breached": False,
                "at_risk": False,
                "remaining_seconds": 0,
                "remaining_minutes": 0,
                "deadline": deadline,
                "responded_at": responded_at,
            }

        if not deadline:

            return {
                "state": "NO_SLA",
                "breached": False,
                "at_risk": False,
                "remaining_seconds": None,
                "remaining_minutes": None,
                "deadline": None,
                "responded_at": None,
            }

        now = (
            now
            or datetime.utcnow()
        )

        if now >= deadline:

            return {
                "state": "BREACHED",
                "breached": True,
                "at_risk": True,
                "remaining_seconds": 0,
                "remaining_minutes": 0,
                "deadline": deadline,
                "responded_at": None,
            }

        remaining_seconds = (
            BusinessCalendar.business_seconds_between(
                now,
                deadline,
                timezone_name,
            )
        )

        remaining_minutes = (
            remaining_seconds / 60
        )

        threshold = cls.get_first_response_minutes(
            priority_level
        )

        # At risk when only 25% of the original
        # first-response window remains.
        at_risk_threshold = (
            threshold * 0.25
        )

        return {
            "state": (
                "AT_RISK"
                if remaining_minutes
                <= at_risk_threshold
                else "ON_TRACK"
            ),
            "breached": False,
            "at_risk": (
                remaining_minutes
                <= at_risk_threshold
            ),
            "remaining_seconds": (
                remaining_seconds
            ),
            "remaining_minutes": (
                remaining_minutes
            ),
            "deadline": deadline,
            "responded_at": None,
        }

    @classmethod
    def evaluate_resolution(
        cls,
        priority_level: str,
        deadline: datetime | None,
        now: datetime | None = None,
        timezone_name: str = "Asia/Kolkata",
    ) -> dict:

        if not deadline:

            return {
                "state": "NO_SLA",
                "breached": False,
                "at_risk": False,
                "remaining_seconds": None,
                "remaining_hours": None,
            }

        now = (
            now
            or datetime.utcnow()
        )

        if now >= deadline:

            return {
                "state": "BREACHED",
                "breached": True,
                "at_risk": True,
                "remaining_seconds": 0,
                "remaining_hours": 0,
                "deadline": deadline,
            }

        remaining_seconds = (
            BusinessCalendar.business_seconds_between(
                now,
                deadline,
                timezone_name,
            )
        )

        remaining_hours = (
            remaining_seconds / 3600
        )

        threshold = cls.AT_RISK_THRESHOLD.get(
            priority_level,
            4,
        )

        at_risk = (
            remaining_hours
            <= threshold
        )

        return {
            "state": (
                "AT_RISK"
                if at_risk
                else "ON_TRACK"
            ),
            "breached": False,
            "at_risk": at_risk,
            "remaining_seconds": (
                remaining_seconds
            ),
            "remaining_hours": (
                remaining_hours
            ),
            "deadline": deadline,
        }

    @classmethod
    def evaluate(
        cls,
        priority_level: str,
        deadline: datetime | None,
        now: datetime | None = None,
        timezone_name: str = "Asia/Kolkata",
    ) -> dict:

        return cls.evaluate_resolution(
            priority_level=priority_level,
            deadline=deadline,
            now=now,
            timezone_name=timezone_name,
        )