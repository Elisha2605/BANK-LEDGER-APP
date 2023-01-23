#!/bin/env python3
from config.secrets import get_env, validate_envs
from fastapi.middleware.cors import CORSMiddleware
from models.objects import TransactionPostObject, TransactionRequestObject
from utility.logger import log
from utility.functions import (
    create_transfer,
    delete_transfer,
    function_with_retries,
    get_account_balance,
)
from fastapi import FastAPI, Response, HTTPException
import uvicorn
from uuid import uuid4
from requests.models import Response as Res
from ipaddress import ip_address

server = FastAPI()
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@server.get("/balance")
def temp():
    import decimal

    return {"balance": decimal.Decimal(100.00)}


@server.post("/transaction")
async def incoming_transaction(payload: TransactionRequestObject):
    log.info(f"Received a request on /transaction with the payload: {payload}")

    # Validate amount
    if payload.amount <= 0:
        log.warn(
            f"'amount' attribute can not be negative, amount received: {payload.amount}"
        )
        raise HTTPException(
            status_code=422,
            detail=f"'amount' attribute can not be negative, amount received: {payload.amount}",
        )

    # Get both account balances, this ensures that both banks are online and both accounts exist
    own_balance: Res = get_account_balance(payload.own_bank_ip, payload.own_account_id)
    other_balance: Res = get_account_balance(payload.other_bank_ip, payload.other_account_id)

    log.debug(f"Balance One: {own_balance}")
    log.debug(f"Balance Two: {other_balance}")

    if own_balance.status_code != 200 or own_balance.json().get("error") or other_balance.status_code != 200 or other_balance.json().get("error"):
        problem = (
            f"{payload.own_account_id}"
            if own_balance.status_code != 200
            else f"{payload.other_account_id}"
        )
        raise HTTPException(
            status_code=400, detail=f"Bank account '{problem}' was not found."
        )

    log.info(f"Own balance is: {own_balance.json()['ok']}")
    log.info(f"Other balance is: {other_balance.json()['ok']}")
    # Validate that the sender has enough balance to make the transfer
    if own_balance.json()["ok"] < payload.amount:
        raise HTTPException(
            status_code=409,
            detail=f"Bank account '{payload.own_account_id}' as insufficient funds: '{own_balance.json()['ok']}' to send: '{payload.amount}' currency",
        )
    

    # Create a transaction object to send to the banks
    transaction_obj = TransactionPostObject(
        transaction_id=payload.transaction_id,
        amount=payload.amount,
        origin_id=payload.own_account_id,
        destination_id=payload.other_account_id,
        comment=payload.comment,
    )
    transaction_result_one: dict["str", "str"]
    transaction_result_two: dict["str", "str"]

    # Flag for failed transaction
    transaction_failed = False

    # Attempt to make the transaction on both banks
    # will try to do it 3 times, then consider it failed if no replies
    transaction_result_one = function_with_retries(
        delay=2,
        retries=3,
        function=lambda: create_transfer(
            transfer_obj=transaction_obj, bank_ip=payload.own_bank_ip
        ),
    )
    transaction_result_two = function_with_retries(
        delay=2,
        retries=3,
        function=lambda: create_transfer(
            transfer_obj=transaction_obj, bank_ip=payload.other_bank_ip
        ),
    )
    if transaction_result_one.get("error") or transaction_result_two.get("error"):
        # TODO: figure out how to reply before doing this...
        print("A transaction has failed, undoing...")

        # send delete request with the transaction_id to both banks
        # Does nothing if not found, deletes if it does exist
        transaction_failed = True
        result_one = function_with_retries(
            delay=5,
            retries=5,
            function=lambda: delete_transfer(
                payload.transaction_id, bank_ip=payload.own_bank_ip
            ),
        )  # total time = 25 seconds
        result_two = function_with_retries(
            delay=5,
            retries=5,
            function=lambda: delete_transfer(
                payload.transaction_id, bank_ip=payload.other_bank_ip
            ),
        )  # total time = 25 seconds

        print(result_one)  # TODO: do something with this.
        print(result_two)  # TODO: do something with this.

    if transaction_failed:  # TODO: find out how to do this sooner.
        raise HTTPException(
            status_code=503,
            detail=f"One or more banks are unavailable right now, transaction has been cancelled, and any pending transaction have been deleted.",
        )

    # TODO: parse responses for correctness
    print("Transaction One: ", transaction_result_one)
    print("Transaction Two: ", transaction_result_two)

    return {
        "status": "success",
        "transactions": [transaction_result_one, transaction_result_two],
    }


if __name__ == "__main__":
    validate_envs().data()
    port = int(get_env("BROKER_PORT"))
    host = get_env("BROKER_HOST")
    will_reload = bool(int(get_env("RELOAD_UVICORN")))
    log.info(f"Server will run on port '{port}'. Autoreload enabled?: '{will_reload}'.")

    uvicorn.run(
        "main:server",
        port=port,
        host=host,
        reload=will_reload,
        headers=[("ContentType", "application/json")],
    )
