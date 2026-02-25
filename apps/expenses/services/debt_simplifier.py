"""
Debt simplification using the min-cash-flow (greedy heap) algorithm.

Given all unsettled expenses in a group, this module computes each member's
net balance and then greedily matches the largest creditor with the largest
debtor, producing the minimum number of settlement transactions.
"""
import heapq
import logging
from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from apps.expenses.models import Debt, Expense, ExpenseSplit
from apps.users.models import User

logger = logging.getLogger(__name__)


def simplify_debts(group_id):
    """
    Simplify all outstanding debts within a group.

    Algorithm
    ---------
    1. Fetch every unsettled expense for *group_id*.
    2. Compute net balance per member:
       ``net[user] = total_paid - total_owed`` (via splits).
    3. Separate members into *creditors* (net > 0) and *debtors* (net < 0).
    4. Use two heaps (max-heap for creditors, max-heap for absolute-value
       debtors) to greedily pair the largest creditor with the largest
       debtor, emitting one ``Debt`` record per pair.
    5. Delete old unsettled ``Debt`` records for the group.
    6. Bulk-create the new simplified ``Debt`` records.
    7. Return the new ``Debt`` queryset.
    """
    # Step 1: Gather all expenses for this group (settled debts are ignored;
    #         we look at expenses, not existing debt records).
    expenses = Expense.objects.filter(group_id=group_id).select_related('paid_by')
    splits = ExpenseSplit.objects.filter(
        expense__group_id=group_id,
    ).select_related('user', 'expense')

    # Step 2: Calculate net balance for each user.
    #   net > 0 => others owe this person money (creditor)
    #   net < 0 => this person owes money (debtor)
    net_balance = defaultdict(Decimal)

    for expense in expenses:
        net_balance[expense.paid_by_id] += expense.amount

    for split in splits:
        net_balance[split.user_id] -= split.amount

    # Remove zero balances
    net_balance = {uid: bal for uid, bal in net_balance.items() if bal != Decimal('0')}

    if not net_balance:
        # Nothing to simplify — delete any stale debt records.
        with transaction.atomic():
            Debt.objects.filter(group_id=group_id, is_settled=False).delete()
        return Debt.objects.none()

    # Step 3: Separate into creditors and debtors.
    # Python heapq is a min-heap, so we negate values to simulate a max-heap.
    creditors = []  # (-amount, user_id) — max-heap by amount
    debtors = []    # (-amount, user_id) — max-heap by |amount|

    for uid, balance in net_balance.items():
        if balance > Decimal('0'):
            heapq.heappush(creditors, (-balance, str(uid)))
        elif balance < Decimal('0'):
            heapq.heappush(debtors, (balance, str(uid)))  # already negative

    # Step 4: Greedy matching.
    new_debts = []

    # Determine the group's default currency from the most recent expense.
    latest_expense = expenses.order_by('-date', '-created_at').first()
    currency = latest_expense.currency if latest_expense else 'USD'

    while creditors and debtors:
        credit_neg, creditor_id = heapq.heappop(creditors)
        debt_neg, debtor_id = heapq.heappop(debtors)

        credit_amount = -credit_neg  # positive
        debt_amount = -debt_neg      # positive (was stored as negative)

        settle_amount = min(credit_amount, debt_amount)

        new_debts.append(
            Debt(
                group_id=group_id,
                from_user_id=debtor_id,
                to_user_id=creditor_id,
                amount=settle_amount,
                currency=currency,
                is_settled=False,
            )
        )

        remainder_credit = credit_amount - settle_amount
        remainder_debt = debt_amount - settle_amount

        if remainder_credit > Decimal('0'):
            heapq.heappush(creditors, (-remainder_credit, creditor_id))
        if remainder_debt > Decimal('0'):
            heapq.heappush(debtors, (-remainder_debt, debtor_id))

    # Steps 5 & 6: Atomically replace old unsettled debts with new ones.
    with transaction.atomic():
        Debt.objects.filter(group_id=group_id, is_settled=False).delete()
        Debt.objects.bulk_create(new_debts)

    # Step 7: Return the fresh queryset.
    return Debt.objects.filter(
        group_id=group_id,
        is_settled=False,
    ).select_related('from_user', 'to_user', 'group')
