from .models import Account, Ledger
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from decimal import *
from django_rq import job

BANK_ACCOUNT_ID = "5bc6860e-61c2-4427-b9d8-b21c80c8370d"

@job
def add_late_fee_task():
    all_loans = Ledger.objects.filter(origin_id=BANK_ACCOUNT_ID)
    for ledger in all_loans:
        if (ledger.timestamp + relativedelta(years=1) <= timezone.now() and ledger.loan_balance(ledger.transaction_id) != 0):
            customer = Account.objects.get(account_id=ledger.destination).customer
            fee = 0
            if (customer.rank == "Base"):
                fee = 100
            elif (customer.rank == "Silver"):
                fee = 75
            else:
                fee = 50
            Ledger.objects.create(
                origin=ledger.destination,
                destination=Account.objects.get(pk=BANK_ACCOUNT_ID),
                amount=fee,
                comment='Late fee for loan: ' + str(ledger.transaction_id)
            )
            print("Late fee added for user " + customer.email + " for loan: " + str(ledger.transaction_id) )

@job
def add_interest_task():
    all_loans = Ledger.objects.filter(origin_id=BANK_ACCOUNT_ID)
    for ledger in all_loans:
        if (ledger.timestamp + relativedelta(years=1) <= timezone.now() and ledger.loan_balance(ledger.transaction_id) != 0):
            customer = Account.objects.get(account_id=ledger.destination).customer
            interest:Decimal = 0.0
            if (customer.rank == "Base"):
                interest = 0.05
            elif (customer.rank == "Silver"):
                interest = 0.04
            else:
                interest = 0.03
            Ledger.objects.create(
                destination=Account.objects.get(pk=BANK_ACCOUNT_ID),
                origin=ledger.destination,
                amount=ledger.loan_balance(ledger.transaction_id) * Decimal(interest),
                comment='Interest for loan: ' + str(ledger.transaction_id)
            )
            print("Interest added for user " + customer.email + " for loan: " + str(ledger.transaction_id) )

@job
def recusive_payment_task():
    all_payments = Ledger.objects.all().exclude(months=0).exclude(months=None)
    for ledger in all_payments:
        if (ledger.months == 0 or ledger.months == None or ledger.amount == 0 or ledger.amount == None or Account.objects.get(pk=ledger.origin).balance < ledger.amount):
            continue
        try:
            Ledger.objects.create(
                origin=ledger.origin,
                destination=ledger.destination,
                amount=ledger.amount,
                comment=ledger.comment,
                loan_id=ledger.loan_id
            )
            ledger.months = ledger.months - 1
            ledger.save()
            print("Payment created for account " + Account.objects.get(pk=ledger.origin).account_name+ " for transaction: " + str(ledger.transaction_id) )
        except Exception as e:
            print("Payment failed for account " + Account.objects.get(pk=ledger.origin).account_name+ " for transaction: " + str(ledger.transaction_id) )
            print("ERROR ", e)
            continue

