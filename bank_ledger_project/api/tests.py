from django.test import TestCase

from api.views import create_transaction
from .models import Transaction
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from bank_ledger_app.models import Ledger
from bank_ledger_project.settings import OWN_BANK_IP, OTHER_BANK_IP
import os
from bank_ledger_app.models import Account


TRANS_ID = "8d2687bd-3e96-47c4-ab88-d8221b7eb80d"

OWN_ACCOUNT_ID = "5bc6860e-61c2-4427-b9d8-b21c80c8370d"
OTHER_ACCOUNT_ID = "1f4bc043-804c-4a77-b3dc-a9ac499f562b"

# Create your tests here.
class ApiTests(TestCase):
    def setUp(self):
        ...

    def test_create_transaction(self):

        transObj = Transaction(
            own_bank_ip="192.158.1.38",
            other_bank_ip="192.158.1.39",
            own_account_id="08ebc7e5-e728-45f2-b202-7eed7f2be73d",
            other_account_id="a1feaac2-9101-4ca0-8fc8-65219049985d",
            transfer_amount="100",
            comment="Here is a lil comment yay",
        )

        try:
            transObj.full_clean()
            assert True
        except ValidationError as error:
            print('-\n', error)
            assert False


# class ApiTestsOptimized(APITestCase):
#     def setUp(self):
#         ledgerObj = Ledger(
#             transaction_id=TRANS_ID,
#             origin_id=OWN_ACCOUNT_ID,
#             destination="bcabae70-d0c6-45f8-9113-09c898a80a63",
#             amount="2",
#             comment="s",
#         )
#         ledgerObj.save()

#     def test_create_transaction(self):
#         transaction = {
#             "own_bank_ip": OWN_BANK_IP,
#             "other_bank_ip": OTHER_BANK_IP,
#             "own_account_id": OWN_ACCOUNT_ID,
#             "other_account_id": OTHER_ACCOUNT_ID,
#             "transfer_amount": "20",
#             "comment": "woop",
#         }
#         account = Account.objects.get(pk=OWN_ACCOUNT_ID)
#         print("BANK BALANCE IS: ", account.balance)
#         result = create_transaction(
#             own_account_id=transaction["own_account_id"],
#             other_account_id=transaction["other_account_id"],
#             transfer_amount=transaction["transfer_amount"],
#             comment=transaction["comment"],
#         )
#         print("BANK BALANCE IS: ", account.balance)
#         print("Result", result)
#         print("Result DATA IS ", result.data)
#         assert 1 == 2

#          # self.client.post("http://127.0.0.1:8000/api/create-transaction/", transaction)

#     def test_delete_transaction(self):
#         self.client.post(
#             "http://127.0.0.1:8000/api/transaction/" + TRANS_ID, {"data": "lmao"}
#         )
