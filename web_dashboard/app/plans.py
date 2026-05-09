from decimal import Decimal, InvalidOperation


MIN_DEPOSIT_AMOUNT = Decimal("10.00")

PLAN_LABELS = {
    "silver": "Silver",
    "gold": "Gold",
    "vip": "VIP",
}


def parse_deposit_amount(value: str | Decimal | int | float | None) -> Decimal:
    try:
        amount = Decimal(str(value or "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("يرجى إدخال مبلغ صحيح.")

    if amount < MIN_DEPOSIT_AMOUNT:
        raise ValueError("لا يمكن إرسال طلب بمبلغ أقل من 10 USDT.")

    return amount.quantize(Decimal("0.01"))


def determine_plan_for_amount(amount: Decimal) -> str:
    if amount <= Decimal("100.00"):
        return "silver"
    if amount <= Decimal("300.00"):
        return "gold"
    return "vip"


def plan_label(plan: str) -> str:
    return PLAN_LABELS.get(plan, plan or "-")
