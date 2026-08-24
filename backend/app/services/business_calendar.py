from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class BusinessCalendar:

    DEFAULT_TIMEZONE = "Asia/Kolkata"

    DEFAULT_START_HOUR = 9
    DEFAULT_END_HOUR = 18

    WORKING_DAYS = {
        0,
        1,
        2,
        3,
        4,
    }

    HOLIDAYS = {
        "2026-01-26",
        "2026-08-15",
        "2026-10-02",
        "2026-12-25",
    }

    @classmethod
    def timezone(
        cls,
        timezone_name: str | None = None,
    ) -> ZoneInfo:

        try:
            return ZoneInfo(
                timezone_name
                or cls.DEFAULT_TIMEZONE
            )
        except Exception:
            return ZoneInfo(
                cls.DEFAULT_TIMEZONE
            )

    @classmethod
    def ensure_aware(
        cls,
        value: datetime,
    ) -> datetime:

        if value.tzinfo is None:
            return value.replace(
                tzinfo=ZoneInfo("UTC")
            )

        return value

    @classmethod
    def to_timezone(
        cls,
        value: datetime,
        timezone_name: str | None = None,
    ) -> datetime:

        value = cls.ensure_aware(value)

        return value.astimezone(
            cls.timezone(
                timezone_name
            )
        )

    @classmethod
    def to_utc_naive(
        cls,
        value: datetime,
    ) -> datetime:

        value = cls.ensure_aware(value)

        return (
            value.astimezone(
                ZoneInfo("UTC")
            )
            .replace(tzinfo=None)
        )

    @classmethod
    def is_holiday(
        cls,
        current: datetime,
    ) -> bool:

        return (
            current.strftime("%Y-%m-%d")
            in cls.HOLIDAYS
        )

    @classmethod
    def is_business_day(
        cls,
        current: datetime,
    ) -> bool:

        return (
            current.weekday()
            in cls.WORKING_DAYS
            and not cls.is_holiday(
                current
            )
        )

    @classmethod
    def business_start(
        cls,
        current: datetime,
    ) -> datetime:

        return current.replace(
            hour=cls.DEFAULT_START_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )

    @classmethod
    def business_end(
        cls,
        current: datetime,
    ) -> datetime:

        return current.replace(
            hour=cls.DEFAULT_END_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )

    @classmethod
    def normalize(
        cls,
        current: datetime,
        timezone_name: str | None = None,
    ) -> datetime:

        current = cls.to_timezone(
            current,
            timezone_name,
        )

        while True:

            if not cls.is_business_day(
                current
            ):

                current = (
                    current
                    + timedelta(days=1)
                ).replace(
                    hour=cls.DEFAULT_START_HOUR,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

                continue

            start = cls.business_start(
                current
            )

            end = cls.business_end(
                current
            )

            if current < start:
                return start

            if current >= end:

                current = (
                    current
                    + timedelta(days=1)
                ).replace(
                    hour=cls.DEFAULT_START_HOUR,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

                continue

            return current

    @classmethod
    def add_business_hours(
        cls,
        start: datetime,
        hours: float,
        timezone_name: str | None = None,
    ) -> datetime:

        current = cls.normalize(
            start,
            timezone_name,
        )

        remaining_seconds = (
            float(hours) * 3600
        )

        while remaining_seconds > 0:

            current = cls.normalize(
                current,
                timezone_name,
            )

            end = cls.business_end(
                current
            )

            available_seconds = (
                end - current
            ).total_seconds()

            if (
                remaining_seconds
                <= available_seconds
            ):

                return cls.to_utc_naive(
                    current
                    + timedelta(
                        seconds=remaining_seconds
                    )
                )

            remaining_seconds -= (
                available_seconds
            )

            current = (
                current
                + timedelta(days=1)
            ).replace(
                hour=cls.DEFAULT_START_HOUR,
                minute=0,
                second=0,
                microsecond=0,
            )

        return cls.to_utc_naive(
            current
        )

    @classmethod
    def add_business_seconds(
        cls,
        start: datetime,
        seconds: float,
        timezone_name: str | None = None,
    ) -> datetime:

        return cls.add_business_hours(
            start=start,
            hours=seconds / 3600,
            timezone_name=timezone_name,
        )

    @classmethod
    def business_seconds_between(
        cls,
        start: datetime,
        end: datetime,
        timezone_name: str | None = None,
    ) -> float:

        start_local = cls.to_timezone(
            start,
            timezone_name,
        )

        end_local = cls.to_timezone(
            end,
            timezone_name,
        )

        if end_local <= start_local:
            return 0.0

        total_seconds = 0.0
        cursor = start_local

        while cursor < end_local:

            if not cls.is_business_day(
                cursor
            ):

                cursor = (
                    cursor
                    + timedelta(days=1)
                ).replace(
                    hour=cls.DEFAULT_START_HOUR,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

                continue

            day_start = cls.business_start(
                cursor
            )

            day_end = cls.business_end(
                cursor
            )

            if cursor < day_start:

                cursor = day_start
                continue

            if cursor >= day_end:

                cursor = (
                    cursor
                    + timedelta(days=1)
                ).replace(
                    hour=cls.DEFAULT_START_HOUR,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

                continue

            segment_end = min(
                day_end,
                end_local,
            )

            total_seconds += (
                segment_end - cursor
            ).total_seconds()

            cursor = segment_end

            if cursor < end_local:

                cursor = (
                    cursor
                    + timedelta(days=1)
                ).replace(
                    hour=cls.DEFAULT_START_HOUR,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

        return max(
            total_seconds,
            0.0,
        )