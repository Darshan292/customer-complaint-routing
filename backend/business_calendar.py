from datetime import datetime

from app.services.business_calendar import (
    BusinessCalendar,
)


def show(
    label,
    value,
):
    print(
        f"{label}: "
        f"{value}"
    )


def main():

    timezone = "Asia/Kolkata"

    # Friday 16:00
    friday = datetime(
        2026,
        8,
        14,
        16,
        0,
    )

    # Four business hours should move
    # into Monday because the remaining
    # Friday business window is only 2 hours.
    deadline = (
        BusinessCalendar.add_business_hours(
            friday,
            4,
            timezone,
        )
    )

    show(
        "Friday 16:00 + 4 business hours",
        deadline,
    )

    # Saturday.
    saturday = datetime(
        2026,
        8,
        15,
        12,
        0,
    )

    normalized = (
        BusinessCalendar.normalize(
            saturday,
            timezone,
        )
    )

    show(
        "Saturday normalized",
        normalized,
    )


if __name__ == "__main__":
    main()