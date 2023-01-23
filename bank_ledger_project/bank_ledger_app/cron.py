from .models import Employee, Customer, Account, CustomerRanks, Ledger
from django.utils import timezone
import datetime
from dateutil.relativedelta import relativedelta
from decimal import *
from .tasks import add_late_fee_task, add_interest_task, recusive_payment_task
import django_rq

BANK_ACCOUNT_ID = "5bc6860e-61c2-4427-b9d8-b21c80c8370d"


def add_late_fee():
    django_rq.enqueue(add_late_fee_task)


def add_interest():
    django_rq.enqueue(add_interest_task)


def recusive_payment():
    django_rq.enqueue(recusive_payment_task)
