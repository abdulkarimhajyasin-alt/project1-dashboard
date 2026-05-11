from decimal import Decimal, InvalidOperation


MIN_DEPOSIT_AMOUNT = Decimal("10.00")

PLAN_LABELS = {
    "silver": "Silver",
    "gold": "Gold",
    "vip": "VIP",
}

PLAN_AMOUNT_RANGES = {
    "silver": {
        "min": Decimal("10.00"),
        "max": Decimal("100.00"),
        "error": "المبلغ يجب أن يكون بين 10 و 100 USDT.",
    },
    "gold": {
        "min": Decimal("101.00"),
        "max": Decimal("300.00"),
        "error": "المبلغ يجب أن يكون بين 101 و 300 USDT.",
    },
    "vip": {
        "min": Decimal("301.00"),
        "max": None,
        "error": "المبلغ يجب أن يكون 301 USDT أو أكثر.",
    },
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
    if amount <= PLAN_AMOUNT_RANGES["silver"]["max"]:
        return "silver"
    if amount <= PLAN_AMOUNT_RANGES["gold"]["max"]:
        return "gold"
    return "vip"


def plan_label(plan: str) -> str:
    return PLAN_LABELS.get(plan, plan or "-")


def validate_amount_for_plan(plan: str, amount: Decimal) -> tuple[bool, str]:
    rule = PLAN_AMOUNT_RANGES.get(plan)
    if not rule:
        return False, "الباقة غير صحيحة."

    min_amount = rule["min"]
    max_amount = rule["max"]
    if amount < min_amount or (max_amount is not None and amount > max_amount):
        return False, rule["error"]

    return True, ""
