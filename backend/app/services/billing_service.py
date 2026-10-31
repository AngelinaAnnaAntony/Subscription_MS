from decimal import Decimal
from datetime import date, datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.subscription import Subscription, SubscriptionLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.discount import DiscountRule
from app.services.date_utils import advance_billing_date, billing_period_end, payment_due_date


class BillingService:

    @staticmethod
    def _generate_invoice_number():
        year = date.today().year
        count = Invoice.query.filter(
            db.extract('year', Invoice.created_at) == year
        ).count() + 1
        return f'INV-{year}-{count:04d}'

    @staticmethod
    def _calculate_discount(subtotal: Decimal, subscription: Subscription) -> Decimal:
        """Find the best applicable discount and return the discount amount."""
        today = date.today()
        discounts = DiscountRule.query.filter_by(is_active=True).all()
        best_discount = Decimal('0')

        for d in discounts:
            if not d.is_valid:
                continue
            if d.min_purchase and subtotal < d.min_purchase:
                continue
            # Calculate this discount's value
            if d.discount_type == 'percentage':
                amount = subtotal * (d.value / Decimal('100'))
            else:  # fixed
                amount = d.value

            amount = min(amount, subtotal)  # cannot exceed subtotal
            if amount > best_discount:
                best_discount = amount

        return best_discount

    @classmethod
    def generate_invoice_for_subscription(cls, subscription_id: int):
        """
        Generate a draft invoice for the given subscription.
        Returns (invoice, error_message).
        Uses a DB transaction; rolls back on any error.
        """
        try:
            subscription = Subscription.query.get(subscription_id)
            if not subscription:
                return None, 'Subscription not found'

            if subscription.status != 'active':
                return None, f'Subscription is not active (status: {subscription.status})'

            today = date.today()
            if subscription.next_billing_date is None:
                return None, 'Subscription has no next billing date set'

            if subscription.next_billing_date > today:
                return None, (
                    f'Next billing date {subscription.next_billing_date} is in the future'
                )

            period_start = subscription.next_billing_date
            period_end = billing_period_end(period_start, subscription.plan.billing_frequency)

            # Duplicate check
            existing = Invoice.query.filter_by(
                subscription_id=subscription_id,
                billing_period_start=period_start,
                billing_period_end=period_end,
            ).first()
            if existing:
                return None, (
                    f'Invoice already exists for this period: {existing.invoice_number}'
                )

            # Build invoice lines from subscription lines
            lines = subscription.lines.all()
            if not lines:
                return None, 'Subscription has no lines; cannot generate invoice'

            subtotal = Decimal('0')
            tax_total = Decimal('0')
            invoice_lines = []

            for sl in lines:
                qty = Decimal(str(sl.quantity))
                unit_price = Decimal(str(sl.unit_price))
                tax_rate = Decimal(str(sl.tax_rate))
                line_subtotal = qty * unit_price
                line_tax = (line_subtotal * tax_rate / Decimal('100')).quantize(Decimal('0.01'))
                line_total = line_subtotal + line_tax

                subtotal += line_subtotal
                tax_total += line_tax

                invoice_lines.append(InvoiceLine(
                    product_id=sl.product_id,
                    variant_id=sl.variant_id,
                    description=sl.description or (sl.product.name if sl.product else 'Service'),
                    quantity=sl.quantity,
                    unit_price=sl.unit_price,
                    tax_rate=sl.tax_rate,
                    tax_amount=line_tax,
                    discount_amount=Decimal('0'),
                    line_total=line_total,
                ))

            # Apply discount
            discount_amount = cls._calculate_discount(subtotal, subscription)
            total_amount = (subtotal + tax_total - discount_amount).quantize(Decimal('0.01'))
            if total_amount < Decimal('0'):
                total_amount = Decimal('0')

            due = payment_due_date(today, subscription.payment_terms)

            invoice = Invoice(
                invoice_number=cls._generate_invoice_number(),
                subscription_id=subscription_id,
                customer_id=subscription.customer_id,
                billing_period_start=period_start,
                billing_period_end=period_end,
                status='draft',
                due_date=due,
                subtotal=subtotal.quantize(Decimal('0.01')),
                tax_amount=tax_total.quantize(Decimal('0.01')),
                discount_amount=discount_amount.quantize(Decimal('0.01')),
                total_amount=total_amount,
                amount_paid=Decimal('0'),
                amount_outstanding=total_amount,
            )
            db.session.add(invoice)
            db.session.flush()  # get invoice.id

            for il in invoice_lines:
                il.invoice_id = invoice.id
                db.session.add(il)

            # Advance next_billing_date
            subscription.next_billing_date = advance_billing_date(
                period_start, subscription.plan.billing_frequency
            )

            db.session.commit()
            return invoice, None

        except IntegrityError:
            db.session.rollback()
            return None, 'Duplicate invoice detected for this billing period'
        except Exception as e:
            db.session.rollback()
            return None, f'Invoice generation failed: {str(e)}'

    @classmethod
    def generate_all_due_invoices(cls):
        """Generate invoices for all active subscriptions due today or overdue."""
        today = date.today()
        due_subscriptions = Subscription.query.filter(
            Subscription.status == 'active',
            Subscription.next_billing_date <= today,
        ).all()

        generated = []
        errors = []

        for sub in due_subscriptions:
            invoice, error = cls.generate_invoice_for_subscription(sub.id)
            if invoice:
                generated.append(invoice.to_dict())
            else:
                errors.append({'subscription_id': sub.id,
                               'subscription_number': sub.subscription_number,
                               'error': error})

        return generated, errors
