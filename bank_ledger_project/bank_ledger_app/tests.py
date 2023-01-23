from decimal import Decimal
from django.test import TestCase
from .models import Customer, Account, Employee, Ledger
from .tasks import recusive_payment_task
from django_rq import enqueue
from django_rq import get_worker

# Create your tests here.


class BankLedgerAppTests(TestCase):

    # 'setUp' is the required naming convention, do not blame me.
    def setUp(self):
        """Set up function to ensure we have some data to test against

        At the end of setup, we will have have:

        One employee account:
        * employee@work.mail

        Two customer accounts:
        * customerOne@cust.com
        * customerTwo@cust.com

        Two bank accounts for `customerOne`:
        * 'Main Account'
        * 'Savings Account'

        One bank account for `customerTwo`:
        * 'Main Account'
        """

        from django.contrib.auth.models import User

        test_user_emp = User(username="test_employee", password="test_password")
        test_user_emp.save()

        test_emp = Employee(user=test_user_emp, email="employee@work.mail")
        test_emp.save()

        test_user_one = User(username="test_user_one", password="test_password")
        test_user_one.save()

        test_user_two = User(username="test_user_two", password="test_password")
        test_user_two.save()

        test_emp.create_customer(
            customer_email="customerOne@cust.com",
            customer_phone_number="12345678",
            user=test_user_one,
        )
        test_emp.create_customer(
            customer_email="customerTwo@cust.com",
            customer_phone_number="12345678",
            user=test_user_two,
        )
        customer_one = Customer.objects.get(email="customerOne@cust.com")

        test_emp.create_account(
            customer_id=customer_one.customer_id,
            account_name="Savings Account",
        )

    def set_up_two_accounts_and_funds(self):
        # Get customers
        customer_one = Customer.objects.get(email="customerOne@cust.com")
        customer_two = Customer.objects.get(email="customerTwo@cust.com")

        [customer_one_main_account] = Account.objects.filter(
            customer_id=customer_one.customer_id, account_name="Main Account"
        )

        [customer_one_second_account] = Account.objects.filter(
            customer_id=customer_one.customer_id, account_name="Savings Account"
        )

        [customer_two_main_account] = Account.objects.filter(
            customer_id=customer_two.customer_id, account_name="Main Account"
        )

        # 'Cheat' some money into customer one's Main Account by making his Savings go into negative
        # Now customer one's Main Account is at 1000 funds and his Savings is at -1000
        Ledger(
            origin=customer_one_second_account.account_id,
            destination=customer_one_main_account.account_id,
            amount=1000,
            comment="Cheated Money is Bad Money",
        ).save()

        return (
            customer_one,
            customer_two,
            customer_one_main_account,
            customer_two_main_account,
        )

    def test_ledger_balance(self):
        """Tests to ensure that when transactions are created, the ledger `balance()` function counts correctly"""
        customer_one_id = Customer.objects.get(email="customerOne@cust.com").customer_id
        customer_two_id = Customer.objects.get(email="customerTwo@cust.com").customer_id

        # Balance: one: 0 -- two: 0
        account_one = Account.objects.filter(customer_id=customer_one_id)[
            0
        ]  # [0] as this user has 2 accounts
        account_two = Account.objects.get(customer_id=customer_two_id)

        # Balance: one = -1000 -- two = +1000
        Ledger(
            origin=account_one.account_id,
            destination=account_two.account_id,
            amount=1000,
        ).save()
        one_first = Ledger.balance(account_one.account_id)
        two_first = Ledger.balance(account_two.account_id)

        # Balance: one = -500 -- two = +500
        Ledger(
            origin=account_two.account_id,
            destination=account_one.account_id,
            amount=500,
        ).save()
        one_second = Ledger.balance(account_one.account_id)
        two_second = Ledger.balance(account_two.account_id)

        # Balance: one = -299.5 -- Two = +300.5
        Ledger(
            origin=account_two.account_id,
            destination=account_one.account_id,
            amount=200.50,
        ).save()
        one_third = Ledger.balance(account_one.account_id)
        two_third = Ledger.balance(account_two.account_id)

        Ledger(
            origin=account_two.account_id,
            destination=account_one.account_id,
            amount=299.50,
        ).save()
        one_fourth = Ledger.balance(account_one.account_id)
        two_fourth = Ledger.balance(account_two.account_id)

        assert one_first == Decimal(-1000)
        assert two_first == Decimal(1000)

        assert one_second == Decimal(-500)
        assert two_second == Decimal(500)

        assert one_third == Decimal(-299.5)
        assert two_third == Decimal(299.5)

        assert one_fourth == Decimal(0)
        assert two_fourth == Decimal(0)

    def test_account_balance(self):
        """Test to make sure the `Account.balance` property retrieves the correct balance from Ledger"""
        # Balance: one: 0 -- two: 0
        customer_one_id = Customer.objects.get(email="customerOne@cust.com").customer_id
        account_one = Account.objects.filter(customer_id=customer_one_id)[0]
        account_two = Account.objects.filter(customer_id=customer_one_id)[1]
        # Balance: one = -50.25 -- two = +50.25
        Ledger(
            origin=account_one.account_id,
            destination=account_two.account_id,
            amount=50.25,
        ).save()
        balance_one = account_one.balance
        balance_two = account_two.balance

        assert balance_one == Decimal(-50.25)
        assert balance_two == Decimal(50.25)

    def test_ledger_account_history_correct_order(self):
        # Get customer and account data
        customer_one_id = Customer.objects.get(email="customerOne@cust.com").customer_id
        customer_two_id = Customer.objects.get(email="customerTwo@cust.com").customer_id
        [account_one, account_two] = Account.objects.filter(customer_id=customer_one_id)
        [account_three] = Account.objects.filter(customer_id=customer_two_id)

        # Make random transactions to and from account_one
        Ledger(
            origin=account_one.account_id,
            destination=account_two.account_id,
            amount=100,
            comment="first",
        ).save()
        Ledger(
            origin=account_two.account_id,
            destination=account_one.account_id,
            amount=50,
            comment="second",
        ).save()
        Ledger(
            origin=account_one.account_id,
            destination=account_two.account_id,
            amount=200,
            comment="third",
        ).save()
        Ledger(
            origin=account_two.account_id,
            destination=account_one.account_id,
            amount=75,
            comment="fourth",
        ).save()
        Ledger(
            origin=account_three.account_id,
            destination=account_one.account_id,
            amount=500,
            comment="different user account",
        ).save()

        # Retrieve the account history for account_one
        transaction_history = Ledger.history(account_id=account_one.account_id)

        # Assert that the timestamps of these transactions are in the right order
        assert transaction_history[0].timestamp < transaction_history[1].timestamp
        assert transaction_history[1].timestamp < transaction_history[2].timestamp
        assert transaction_history[2].timestamp < transaction_history[3].timestamp
        assert transaction_history[3].timestamp < transaction_history[4].timestamp

    def test_ledger_account_history_no_transactions(self):
        import uuid

        # Generate a random UUID - not in DB
        random_uuid = uuid.uuid4()
        transaction_history = Ledger.history(account_id=random_uuid)

        # Assert that it should be an empty array
        assert transaction_history == []

    def test_account_history_property(self):
        """Test to make sure the `Account.history` property retrieves the correct transaction history from Ledger"""
        # Get a customer ID
        customer_one_id = Customer.objects.get(email="customerOne@cust.com").customer_id
        # Get that customer's two accounts
        [account_one, account_two] = Account.objects.filter(customer_id=customer_one_id)

        # Make one transaction on each
        Ledger(
            origin=account_one.account_id,
            destination=account_two.account_id,
            amount=100,
            comment="first",
        ).save()
        Ledger(
            origin=account_two.account_id,
            destination=account_one.account_id,
            amount=50,
            comment="second",
        ).save()

        # Call the history function on both and check its contents
        account_one_history = account_one.history
        account_two_history = account_two.history

        # Make sure the data is consistent on both accounts
        assert account_one_history[0].amount == 100
        assert account_one_history[0].destination == account_two.account_id
        assert account_two_history[1].amount == 50
        assert account_two_history[1].destination == account_one.account_id

    def test_transfer_funds_method(self):
        # Get a customer ID
        customer_one_id = Customer.objects.get(email="customerOne@cust.com").customer_id
        # Get that customer's two accounts
        [account_one, account_two] = Account.objects.filter(customer_id=customer_one_id)

        # Make a 'cheated' transaction, doing it this way we may send accounts into negative balance
        # For testing only
        # this way, account 2 has 1000 currency to transfer before being unable to
        Ledger(
            origin=account_one.account_id,
            destination=account_two.account_id,
            amount=1000,
            comment="first",
        ).save()

        assert account_two.balance == Decimal(1000)

        # This transfer puts account2 from 1000 -> 400
        # It is valid
        transfer_one = Ledger.transfer_money(
            origin_id=account_two.account_id,
            destination_id=account_one.account_id,
            amount=600.0,
            comment="first transfer",
        )

        assert account_two.balance == 400
        # Check that the return type has the 'ok' key in it
        assert is_ok(transfer_one) == True

        # this transfer would put account2 from 400 -> -100
        # This is not allowed and should be rejected
        transfer_two = Ledger.transfer_money(
            origin_id=account_two.account_id,
            destination_id=account_one.account_id,
            amount=500,
            comment="second transfer",
        )

        assert account_two.balance == 400
        # Check that the return type was has the 'error' key in it
        assert is_err(transfer_two) == True

    def test_customer_transfer_money_same_account(self):
        """Should return an error Dict with `SameAccountError`

        This is because the account origin and destination is the same
        """
        # Get a customer
        customer_one = Customer.objects.get(email="customerOne@cust.com")

        customer_one_main_account = Account.objects.filter(
            customer_id=customer_one.customer_id, account_name="Main Account"
        )

        result = customer_one.transfer_money(
            own_account_id=customer_one_main_account,
            other_account_id=customer_one_main_account,
            amount=Decimal(10.00),
        )

        assert is_err(result) == True
        assert result["error"] == "SameAccountError"

    def test_customer_transfer_money(self):
        """Should successfully transfer money from customerOne to customerTwo"""
        (
            customer_one,
            customer_two,
            customer_one_main_account,  # balance: 1000
            customer_two_main_account,  # balance: 0
        ) = self.set_up_two_accounts_and_funds()

        assert customer_two_main_account.balance == 0
        assert customer_one_main_account.balance == 1000
        result = customer_one.transfer_money(
            own_account_id=str(customer_one_main_account.account_id),
            other_account_id=str(customer_two_main_account.account_id),
            amount=500.0,
        )
        # Assert that the result was a success
        assert is_ok(result) == True
        # Assert that the balance has indeed changed
        assert customer_one_main_account.balance == 500
        assert customer_two_main_account.balance == 500

    def test_customer_transfer_money_insufficient(self):
        """Should fail to transfer money from customerOne to customerTwo due to limited funds"""
        (
            customer_one,
            _,
            customer_one_main_account,  # balance: 1000
            customer_two_main_account,  # balance: 0
        ) = self.set_up_two_accounts_and_funds()

        assert customer_one_main_account.balance == 1000
        assert customer_two_main_account.balance == 0

        # Attempt to send more money than is available on the customer_one_main_account
        result = customer_one.transfer_money(
            own_account_id=customer_one_main_account.account_id,
            other_account_id=customer_two_main_account.account_id,
            amount=1200,
        )

        # Assert that there was indeed an error, and what kind
        assert is_err(result) == True
        assert result["error"] == "InsufficientFunds"
        # Assert that the balance remains unchanged
        assert customer_one_main_account.balance == 1000
        assert customer_two_main_account.balance == 0

    def test_customer_transfer_money_not_own_account(self):
        """Should fail to transfer money as the `own_account_id` is not the customer's own"""
        (
            customer_one,
            customer_two,
            customer_one_main_account,  # balance: 1000
            customer_two_main_account,  # balance: 0
        ) = self.set_up_two_accounts_and_funds()

        assert customer_one_main_account.balance == 1000
        assert customer_two_main_account.balance == 0

        # Attempt to, from customer_one, to send money from customer_two to self
        result = customer_one.transfer_money(
            own_account_id=customer_two_main_account.account_id,
            other_account_id=customer_one_main_account.account_id,
            amount=100,
        )

        # Assert that there was indeed an error, and what kind
        assert is_err(result) == True
        assert result["error"] == "NotOwnAccountError"
        # Assert that the balance remains unchanged
        assert customer_one_main_account.balance == 1000
        assert customer_two_main_account.balance == 0

    def test_bank_details_exists(self):
        bank = Customer.objects.get(pk="40c49b66-8eb1-499b-a914-48f60dd48b7b") or None

        assert bank.email == "bank@bankaccount.bank"
        assert bank.phone_number == "illegal_num"
        assert bank.rank == "Super"

        bank_loan_account = (
            Account.objects.get(pk="5bc6860e-61c2-4427-b9d8-b21c80c8370d") or None
        )

        assert bank_loan_account.account_name == "Bank Loan Account"
        assert bank_loan_account.customer_id == bank.customer_id

    def test_loan_with_wrong_rank(self):
        """Should return an error as the customer is of the 'Base" rank"""
        customer = Customer.objects.get(email="customerOne@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        # Assert that the customer rank is what we expect
        assert customer.rank == "Base"
        # Assert that the customer's account has the balance we expect
        assert customer_account.balance == 0

        # Attempt to loan some money
        response = customer.loan_money(customer_account.account_id, 10_000)

        # Assert that there was indeed an error, and what kind
        assert is_err(response) == True
        assert response["error"] == "WrongAccountRank"

        # Assert that the account balance has not changed
        assert customer_account.balance == 0

        ...

    def test_loan_with_silver_rank(self):
        """Should succeed due to the customer being of the rank: `Silver`"""
        customer = Customer.objects.get(email="customerOne@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        emp = Employee.objects.all()[0]
        result = emp.update_customer_rank(
            customer_id=customer.customer_id, new_rank="Silver"
        )

        customer = Customer.objects.get(email="customerOne@cust.com")

        assert is_ok(result) == True
        # Assert that the customer rank is what we expect
        assert customer.rank.title() == "Silver"
        # Assert that the customer's account has the balance we expect
        assert customer_account.balance == 0

        # Attempt to loan some money, with no comment
        response = customer.loan_money(customer_account.account_id, 10_000)

        # Assert that the operation succeeded
        assert is_ok(response) == True
        # Assert that the account balance has changed
        assert customer_account.balance == 10_000

        # Attempt to loan some more money, with a comment
        response = customer.loan_money(customer_account.account_id, 1000, "For myself")
        # Assert that the account balance has not changed
        assert customer_account.balance == 11_000

    def test_loan_with_gold_rank(self):
        """Should succeed due to the customer being of the rank: `Gold`"""
        customer = Customer.objects.get(email="customerOne@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        emp = Employee.objects.all()[0]
        result = emp.update_customer_rank(
            customer_id=customer.customer_id, new_rank="Gold"
        )

        customer = Customer.objects.get(email="customerOne@cust.com")

        # Assert that the operation succeeded
        assert is_ok(result) == True
        # Assert that the customer rank is what we expect
        assert customer.rank.title() == "Gold"

        # Attempt to loan some money, with comment
        response = customer.loan_money(
            customer_account.account_id, 10000, "I am important"
        )
        # Assert that there was indeed an error, and what kind
        assert is_ok(response) == True

        # Assert that the account balance has changed
        assert customer_account.balance == 10_000

    def test_loan_with_negative_amount(self):
        """Should fail due to the amount being a negative number"""
        customer = Customer.objects.get(email="customerOne@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        result = customer.loan_money(customer_account.account_id, -10_000)

        # Assert that there was indeed an error, and what kind
        assert is_err(result) == True
        # Assert that the error is what we expect
        assert result["error"] == "NegativeNumberError"

        # Attempt to loan some money, with comment
        result = customer.loan_money(customer_account.account_id, 0, "I want nothing")
        # Assert that there was indeed an error, and what kind
        assert is_err(result) == True
        # Assert that the error is what we expect
        assert result["error"] == "NegativeNumberError"

        # Assert that the account balance has not changed
        assert customer_account.balance == 0

    def test_pay_loan_to_bank_with_id(self):
        customer = Customer.objects.get(email="customerTwo@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        # Get the first employee instance
        emp = Employee.objects.all()[0]
        # Update customerTwo to the rank of 'Gold'
        result = emp.update_customer_rank(
            customer_id=customer.customer_id, new_rank="Gold"
        )
        # Retrieve the updated customer stored in the 'ok' key of the dict
        customer = result["ok"]
        # Loan som money
        result = customer.loan_money(customer_account.account_id, 10_000)
        # Retrieve the transaction_id from the result
        transaction_id = result["ok"].transaction_id

        # Check that the ledger has a transaction of 10.000
        assert Ledger.loan_balance(loan_id=transaction_id) == 10_000
        # Assert that the customer's balance is 10.000
        assert customer_account.balance == 10_000
        # Repay 1.000 to the loan of 10.000

        customer.pay_loan(
            own_account_id=str(customer_account.account_id),
            loan_id=str(transaction_id),
            amount=1000,
        )

        # Assert that the loan is now 9.000
        assert Ledger.loan_balance(loan_id=transaction_id) == 9_000
        # Assert that the customer's balance is now 9.000
        assert customer_account.balance == 9_000

    def test_pay_loan_two_loans(self):
        customer = Customer.objects.get(email="customerTwo@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        # Get the first employee instance
        emp = Employee.objects.all()[0]
        # Update customerTwo to the rank of 'Gold'
        result = emp.update_customer_rank(
            customer_id=customer.customer_id, new_rank="Gold"
        )
        # Retrieve the updated customer stored in the 'ok' key of the dict
        customer = result["ok"]

        # Loan 10.000 money
        loan_one_result = customer.loan_money(
            own_account_id=customer_account.account_id,
            amount=10_000,
            comment="House Loan",
        )
        # Grab that transaction's id
        loan_one_id = loan_one_result["ok"].transaction_id

        # Assert that the account balance is 10.000
        assert customer_account.balance == 10_000
        # Assert that the ledger knows that there is a loan of 10.000 on this id
        assert Ledger.loan_balance(loan_one_id) == 10_000

        # Loan an additional 5000 on the same account
        loan_two_result = customer.loan_money(
            own_account_id=customer_account.account_id,
            amount=5_000,
            comment="Pool Party",
        )
        # Grab that transaction's id
        loan_two_id = loan_two_result["ok"].transaction_id

        # Assert that the account now has the total of 15.000
        assert customer_account.balance == 15_000
        # Assert that the ledger knows the balance of both of the loans
        assert Ledger.loan_balance(loan_two_id) == 5_000
        assert Ledger.loan_balance(loan_one_id) == 10_000

        # Pay back loan_one by 1.000 value
        result = customer.pay_loan(customer_account.account_id, loan_one_id, 1_000)

        # Assert that the payment was successful
        assert is_ok(result) == True
        # Assert that the account has 1.000 less
        assert customer_account.balance == 14_000
        # Assert that ledger loan one balance has decreased by 1.000
        assert Ledger.loan_balance(loan_one_id) == 9_000
        # Assert that the ledger loan two has not changed
        assert Ledger.loan_balance(loan_two_id) == 5_000

        result = customer.pay_loan(customer_account.account_id, loan_two_id, 1_000)

        # Assert that the payment was successful
        assert is_ok(result) == True
        # Assert that the account has 1.000 less
        assert customer_account.balance == 13_000
        # Assert that the ledger loan one has not changed
        assert Ledger.loan_balance(loan_one_id) == 9_000
        # Assert that ledger loan two balance has decreased by 1.000
        assert Ledger.loan_balance(loan_two_id) == 4_000

        # Pay loan two off completely
        result = customer.pay_loan(customer_account.account_id, loan_two_id, 4_000)

        # Assert that the payment was successful
        assert is_ok(result) == True
        # Assert that the account has 1.000 less
        assert customer_account.balance == 9_000
        # Assert that the ledger loan one has not changed
        assert Ledger.loan_balance(loan_one_id) == 9_000
        # Assert that ledger loan two balance is now 0
        assert Ledger.loan_balance(loan_two_id) == 0

    def test_pay_loan_too_much_repayment(self):
        customer = Customer.objects.get(email="customerTwo@cust.com")
        [customer_account] = Account.objects.filter(
            customer_id=customer.customer_id, account_name="Main Account"
        )

        # Get the first employee instance
        emp = Employee.objects.all()[0]
        # Update customerTwo to the rank of 'Gold'
        result = emp.update_customer_rank(
            customer_id=customer.customer_id, new_rank="Gold"
        )
        # Retrieve the updated customer stored in the 'ok' key of the dict
        customer = result["ok"]

        # Loan some money
        result = customer.loan_money(customer_account.account_id, 10_000)

        # Get the transaction id from the 'ok' key of the result dict
        transaction_id = result["ok"].transaction_id

        # Attempt to repay more than what was loaned
        result = customer.pay_loan(
            own_account_id=customer_account.account_id,
            loan_id=transaction_id,
            amount=20_000,
        )

        # Assert that there was indeed an error, and what kind
        assert is_err(result) == True
        assert result["error"] == "ExcessRepaymentError"
        # Assert that the customer's balance has not changed due to failed repayment
        assert customer_account.balance == 10_000

    # def test_reccursive_payment(self):
    #     customer = Customer.objects.get(email="customerTwo@cust.com")
    #     [customer_account] = Account.objects.filter(
    #         customer_id=customer.customer_id, account_name="Main Account"
    #     )
    #     # Get the first employee instance
    #     emp = Employee.objects.all()[0]
    #     # Update customerTwo to the rank of 'Gold'
    #     result = emp.update_customer_rank(
    #         customer_id=customer.customer_id, new_rank="Gold"
    #     )
    #     # Retrieve the updated customer stored in the 'ok' key of the dict
    #     customer = result["ok"]

    #     # Loan some money
    #     result = customer.loan_money(customer_account.account_id, 10_000)

    #     # Get the transaction id from the 'ok' key of the result dict
    #     transaction_id = result["ok"].transaction_id

    #     # Create a reccuring payment
    #     result = customer.pay_loan(
    #         own_account_id=customer_account.account_id,
    #         loan_id=transaction_id,
    #         amount=100,
    #         months=2,
    #     )
    #     # Enqueue task
    #     enqueue(recusive_payment_task)

    #     # Get worker to do the task
    #     get_worker().work(burst=True)

    #     assert result["ok"]


def is_err(dictionary: dict) -> bool:
    if dictionary.get("ok") == None:
        return True
    else:
        return False


def is_ok(dictionary: dict) -> bool:
    if dictionary.get("error") == None:
        return True
    else:
        return False
