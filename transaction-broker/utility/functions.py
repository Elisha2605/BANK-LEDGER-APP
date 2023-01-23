import uuid
import json
import decimal
from ipaddress import IPv4Address
from uuid import UUID
from fastapi import HTTPException
from models.objects import TransactionPostObject
import requests
from utility.logger import log


def get_account_balance(bank_ip: str, account_id: UUID):
    try:
        response = requests.get(
            url=f"http://nginx/api/balance/{account_id}",
            timeout=1,
            headers={'Host': f"{bank_ip}.nginx", 'Content-Type': 'application/json'},
        )
        log.info(f"Response was: {response}")
    except Exception as error:
        log.error("Error has occurred while trying to get balance!: ", error)
        raise HTTPException(
            status_code=503, detail=f"Bank on host: '{bank_ip}.nginx' did not respond."
        )
    return response


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


def create_transfer(transfer_obj: TransactionPostObject, bank_ip: IPv4Address | str):
    try:
        response = requests.post(
            url=f"http://nginx/api/transfer-funds/",
            json=json.dumps(transfer_obj.__dict__, cls=ObjectDecoder),
            headers={"Host": f"{bank_ip}.nginx", "Content-Type": "application/json"}
        )
        log.debug("create_transfer response as JSON: ", response.json())
    except Exception as err:
        log.error("create_transfer error: ", err)
        raise HTTPException(
            status_code=503, detail=f"Bank on ip: '{bank_ip}' did not respond."
        )
    return {"ok": response.json()}


def delete_transfer(transaction_id: UUID, bank_ip: IPv4Address | str):
    try:
        response = requests.delete(
            url=f"http://nginx/api/transaction/{transaction_id}",
            headers={"Host": f"{bank_ip}.nginx", "Content-Type": "application/json"}
        )
        log.debug("delete_transfer response as JSON: ", response.json())
    except Exception as err:
        print("delete_transfer error: ", err)
        raise HTTPException(
            status_code=503, detail=f"Bank on ip: '{bank_ip}' did not respond."
        )
    return {"ok": response.json()}


def function_with_retries(retries: int, delay: int, function):
    import time

    try:
        result = function()
    except Exception as error:
        print(f"Function {function.__name__} hit an exception! {error}")
        result = {"error": f"Function hit an exception! {error}"}

    if retries > 0:
        if result.get("ok"):
            return result
        if result.get("error"):
            time.sleep(delay)
            return function_with_retries(retries - 1, delay,  function)
    return result
