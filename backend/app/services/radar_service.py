from decimal import Decimal
from datetime import date, timedelta

from app.extensions import db
from app.models.subscription import Subscription
from app.models.invoice import Invoice
from app.models.discount import DiscountRule


RISK_THRESHOLDS = {
    'LOW': 30,
    'MEDIUM': 60,
}


class RevenueRadarService:

    @staticmethod
    def calculate_risk(subscription_id: int) -> dict:
        """
        Evaluate revenue risk for a single subscription.
        Returns a dict conforming to the Radar output spec.
        """
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            return None

        today = date.today()
        score = 0
        reasons = []
        amount_at_risk = Decimal('0')
        related_invoice = None

        # Fetch invoices for this subscription
        invoices = Invoice.query.filter_by(subscription_id=subscription_id).all()
        confirmed_invoices = [i for i in invoices if i.status in ('confirmed', 'paid')]

        # --- R1/R2/R3: Overdue invoices ---
        for inv in invoices:
            if inv.status not in ('confirmed',):
                continue
            if not inv.due_date:
                continue
            days_overdue = (today - inv.due_date).days
            outstanding = Decimal(str(inv.amount_outstanding))
            if days_overdue > 30:
                score += 30
                reasons.append(
                    f'Invoice {inv.invoice_number} is overdue by {days_overdue} days'
                )
                amount_at_risk += outstanding
                related_invoice = inv.invoice_number
            elif days_overdue >= 7:
                score += 20
                reasons.append(
                    f'Invoice {inv.invoice_number} is overdue by {days_overdue} days'
                )
                amount_at_risk += outstanding
                related_invoice = inv.invoice_number
            elif days_overdue >= 1:
                score += 10
                reasons.append(
                    f'Invoice {inv.invoice_number} is {days_overdue} day(s) overdue'
                )
                amount_at_risk += outstanding
                related_invoice = inv.invoice_number

        # --- R4/R5: Subscription expiring soon ---
        if subscription.expiry_date and subscription.status == 'active':
            days_to_expiry = (subscription.expiry_date - today).days
            if 0 <= days_to_expiry <= 7:
                score += 20
                reasons.append(
                    f'Subscription expires in {days_to_expiry} day(s) with no renewal action'
                )
            elif 7 < days_to_expiry <= 30:
                score += 10
                reasons.append(
                    f'Subscription expiring in {days_to_expiry} days'
                )

        # --- R6: Renewal due but no invoice generated ---
        if (subscription.status == 'active'
                and subscription.next_billing_date
                and subscription.next_billing_date <= today):
            # Check if there is a recent draft or confirmed invoice for this period
            recent_inv = Invoice.query.filter_by(
                subscription_id=subscription_id,
                billing_period_start=subscription.next_billing_date,
            ).first()
            if not recent_inv:
                score += 15
                reasons.append(
                    f'Billing date {subscription.next_billing_date} is due but no invoice generated'
                )
                if subscription.total_amount:
                    amount_at_risk += Decimal(str(subscription.total_amount))

        # --- R7/R8: Partially paid invoices ---
        for inv in invoices:
            if inv.status not in ('confirmed',):
                continue
            outstanding = Decimal(str(inv.amount_outstanding))
            if outstanding <= Decimal('0'):
                continue
            amount_paid = Decimal(str(inv.amount_paid))
            if amount_paid > Decimal('0') and outstanding > Decimal('0'):
                # Partially paid
                days_old = (today - inv.created_at.date()).days if inv.created_at else 0
                if days_old > 30:
                    score += 15
                    reasons.append(
                        f'Invoice {inv.invoice_number} partially paid; '
                        f'₹{outstanding:.2f} outstanding for {days_old} days'
                    )
                    amount_at_risk += outstanding
                elif days_old >= 1:
                    score += 10
                    reasons.append(
                        f'Invoice {inv.invoice_number} partially paid; ₹{outstanding:.2f} outstanding'
                    )
                    amount_at_risk += outstanding

        # --- R9: High cumulative outstanding ---
        total_outstanding = sum(
            Decimal(str(i.amount_outstanding))
            for i in invoices if i.status == 'confirmed'
        )
        if total_outstanding > Decimal('10000'):
            score += 10
            reasons.append(
                f'Total outstanding balance is ₹{total_outstanding:.2f} (above ₹10,000 threshold)'
            )
            amount_at_risk = max(amount_at_risk, total_outstanding)

        # --- R10: Duplicate billing detection ---
        period_groups: dict = {}
        for inv in confirmed_invoices:
            key = (inv.billing_period_start, inv.billing_period_end)
            period_groups.setdefault(key, []).append(inv)
        for key, group in period_groups.items():
            if len(group) > 1:
                score += 25
                nums = ', '.join(i.invoice_number for i in group)
                reasons.append(
                    f'Possible duplicate invoices for period {key[0]}–{key[1]}: {nums}'
                )
                break

        # --- R11: Discount expiring soon ---
        discounts = DiscountRule.query.filter_by(is_active=True).all()
        for d in discounts:
            if d.end_date:
                days_left = (d.end_date - today).days
                if 0 <= days_left <= 7:
                    score += 5
                    reasons.append(
                        f'Discount "{d.name}" expires in {days_left} day(s)'
                    )
                    break

        # --- R12: Discount near usage limit ---
        for d in discounts:
            if d.usage_limit and d.usage_limit > 0:
                usage_pct = d.usage_count / d.usage_limit
                if usage_pct >= 0.8:
                    score += 5
                    reasons.append(
                        f'Discount "{d.name}" is at {usage_pct*100:.0f}% of usage limit'
                    )
                    break

        # Cap score
        score = min(score, 100)

        # Determine risk level
        if score >= 60:
            risk_level = 'High'
        elif score >= 30:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'

        # Recommended action
        if risk_level == 'High':
            action = (
                'Immediate attention required. Contact customer, resolve overdue payments, '
                'and ensure renewal is processed.'
            )
        elif risk_level == 'Medium':
            action = (
                'Follow up with customer on outstanding invoices and upcoming renewal. '
                'Consider sending payment reminders.'
            )
        else:
            action = 'Monitor subscription. No immediate action required.'

        if not reasons:
            reasons = ['No significant risk factors detected']

        return {
            'subscription_id': subscription.id,
            'subscription_number': subscription.subscription_number,
            'customer_name': subscription.customer.full_name if subscription.customer else 'Unknown',
            'customer_email': subscription.customer.email if subscription.customer else None,
            'risk_score': score,
            'risk_level': risk_level,
            'reasons': reasons,
            'amount_at_risk': str(amount_at_risk.quantize(Decimal('0.01'))),
            'recommended_action': action,
            'related_invoice': related_invoice,
            'related_subscription': subscription.subscription_number,
            'last_calculated': __import__('datetime').datetime.now(
                __import__('datetime').timezone.utc
            ).isoformat(),
        }

    @classmethod
    def get_all_risks(cls, page=1, per_page=20, risk_level=None):
        """Run radar scoring on all active subscriptions."""
        subscriptions = Subscription.query.filter_by(status='active').all()
        results = []
        for sub in subscriptions:
            result = cls.calculate_risk(sub.id)
            if result:
                if risk_level is None or result['risk_level'] == risk_level:
                    results.append(result)

        # Sort by risk_score descending
        results.sort(key=lambda x: x['risk_score'], reverse=True)

        # Manual pagination
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        items = results[start:end]

        return items, {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
        }

    @classmethod
    def get_summary(cls):
        """Return risk counts by level."""
        subscriptions = Subscription.query.filter_by(status='active').all()
        counts = {'Low': 0, 'Medium': 0, 'High': 0, 'total': 0}
        for sub in subscriptions:
            result = cls.calculate_risk(sub.id)
            if result:
                counts[result['risk_level']] += 1
                counts['total'] += 1
        return counts
