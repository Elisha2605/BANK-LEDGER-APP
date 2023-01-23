# Create your views here.
from decimal import Decimal
import decimal
import json
import uuid
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.decorators import api_view
from api.models import Transaction, TransferFunds
import requests
from requests.exceptions import InvalidSchema
from django.core.exceptions import ValidationError
from bank_ledger_app.models import Account, Ledger
from bank_ledger_project.settings import OWN_BANK_IP, OTHER_BANK_IP
from django.db.models import Model


class ObjectDecoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, uuid.UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(o)

        if isinstance(o, decimal.Decimal):
            # if the obj is uuid, we simply return the value of uuid
            return str(o)
        # otherwise, encode as normal
        return json.JSONEncoder.default(self, o)


def create_transaction(
    own_account_id: uuid.UUID,
    other_account_id: uuid.UUID,
    transfer_amount: Decimal,
    comment: str or None,
):
    print("create_transaction has been called")
    transaction_object = Transaction(
        own_bank_ip=OWN_BANK_IP,
        other_bank_ip=OTHER_BANK_IP,
        own_account_id=own_account_id,
        other_account_id=other_account_id,
        transfer_amount=transfer_amount,
        comment=comment,
    )
    print("transaction object is: ", transaction_object.__dict__)
    try:
        print("Attempting to clean the transaction object...")
        transaction_object.full_clean()
    except ValidationError as error:
        print("There was a validation error")
        return Response({"error": "ValidationError", "detail": error}, status=400)
    except AttributeError as error:
        print("There was an attribute error")
        return Response({"error": "AttributeError", "detail": error}, status=400)

    body = {
        "transaction_id": str(uuid.uuid4()),
        "own_bank_ip": OWN_BANK_IP,
        "other_bank_ip": OTHER_BANK_IP,
        "own_account_id": str(own_account_id),
        "other_account_id": str(other_account_id),
        "amount": str(transfer_amount),
        "comment": comment,
    }
    print("Body to send: ", body)
    try:
        print("Trying send a post request to transaction broker.")

        json_body = json.dumps(body)
        print("Json Body: ", json_body)
        r = requests.post(
            url="http://nginx/transaction",
            data=json.dumps(body),
            timeout=2,
            headers={"Host": "broker.nginx", "Content-Type": "application/json"},
        )
        print("Response is: ", r)
        data = r.json()
        print("Response in json is: ", data)
    except InvalidSchema as error:
        print("There was an Invalid Schema error.")
        return Response({"error": "InvalidSchema", "detail": error}, status=400)
    except requests.ConnectTimeout as error:
        print("There was a connection timeout.")
        return Response({"error": "ConnectTimeout", "detail": error}, status=500)
    except Exception as err:
        print("UnknownException in create_transaction: ", err)
        return Response({"error": "InternalServerError", "detail": "Something unexpected  went wrong"}, status=500)

    if r.status_code == 200:
        return Response({"ok": data}, status=200)
    else:
        return Response({"error": r.status_code, "detail": data}, status=r.status_code)


# TODO: Prevent external calls
# url: balance/<str:pk>/


@api_view(["GET"])
def get_account_balance_by_id(request, pk):
    if pk is None:
        return Response({"error": "BadRequestError", "detail": "Missing account id"}, status=400)
    try:
        account_found_by_id = Account.objects.get(pk=pk)
    except Exception:
        print("Transaction id was not found, proceeding with null")
        account_found_by_id = None

    if account_found_by_id is None:
        return Response({"error": "NotFoundError", "detail": "Account not found"}, status=404)
    else:
        balance = account_found_by_id.balance
        return Response({"ok": balance})


# TODO: Prevent external calls
# url: transfer-funds/
@api_view(["POST"])
def transfer_funds(request):
    print("Attempting to parse request object...")
    json_request = json.loads(request.data)

    print("Dict of request data: ", json_request)

    transfer_object = TransferFunds(
        transaction_id=json_request.get("transaction_id"),
        origin=json_request.get("origin_id"),
        destination=json_request.get("destination_id"),
        transfer_amount=Decimal(json_request.get("amount")),
        comment=json_request.get("comment"),
        created=json_request.get("created"),
    )
    try:
        print("Validating transfer object...")
        transfer_object.full_clean()
    except ValidationError as error:
        print("ValidationError: ", error)
        return Response({"error": "ValidationError", "detail": error}, status=400)
    except AttributeError as error:
        print("AttributeError: ", error)
        return Response({"error": "AttributeError", "detail": error}, status=400)
    except Exception as err:
        print("UnknownError: ", error)
        return Response({"error": "UnexpectedError", "detail": err}, status=500)

    # CHECK IF TRANSFER ID EXISTS IN LEDGER
    try:
        transaction_by_id = Ledger.objects.get(pk=transfer_object.transaction_id)
    except Exception as error:
        print(f"[INFO]   Ledger entry with id: {transfer_object.transaction_id} was not found. Detail : ", error)
        transaction_by_id = None

    if transaction_by_id is None:
        response = broker_unsafe_transfer(
            transaction_id=transfer_object.transaction_id,
            origin=transfer_object.origin,
            destination=transfer_object.destination,
            amount=transfer_object.transfer_amount,
            comment=transfer_object.comment,
        )
        print("Response data:", response)
        return response
    else:
        new_transfer_funds = {
            "transaction_id": transaction_by_id.transaction_id,
            "origin": transfer_object.origin,
            "destination": transfer_object.destination,
            "transfer_amount": transfer_object.transfer_amount,
            "comment": transfer_object.comment,
        }
        return Response({"ok": new_transfer_funds})


def broker_unsafe_transfer(
    transaction_id: uuid.UUID,
    origin: str,
    destination: str,
    amount: Decimal,
    comment: str = "",
):

    if amount <= 0:
        return Response({
            "error": "NegativeNumberError",
            "detail": f"The amount of money being transferred can not be negative, amount set: {amount}",
        }, status=400)

    try:
        ledger_object = {
            "transaction_id": transaction_id,
            "origin": origin,
            "destination": destination,
            "amount": amount,
            "loan_id": None,
            "comment": comment,
        }
        print("Attempting to save the Ledger transaction with fields: ", ledger_object)
        Ledger.objects.create(
            transaction_id=transaction_id,
            origin=origin,
            destination=destination,
            amount=amount,
            loan_id=None,
            comment=comment,
        )
        print("Transaction saved successfully.")
        ledger_json = json.dumps(ledger_object, cls=ObjectDecoder)
        return Response({"ok": ledger_json})
    except IntegrityError as err:
        print("IntegrityError: ", err)
        return Response({"error":  "IntegrityError", "detail": str(err)}, status=400)
    except Exception as err:
        print("UnknownExceptionError while trying to create Ledger entry: ", err)
        return Response({"error": "UnexpectedError", "detail": err}, status=500)


# TODO: Prevent external calls
# url: transaction/<str:pk>/
@api_view(["DEL"])
def delete_transaction(request, pk):

    [transaction_by_id] = Ledger.objects.filter(pk=pk) or None

    if transaction_by_id is None:
        return Response({"ok": "Transaction does not exist"})
    else:
        try:
            delete_response = transaction_by_id.delete()
            print(delete_response)

            return Response({"ok": "Transaction has been deleted"})
        except Exception as err:
            return Response({"error": "UnknownError", "detail": err}, status=500)
