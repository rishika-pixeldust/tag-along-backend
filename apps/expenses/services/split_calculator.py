"""
Utilities for calculating how an expense is split among group members.

All functions return dictionaries mapping user IDs to ``Decimal`` amounts,
ensuring the individual shares always sum to the original total (any
rounding remainder is assigned to the first participant).
"""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal


def calculate_equal_split(amount, member_ids):
    """
    Split *amount* equally among *member_ids*.

    Parameters
    ----------
    amount : Decimal | str | int | float
        The total amount to split.
    member_ids : list
        A list of user IDs (UUIDs or strings) to split among.

    Returns
    -------
    dict
        ``{user_id: Decimal}`` mapping each member to their share.

    Raises
    ------
    ValueError
        If *member_ids* is empty.
    """
    if not member_ids:
        raise ValueError('member_ids must not be empty.')

    amount = Decimal(str(amount))
    num = len(member_ids)

    # Calculate per-person share truncated to 2 decimal places
    per_person = (amount / num).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    remainder = amount - (per_person * num)

    result = {}
    for i, uid in enumerate(member_ids):
        share = per_person
        if i == 0:
            # Give the rounding remainder to the first member
            share += remainder
        result[uid] = share.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return result


def calculate_percentage_split(amount, percentages):
    """
    Split *amount* according to the given *percentages*.

    Parameters
    ----------
    amount : Decimal | str | int | float
        The total amount to split.
    percentages : dict
        ``{user_id: Decimal}`` mapping each member to their percentage
        (values should sum to 100).

    Returns
    -------
    dict
        ``{user_id: Decimal}`` mapping each member to their share.

    Raises
    ------
    ValueError
        If percentages do not sum to 100.
    """
    if not percentages:
        raise ValueError('percentages must not be empty.')

    amount = Decimal(str(amount))

    total_pct = sum(Decimal(str(v)) for v in percentages.values())
    if total_pct != Decimal('100'):
        raise ValueError(
            f'Percentages must sum to 100, got {total_pct}.'
        )

    result = {}
    running_total = Decimal('0')
    items = list(percentages.items())

    for uid, pct in items[:-1]:
        share = (amount * Decimal(str(pct)) / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        result[uid] = share
        running_total += share

    # Last member gets whatever is left to guarantee the sum is exact
    last_uid, _ = items[-1]
    result[last_uid] = amount - running_total

    return result


def calculate_exact_split(amounts):
    """
    Validate and return the exact split amounts.

    Parameters
    ----------
    amounts : dict
        ``{user_id: Decimal | str | int | float}`` of exact per-member amounts.

    Returns
    -------
    dict
        ``{user_id: Decimal}`` with each value quantized to 2 decimal places.

    Raises
    ------
    ValueError
        If *amounts* is empty.
    """
    if not amounts:
        raise ValueError('amounts must not be empty.')

    return {
        uid: Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        for uid, val in amounts.items()
    }
