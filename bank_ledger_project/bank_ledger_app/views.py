from secrets import token_urlsafe
from django.shortcuts import render, reverse, redirect
from django.contrib.auth.models import User
from .models import Employee, Customer, Account
from .forms import (
    CreateCustomerForm,
    UpdateCustomerRankForm,
    CreateAccountForm,
    LoanForm,
    OwnTransferForm,
    OtherTransferForm,
    PayLoanForm,
    CreateUserForm,
    CreateEmployeeForm,
)
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from api.views import create_transaction


def has_customer_obj(request):
    try:
        request.user.customer
        return True
    except AttributeError:
        return False


def index(request):
    if request.user.is_superuser:
        return redirect("bank_ledger_app:create-employee")
    elif request.user.is_staff:
        return redirect("bank_ledger_app:customer-list-info")
    elif has_customer_obj(request):
        customer = request.user.customer
        return redirect("bank_ledger_app:profile-info", customer.pk)
    else:
        return redirect("two_factor:login")


###################################################
#                 CUSTOMER
###################################################
def profile_info(request, pk):
    customer = request.user.customer
    accounts = customer.all_accounts
    loans = customer.loans
    context = {
        "customer": customer,
        "accounts": accounts,
        "customer_id": pk,
        "loans": loans,
    }
    return render(request, "bank_ledger_app/customer/profile-info.html", context)


def account_info(request, pk):
    account = Account.objects.get(account_id=pk)
    account_history = account.history
    context = {"account": account, "account_history": account_history}
    return render(request, "bank_ledger_app/customer/account-info.html", context)


def loan_info(request, pk):
    loan_id = pk
    customer = request.user.customer
    customer_loans = customer.loans
    account = Account.objects.filter(customer_id=customer)
    loan_details = []
    repayments = []
    for loan in customer_loans:
        if str(loan["loan_id"]) == pk:
            loan_details.append(loan)
        for repayment in loan["repayments"]:
            repayments.append(repayment)

    context = {
        "loan_id": loan_id,
        "account_id": account,
        "loan": customer_loans,
        "loan_details": loan_details,
        "repayments": repayments,
    }
    return render(request, "bank_ledger_app/customer/loan-info.html", context)


def loan(request):
    customer: Customer = request.user.customer
    if request.method == "POST":
        form = LoanForm(request.POST)
        form.fields["account"].queryset = customer.accounts
        if form.is_valid():
            account = form.cleaned_data["account"].pk
            amount = form.cleaned_data["amount"]
            comment = form.cleaned_data["comment"]
            try:
                loan = customer.loan_money(account, amount, comment)
                if not loan.get("ok"):
                    context = {
                        "title": loan.get("title"),
                        "description": loan.get("detail"),
                    }
                    return render(
                        request, "bank_ledger_app/customer/errors.html", context
                    )
                return redirect("bank_ledger_app:profile-info", customer.pk)
            except Exception as e:
                print(e)
                return
    else:
        form = LoanForm()
    form.fields["account"].queryset = customer.accounts
    context = {
        "loan_form": form,
    }
    return render(request, "bank_ledger_app/customer/loan.html", context)


def pay_loan_partial(request, pk):
    customer: Customer = request.user.customer
    customer_loans = customer.loans
    loan_details = []
    for loan in customer_loans:
        if str(loan["loan_id"]) == pk:
            loan_details.append(loan)

    for loan_id in loan_details:
        own_account_id = loan_id["from_account"]

    form = PayLoanForm(request.POST)
    if request.method == "POST":
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            try:
                if form.cleaned_data["recurring_payment"] == False:
                    loan = customer.pay_loan(own_account_id, pk, amount)
                    if not loan.get("ok"):
                        context = {
                            "title": loan.get("title"),
                            "description": loan.get("detail"),
                        }
                        return render(
                            request, "bank_ledger_app/customer/errors.html", context
                        )
                    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
                else:
                    loan = customer.pay_loan(
                        own_account_id, pk, amount, form.cleaned_data["how_many_months"]
                    )
                    if not loan.get("ok"):
                        context = {
                            "title": loan.get("title"),
                            "description": loan.get("detail"),
                        }
                        return render(
                            request, "bank_ledger_app/customer/errors.html", context
                        )
                    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
            except Exception as e:
                print(e)
                return

    pay_loan_form = PayLoanForm()
    context = {"account_id": pk, "pay_loan_form": pay_loan_form}

    return render(request, "bank_ledger_app/customer/pay-loan-partial.html", context)


def own_transfer(request):
    customer: Customer = request.user.customer
    if request.method == "POST":
        form = OwnTransferForm(request.POST)
        form.fields["from_account"].queryset = request.user.customer.accounts
        form.fields["to_account"].queryset = request.user.customer.accounts
        if form.is_valid():
            from_account = form.cleaned_data["from_account"].pk
            to_account = form.cleaned_data["to_account"].pk
            amount = form.cleaned_data["amount"]
            comment = form.cleaned_data["comment"]

            try:
                print(
                    "own_transfer trying to create transfer: ",
                    {
                        "from_account": from_account,
                        "to_account": to_account,
                        "amount": amount,
                        "comment": comment,
                    },
                )
                transfer = customer.transfer_money(
                    from_account, to_account, amount, comment
                )
                print("Transfer result is: ", transfer)
                if not transfer.get("ok"):
                    context = {
                        "title": transfer.get("title"),
                        "description": transfer.get("detail"),
                    }
                    return render(
                        request, "bank_ledger_app/customer/errors.html", context
                    )
                else:
                    return redirect("bank_ledger_app:profile-info", customer.pk)
            except Exception as e:
                print("own_transfer hit an UnknownException: ", e)
                print("*" * 30)
                return
    else:
        form = OwnTransferForm()
    form.fields["from_account"].queryset = request.user.customer.accounts
    form.fields["to_account"].queryset = request.user.customer.accounts
    context = {
        "own_transfer_form": form,
    }
    return render(request, "bank_ledger_app/customer/own-transfer.html", context)


def other_transfer(request):
    customer: Customer = request.user.customer
    if request.method == "POST":
        form = OtherTransferForm(request.POST)
        form.fields["from_account"].queryset = request.user.customer.accounts
        if form.is_valid():
            from_account = form.cleaned_data["from_account"].pk
            to_account = form.cleaned_data["to_account"]
            amount = form.cleaned_data["amount"]
            comment = form.cleaned_data["comment"]
            external_transfer = form.cleaned_data["external_transfer"]
            try:
                if form.cleaned_data["recurring_payment"] == False:
                    if external_transfer:
                        print(f"External transfer bool is: ", {external_transfer})
                        result = create_transaction(
                            own_account_id=from_account,
                            other_account_id=to_account,
                            comment=comment,
                            transfer_amount=amount,
                        )
                        print("Result of transaction is: ", result.data)
                        if not result.data.get("ok"):
                            context = {
                                "title": "Error: Insufficient funds ",
                                "description": f"Unable to transfer to money to account: {to_account}",
                            }
                            return render(
                                request, "bank_ledger_app/customer/errors.html", context
                            )

                        context = {
                            "title": "Success",
                            "description": f"You have successfully transfered {amount} to account: {to_account}",
                        }
                        return render(
                            request, "bank_ledger_app/customer/success.html", context
                        )
                    else:
                        transfer = customer.transfer_money(
                        from_account,
                        to_account,
                        amount,
                        comment,
                    )
                    if not transfer.get("ok"):
                        context = {
                            "title": transfer.get("title"),
                            "description": transfer.get("detail"),
                        }
                        return render(
                            request, "bank_ledger_app/customer/errors.html", context
                        )
                    return redirect("bank_ledger_app:profile-info", customer.pk)
                else:
                    transfer = customer.transfer_money(
                        from_account,
                        to_account,
                        amount,
                        comment,
                        months=form.cleaned_data["how_many_months"],
                    )
                    if not transfer.get("ok"):
                        context = {
                            "title": transfer.get("title"),
                            "description": transfer.get("detail"),
                        }
                        return render(
                            request, "bank_ledger_app/customer/errors.html", context
                        )
                    return redirect("bank_ledger_app:profile-info", customer.pk)
            except Exception as e:
                print("UnknownExceptionOccurred: ", e)
                return

    else:
        form = OtherTransferForm()

    form.fields["from_account"].queryset = request.user.customer.accounts
    context = {
        "other_transfer_form": form,
    }
    return render(request, "bank_ledger_app/customer/other-transfer.html", context)


###################################################
#                 EMPLOYEE
###################################################
def customer_list_info(request):
    return render(request, "bank_ledger_app/employee/customer-list-info.html")


def customer_list_partial(request):
    customers = Customer.objects.all()
    context = {"customers": customers}
    return render(
        request, "bank_ledger_app/employee/customer-list-partial.html", context
    )


def customer_profile_info(request, pk):
    customer = Customer.objects.get(pk=pk)
    accounts = Account.objects.filter(customer_id=pk)
    loans = customer.loans
    context = {
        "customer": customer,
        "accounts": accounts,
        "loans": loans,
    }
    return render(
        request, "bank_ledger_app/employee/customer-profile-info.html", context
    )


def customer_loan_info(request, username, pk):
    loan_id = pk
    user = User.objects.get(username=username)
    customer = Customer.objects.get(user=user.pk)
    customer_loans = customer.loans
    account = Account.objects.filter(customer_id=customer.pk)
    loan_details = []
    repayments = []
    for loan in customer_loans:
        if str(loan["loan_id"]) == pk:
            loan_details.append(loan)
        for repayment in loan["repayments"]:
            repayments.append(repayment)

    context = {
        "loan_id": loan_id,
        "account_id": account,
        "loan": customer_loans,
        "loan_details": loan_details,
        "repayments": repayments,
    }

    return render(request, "bank_ledger_app/employee/customer-loan-info.html", context)


def create_customer(request):
    if request.method == "POST":
        user_form = CreateUserForm(request.POST)
        customer_form = CreateCustomerForm(request.POST)
        if customer_form.is_valid() and user_form.is_valid():
            username = user_form.cleaned_data["username"]
            password = token_urlsafe(16)

            email = customer_form.cleaned_data["email"]
            phone_number = customer_form.cleaned_data["phone_number"]
            try:
                employee = Employee.objects.get(user=request.user)
                user = User.objects.create_user(username=username, password=password)

                employee.create_customer(email, phone_number, user)

                print("*" * 41)
                print(f"Customer password: {password}")
                print("*" * 41)
                return HttpResponseRedirect(
                    reverse("bank_ledger_app:customer-list-info")
                )
            except Exception as e:
                print(e)
                return HttpResponseRedirect(reverse("bank_ledger_app:create-customer"))

    create_user_form = CreateUserForm()
    create_customer_form = CreateCustomerForm()
    context = {
        "create_user_form": create_user_form,
        "create_customer_form": create_customer_form,
    }
    return render(request, "bank_ledger_app/employee/create-customer.html", context)


def update_customer_rank_partial(request, pk):
    customer = Customer.objects.get(customer_id=pk)
    customer_id = customer.pk
    if request.method == "POST":
        form = UpdateCustomerRankForm(request.POST)
        if form.is_valid():
            rank_options = form.cleaned_data["rank_options"]
            try:
                employee = Employee.objects.all()[0]
                employee.update_customer_rank(customer_id, rank_options)
                return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
            except Exception as e:
                print(e)
                return
    update_customer_rank_form = UpdateCustomerRankForm()
    context = {
        "update_customer_rank_form": update_customer_rank_form,
        "customer_id": customer_id,
    }
    return render(
        request, "bank_ledger_app/employee/update-customer-rank-partial.html", context
    )


def create_account_partial(request, pk):
    customer = Customer.objects.get(customer_id=pk)
    customer_id = customer.pk
    if request.method == "POST":
        form = CreateAccountForm(request.POST)
        if form.is_valid():
            account_name = form.cleaned_data["account_name"]
            try:
                employee = Employee.objects.all()[0]
                employee.create_account(customer_id, account_name)
                return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
            except Exception as e:
                print(e)
                return
    create_account_form = CreateAccountForm()
    context = {"create_account_form": create_account_form, "customer_id": customer_id}
    return render(
        request, "bank_ledger_app/employee/create-account-partial.html", context
    )


def search_customer(request):
    search_customer = request.POST["customer-search"]
    customers = Customer.search(search_customer)
    print(customers)
    context = {"customers": customers}
    return render(request, "bank_ledger_app/employee/customer-search.html", context)


def search_customer(request):
    search_customer = request.POST["customer-search"]
    customers = Customer.search(search_customer)
    context = {"customers": customers}
    return render(request, "bank_ledger_app/employee/customer-search.html", context)


###################################################
#                 SUPER USER
###################################################
def employee_list_info(request):
    employees = Employee.objects.all()
    context = {"employees": employees}
    return render(request, "bank_ledger_app/superuser/employee-list-info.html", context)


def create_employee(request):
    if request.method == "POST":
        user_form = CreateUserForm(request.POST)
        employee_form = CreateEmployeeForm(request.POST)
        if employee_form.is_valid() and user_form.is_valid():
            username = user_form.cleaned_data["username"]
            password = token_urlsafe(16)

            email = employee_form.cleaned_data["email"]
            try:
                user = User.objects.create_user(
                    username=username, password=password, is_staff=True
                )
                Employee.objects.create(email=email, user=user)

                print("*" * 41)
                print(f"Employee password: {password}")
                print("*" * 41)
                return HttpResponseRedirect(
                    reverse("bank_ledger_app:employee-list-info")
                )
            except Exception as e:
                print(e)
                return HttpResponseRedirect(reverse("bank_ledger_app:create-employee"))

    create_user_form = CreateUserForm()
    create_employee_form = CreateEmployeeForm()
    context = {
        "create_user_form": create_user_form,
        "create_employee_form": create_employee_form,
    }

    return render(request, "bank_ledger_app/superuser/create-employee.html", context)


####################### 2FA ############################


def profile_info_2fa(request):
    return render(request, "bank_ledger_app/two_factor/profile/profile.html")
