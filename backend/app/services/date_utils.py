from datetime import date, timedelta
import calendar


def advance_billing_date(current_date: date, frequency: str) -> date:
    """
    Advance a date by one billing period.
    - daily: +1 day
    - weekly: +7 days
    - monthly: +1 calendar month, end-of-month adjusted
    - yearly: +1 year, leap-year adjusted
    """
    if frequency == 'daily':
        return current_date + timedelta(days=1)
    elif frequency == 'weekly':
        return current_date + timedelta(days=7)
    elif frequency == 'monthly':
        month = current_date.month + 1
        year = current_date.year
        if month > 12:
            month = 1
            year += 1
        last_day = calendar.monthrange(year, month)[1]
        day = min(current_date.day, last_day)
        return date(year, month, day)
    elif frequency == 'yearly':
        year = current_date.year + 1
        last_day = calendar.monthrange(year, current_date.month)[1]
        day = min(current_date.day, last_day)
        return date(year, current_date.month, day)
    else:
        raise ValueError(f'Unknown billing frequency: {frequency}')


def billing_period_end(start_date: date, frequency: str) -> date:
    """Return the last day of the billing period that starts on start_date."""
    next_start = advance_billing_date(start_date, frequency)
    return next_start - timedelta(days=1)


def payment_due_date(invoice_date: date, payment_terms: str) -> date:
    """Calculate invoice due date based on payment terms."""
    terms_map = {
        'immediate': 0,
        'net_15': 15,
        'net_30': 30,
        'net_45': 45,
    }
    days = terms_map.get(payment_terms, 0)
    return invoice_date + timedelta(days=days)
