from datetime import datetime, date
import calendar


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def add_months(source_date: date, months: int) -> date:
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(source_date.day, last_day)

    return date(year, month, day)


def calculate_next_payment_date(
    current_date: date,
    billing_period: str,
) -> date:
    if billing_period == "monthly":
        return add_months(current_date, 1)

    if billing_period == "quarterly":
        return add_months(current_date, 3)

    if billing_period == "yearly":
        return add_months(current_date, 12)

    return current_date