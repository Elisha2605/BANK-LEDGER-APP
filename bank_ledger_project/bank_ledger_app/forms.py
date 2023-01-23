from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError
from .models import Employee, Customer, Account, CustomerRanks
from django.db import OperationalError


class CreateEmployeeForm(forms.ModelForm):
    email = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border"}),
        required=False)

    class Meta:
        model = User
        fields = ('email',)

    def clean(self):
        super().clean()
        return self.cleaned_data


# CUSTOMER FORMS
class LoanForm(forms.Form):
    account = forms.ModelChoiceField(
        label="from_account",
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={"class": "box box-light-border"}))

    amount = forms.DecimalField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border", "placeholder": "0.00 kr"}))

    comment = forms.CharField(
        widget=forms.TextInput(attrs={"class": "box box-light-border"}),
        required=False)


class PayLoanForm(forms.Form):
    amount = forms.DecimalField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border", "placeholder": "0.00 kr"}),
        required=True)

    recurring_payment = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}), 
        required=False)
    
    how_many_months = forms.DecimalField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border", "placeholder": "0"}),
        required=False)

    def clen(self):
        super().clean()
        return self.cleaned_data


class OwnTransferForm(forms.Form):
    from_account = forms.ModelChoiceField(
        label="From account",
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={"class": "box box-light-border"}))

    to_account = forms.ModelChoiceField(
        label="To account",
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={"class": "box box-light-border"}))

    amount = forms.DecimalField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border", "placeholder": "0.00 kr"}))

    comment = forms.CharField(
        widget=forms.TextInput(attrs={"class": "box box-light-border"}),
        required=False)

    def clean(self):
        super().clean()
        return self.cleaned_data


class OtherTransferForm(forms.Form):

    from_account = forms.ModelChoiceField(
        label="From account",
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={"class": "box box-light-border"}))

    to_account = forms.CharField(
        widget=forms.TextInput(attrs={"class": "box box-light-border", "placeholder": "Enter account ID"}))

    amount = forms.DecimalField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border", "placeholder": "0.00 kr"}))

    comment = forms.CharField(
        widget=forms.TextInput(attrs={"class": "box box-light-border"}),
        required=False)

    external_transfer = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}), 
        required=False)

    recurring_payment = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}), 
        required=False)
    
    how_many_months = forms.DecimalField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border", "placeholder": "0"}),
        required=False)

    def clean(self):
        super().clean()
        return self.cleaned_data


# EMPLOYEE FORMS

class CreateUserForm(forms.ModelForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border"}),
        required=False)

    class Meta:
        model = User
        fields = ('username',)

    def clean(self):
        super().clean()
        return self.cleaned_data


class CreateCustomerForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border"}))

    phone_number = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border"}))

    class Meta:
        model = Customer
        fields = ('email', 'phone_number')

    def clean(self):
        super().clean()
        return self.cleaned_data


class UpdateCustomerRankForm(forms.Form):
    rank_options = forms.ChoiceField(
        choices=CustomerRanks.choices,
        widget=forms.Select(
            attrs={"class": "box box-light-border"}))

    def clean(self):
        super().clean()
        return self.cleaned_data


class CreateAccountForm(forms.Form):
    account_name = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "box box-light-border"}))

    def clean(self):
        super().clean()
        return self.cleaned_data


class NewCustomerForm(forms.ModelForm):
    email = forms.CharField(label='email', required=True)
    phone_number = forms.CharField(label='phone number', required=True)

    class Meta:
        model = Customer
        fields = ('email', 'phone_number',)

