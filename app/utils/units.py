from decimal import Decimal

KG_TO_LB_FACTOR = Decimal("2.2046226218")


def kg_to_lb(kg: Decimal) -> Decimal:
    """
    Convert kilograms to pounds.

    This function performs a pure mathematical conversion.
    It does not round or format the result.
    """
    return kg * KG_TO_LB_FACTOR


def lb_to_kg(lb: Decimal) -> Decimal:
    """
    Convert pounds to kilograms.

    This function performs a pure mathematical conversion.
    It does not round or format the result.
    """
    return lb / KG_TO_LB_FACTOR
