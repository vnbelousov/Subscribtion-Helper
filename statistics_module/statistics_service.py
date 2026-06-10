from decimal import Decimal

from data_access_module.models import Subscription

def calculate_monthly_price(subscription: Subscription) -> Decimal:
    if subscription.billing_period == "monthly":
        return subscription.price

    if subscription.billing_period == "quarterly":
        return subscription.price / Decimal("3")

    if subscription.billing_period == "yearly":
        return subscription.price / Decimal("12")

    return Decimal("0")


def calculate_yearly_price(subscription: Subscription) -> Decimal:
    if subscription.billing_period == "monthly":
        return subscription.price * Decimal("12")

    if subscription.billing_period == "quarterly":
        return subscription.price * Decimal("4")

    if subscription.billing_period == "yearly":
        return subscription.price

    return Decimal("0")


def build_statistics_report(subscriptions: list[Subscription]) -> str:
    if not subscriptions:
        return (
            "Статистика пока недоступна.\n\n"
            "Добавьте хотя бы одну активную подписку."
        )

    monthly_total = Decimal("0")
    yearly_total = Decimal("0")
    category_totals: dict[str, Decimal] = {}

    for subscription in subscriptions:
        monthly_price = calculate_monthly_price(subscription)
        yearly_price = calculate_yearly_price(subscription)

        monthly_total += monthly_price
        yearly_total += yearly_price

        category_name = (
            f"{subscription.category.icon} {subscription.category.name}"
        )

        if category_name not in category_totals:
            category_totals[category_name] = Decimal("0")

        category_totals[category_name] += monthly_price

    text = (
        "Статистика расходов по подпискам\n\n"
        f"Расходы в месяц: {monthly_total:.2f} RUB\n"
        f"Расходы в год: {yearly_total:.2f} RUB\n\n"
        "Расходы по категориям в месяц:\n"
    )

    for category_name, total in category_totals.items():
        text += f"• {category_name}: {total:.2f} RUB\n"

    return text