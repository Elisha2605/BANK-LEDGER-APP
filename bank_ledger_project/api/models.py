from django.db import models

class Transaction(models.Model):
    own_bank_ip = models.CharField(null=True, max_length=200)
    other_bank_ip = models.CharField(null=True, max_length=200)
    own_account_id = models.UUIDField(null=False)
    other_account_id = models.UUIDField(null=False)
    transfer_amount = models.DecimalField(null=False, max_digits=15, decimal_places=2)
    comment = models.CharField(null=True, max_length=200)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'own_bank_ip: {self.own_bank_ip}, other_bank_ip: {self.other_bank_ip}, own_account_id: {self.own_account_id}, other_account_id: {self.other_account_id}, transfer_amount: {self.transfer_amount}, comment: {self.comment}, created: {self.created}'


class TransferFunds(models.Model): 
    transaction_id = models.UUIDField(null=False, primary_key=True)
    origin = models.UUIDField(null=False)
    destination = models.UUIDField(null=False)
    transfer_amount = models.DecimalField(null=False, max_digits=15, decimal_places=2)
    comment = models.CharField(null=True, max_length=200)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'transaction_id: {self.transaction_id}, origin: {self.origin}, destination: {self.destination}, transfer_amount: {self.transfer_amount}, comment: {self.comment}, created: {self.created}'