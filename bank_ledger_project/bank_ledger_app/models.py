from django.contrib.auth.models import User
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.db.models import Q
import uuid

BANK_ID = "40c49b66-8eb1-499b-a914-48f60dd48b7b"
BANK_ACCOUNT_ID = "5bc6860e-61c2-4427-b9d8-b21c80c8370d"


# Similar to an ENUM for keeping track of the Ranks
class CustomerRanks(models.TextChoices):
    BASE = 'Base'
    SILVER = 'Silver'
    GOLD = 'Gold'


# Remember to validate with 'customer'.full_clean()
class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(null=False, unique=True, blank=False)
    rank = models.CharField(max_length=6, choices=CustomerRanks.choices, default=CustomerRanks.BASE)
    phone_number = models.CharField(max_length=15, null=False, blank=False)
    user = models.OneToOneField('auth.User', editable=False, on_delete=models.PROTECT)

    def __str__(self):
        return f"user: {self.user} -- customer_id: ({self.customer_id}) - email: ({self.email}) - rank: ({self.rank}) - phone_number: ({self.phone_number})"


    def _is_own_account_id(self, account_id: uuid.UUID) -> bool:
        """Helper function to see if the provided `account_id` belongs to the `Customer` instance
        """
        own_accounts = Account.objects.filter(customer_id=self.customer_id)

        def check_id(uuid: uuid.UUID) -> bool:
            """Tiny filter function to remove any id's that do not match the one provided
            """
            if str(uuid) == str(account_id):
                return True
            else:
                return False
        result = list(filter(check_id, [str(account.account_id) for account in own_accounts]))

        if len(result) >= 1:
            return True
        else:
            return False

    def transfer_money(self, own_account_id: str, other_account_id: str, amount: Decimal, comment: str = "", loan_id: str = None, months: int = None):
        """Transfer Money from a user's own account to any other existing account.

        This returns an `{"error": "...", "reason": "..."}` dict in the event of any failure other than UUID parsing.

        This will throw an error if the provided UUID is not valid. 
        """
        # If the destination account is the same as the origin return early
        if own_account_id == other_account_id:
            return {"error": "SameAccountError", "detail": f"Attempted to send funds from '{own_account_id}' to '{other_account_id}' but these are the same."}
        
        # Make sure that 'own_account_id' is indeed in the user's account list
        is_own_id = self._is_own_account_id(own_account_id)

        if not is_own_id:
            return {"error": "NotOwnAccountError", "detail": "Not able to transfer money from an account you do not own"}

        # Search all accounts for 'other_account_id' to make sure it exists
        other_account = Account.objects.filter(pk=other_account_id) or None

        if other_account == None:
            return {"error": "NotFoundError", "detail": f"other_account with id: '{other_account_id}' could not be found"}

        result = Ledger.transfer_money(
            origin_id=own_account_id,
            destination_id=other_account_id,
            amount=amount,
            comment=comment,
            loan_id=loan_id,
            months=months
        )
        return result

    @classmethod
    def search(cls, search_intput):
        return cls.objects.filter(
            Q(customer_id__contains=search_intput)     |
            Q(user__username__contains=search_intput)  |
            Q(email__contains=search_intput)           |
            Q(phone_number__contains=search_intput)   
        )[:15]

    def __str__(self):
        return f'{self.customer_id} - {self.email} - {self.phone_number}'

    @property
    def customer_accounts(self):
        accounts = Account.objects.filter(customer_id=self.user.customer)
        accounts_list = []
        for account in accounts:
            accounts_list.append((account.account_id, account.account_name),)
        return accounts_list

    @property
    def accounts(self) -> QuerySet:
        accounts = Account.objects.filter(customer=self.user.customer)

        return accounts

    @property
    def all_accounts(self) -> list['Account']:
        accounts = Account.objects.all().filter(customer_id=self.customer_id)
        return list(accounts)

    @property
    def loans(self) -> list[dict]:
        accounts = self.all_accounts
        history = []
        for account in accounts:
            account_id = account.account_id

            loans = Ledger.objects.all().filter(destination=account_id, loan_id=None, origin=BANK_ACCOUNT_ID)
            for loan in loans:
                history_list = {"loan_id": loan.transaction_id,
                                "amount": loan.amount, "date": loan.timestamp,
                                "comment": loan.comment,
                                "current_balance": loan.loan_balance(loan.transaction_id),
                                "from_account": account_id,
                                "repayments": []
                                }

                history_list["repayments"] = [{"date": transaction.timestamp, "amount": transaction.amount, "from_account": account_id}
                                              for transaction in Ledger.objects.filter(loan_id=loan.transaction_id)]
                history.append(history_list)
        return history

    def loan_money(self, own_account_id: str, amount: Decimal, comment: str = "Default"):
        if amount <= 0:
            return {"error": "NegativeNumberError", "detail": f"The amount of money being transferred can not be negative or 0, amount set: {amount}"}

        if self.rank == "Silver" or self.rank == "Gold":
            if self._is_own_account_id(own_account_id):
                try:
                    entry = Ledger.objects.create(
                        origin=Account.objects.get(account_id=BANK_ACCOUNT_ID).account_id,
                        destination=Account.objects.get(account_id=own_account_id).account_id,
                        amount=amount,
                        comment=f"Bank Loan-({comment})"
                    )
                except Exception as error:
                    return {"error": "UnknownError", "detail": error}
                return {"ok": entry}
            else:
                return {"error": "NotOwnAccountError", "detail": "Not able to transfer a loan to an account you do not own"}

        else:
            return {"error": "WrongAccountRank",
                    "detail": f"Only customers with the rank of 'Silver' or 'Gold' may make loans. This Customer has the rank of: {self.rank}"}

    def pay_loan(self, own_account_id: str, loan_id: str, amount: Decimal, months: int = None):
        if amount <= 0:
            return {"error": "NegativeNumberError", "detail": f"The amount of money being transferred can not be negative or 0, amount set: {amount}"}
        if self._is_own_account_id(own_account_id):
            account_history = Account.objects.get(account_id=own_account_id).history
            # Find all transactions from bank
            is_loan = True if len([transaction for transaction in account_history if str(transaction.transaction_id) == str(loan_id)]) >= 1 else False

            if not is_loan:
                return {"error": "InvalidLoan", "detail": f"Loan ID of {loan_id} was not found in the customers transaction history"}

            loan_balance = Ledger.loan_balance(loan_id=loan_id)

            if loan_balance < amount:
                return {"error": "ExcessRepaymentError", "detail": f"The outstanding loan is of value: {loan_balance} and the customer attempted to repay: {amount}"}

            result = self.transfer_money(
                own_account_id=own_account_id,
                other_account_id=BANK_ACCOUNT_ID,
                amount=amount,
                loan_id=loan_id,
                comment="Loan Repayment",
                months=months
            )
            return result
        else:
            return {"error": "NotOwnAccountError", "detail": "Not able to repay a loan from an account you do not own"}


class Account(models.Model):
    account_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    account_name = models.CharField(
        max_length=30,
        default="Main Account",
        null=False,
        blank=False
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)


    def __str__(self):
        # return f"account_id: ({self.account_id}) - account_name: ({self.account_name}) - customer: ({self.customer})"
        return f"{self.account_name} - {self.balance} kr"


    @property
    def balance(self) -> Decimal:
        balance = Ledger.balance(self.account_id)
        return balance

    @property
    def history(self) -> list['Ledger']:
        account_history = Ledger.history(self.account_id)
        # Retrieve all transactions to and from this account
        # Figure out the best way to return this information
        return account_history


class Employee(models.Model):
    employee_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(null=False, unique=True, blank=False)
    user = models.OneToOneField('auth.User', editable=False, on_delete=models.PROTECT)

    def __str__(self):
        return f"user: ({self.user}) - employee_id: ({self.employee_id}) - email: ({self.email})"

    def create_customer(self, customer_email: str, customer_phone_number: str, user=User):
        """Creates a new customer with `customer_email` and `customer_phone_number`

        Creates a new Customer and a default Account for it named 'Main Account', and assigns it to the 
        provided `user` object
        """

        # Start transaction, this ensures that a new user is created together
        # with a new default account.
        try:
            with transaction.atomic():
                new_customer = Customer(email=customer_email, phone_number=customer_phone_number, user=user)
                # Validate that customer has all the right fields
                new_customer.full_clean()
                # Save the customer in the DB. This must be done before we can make
                # a new account and bind it to this ID.
                new_customer.save()

                new_customer_account = Account(customer=new_customer)

                new_customer_account.full_clean()

                new_customer_account.save()

                return {"new_customer": new_customer, "new_account": new_customer_account}
        except ValidationError as error:
            return {"error": "ValidationError", "detail": error}

    def create_account(self, customer_id: str, account_name: str):

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return {"error": "NotFound", "detail": f"Customer of id '{customer_id}' not found!"}

        new_account = Account(account_name=account_name, customer=customer)

        # Validate constraints
        new_account.full_clean()

        new_account.save()
        return {"ok": new_account}

    def update_customer_rank(self, customer_id: str, new_rank: str):
        [customer] = Customer.objects.filter(pk=customer_id) or None

        if customer == None:
            return {"error": "NotFoundError", "detail": f"Customer of id: {customer_id} not found"}

        rank_found = 0
        for rank in CustomerRanks:
            if rank.title().lower() == new_rank.lower():
                customer.rank = rank
                rank_found = 1

        if rank_found != 1:
            return {"error": "NotFoundError", "detail": f"CustomerRank '{new_rank}' does not exist!"}
        else:
            customer.save()
            return {"ok": customer}


class Ledger(models.Model):
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origin = models.UUIDField(null=False)
    destination = models.UUIDField(null=False)
    loan_id = models.ForeignKey('Ledger', on_delete=models.PROTECT, editable=False, null=True, default=None)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.CharField(max_length=254, blank=True, null=True)
    months = models.IntegerField(default=None, null=True, blank=True)

    def __str__(self):
        # The transaction from a bank to a customer will never have the loan_id attribute set
        # This throws an exception when attempting to print it as it is basically `self.None.transaction_id`
        # This is a simple workaround where we try to set temp_transaction_id to the correct value
        # But if it fails (due to being set to None) we represent it as string of null instead
        try:
            temp_transaction_id = self.loan_id.transaction_id
        except AttributeError:
            temp_transaction_id = "null"

        return f"transaction_id: ({self.transaction_id}) - origin_id: ({self.origin}) - destination_id: ({self.destination})- loan_id: {temp_transaction_id} - amount: ({self.amount}) - timestamp: ({self.timestamp}) - comment: ({self.comment})"

    @classmethod
    def history(cls, account_id: str) -> list['Ledger']:
        """Returns a list of all transactions to and from `account_id`

        If none are found an empty list is returned instead

        Throws `ValueError` if the passed `account_id` is not a valid uuid
        """
        from django.db.models import Q
        # Get ALL transactions
        all_movements = cls.objects.all()

        # Filter only the transactions that contain the given `account_id` in both directions
        # then sort by timestamp
        #
        # The Q is needed to do both requests in one query: (query1 | query 2)
        all_account_movements = sorted(all_movements.filter(Q(destination=account_id) | Q(origin=account_id)),
                                       key=lambda x: x.timestamp)

        return all_account_movements

    @classmethod
    def balance(cls, account_id: str) -> Decimal:
        # Get ALL transactions
        all_movements = cls.objects.all()

        # Filter the transaction lits for transactions going into the account
        incoming_transactions = all_movements.filter(destination=account_id)
        # Filter the transaction list for transactions leaving the account
        outgoing_transactions = all_movements.filter(origin=account_id)

        # Iterate the individual lists for the amounts, collect them all and sum the totals
        total_arriving_in_account = sum([transaction.amount for transaction in incoming_transactions])
        total_leaving_account = sum([transaction.amount for transaction in outgoing_transactions])

        # Minus the arriving from the total (as all accounts start with 0 this is safe to do)
        balance = total_arriving_in_account - total_leaving_account

        return Decimal(balance)

    @classmethod
    def loan_balance(cls, loan_id: str) -> Decimal:
        all_repayments = Ledger.objects.filter(loan_id=loan_id)
        total_loaned = Ledger.objects.get(transaction_id=loan_id).amount
        total_returned = sum([transaction.amount for transaction in all_repayments])

        loan_balance = total_loaned - total_returned

        return Decimal(loan_balance)

    @classmethod
    def transfer_money(cls, origin_id: str, destination_id: str, amount: Decimal, comment: str = "", loan_id: str = None, months: int = None):
        if amount < 0:
            return {"error": "NegativeNumberError", "detail": f"The amount of money being transferred can not be negative, amount set: {amount}"}

        [origin] = Account.objects.filter(account_id=origin_id) or None
        [destination] = Account.objects.filter(account_id=destination_id) or None

        if origin == None or destination == None:
            problem_child = origin_id if origin == None else destination_id
            return {"error": "AccountNotFoundError", "detail": f"Could not find account: {problem_child}"}

        origin_balance = origin.balance
        if origin_balance < amount:
            return {"error": "InsufficientFunds",
                    "detail": f"Origin account has: '{origin_balance}' but attempted to transfer: '{amount}'"
                    }

        if loan_id != None:
            loan_id = cls.objects.get(transaction_id=loan_id)
        try:
            transfer = cls.objects.create(origin=origin_id, destination=destination_id,amount=amount, comment=comment, loan_id=loan_id, months=months)
            return {"ok": transfer}

        except ValueError as error:
            return {"error": "ValueError", "detail": error}

    @classmethod
    def broker_delete_transaction(cls, transaction_id: uuid):

        transaction = Ledger.objects.filter(transaction_id=transaction_id) or None

        if transaction:
            result = transaction.delete()
            return {"ok": result}
        else:
            return {"error": "DoesNotExistError", "detail": f"The Ledger entry with the id {transaction_id} does not exist"}
