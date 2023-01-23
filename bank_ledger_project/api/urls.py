from django.urls import path
from . import views

urlpatterns = [
    path("balance/<str:pk>/", views.get_account_balance_by_id),
    path("transfer-funds/", views.transfer_funds),
    path("transaction/<str:pk>/", views.delete_transaction),
]
