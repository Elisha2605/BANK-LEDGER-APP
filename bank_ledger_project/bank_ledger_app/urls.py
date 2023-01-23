from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

app_name = 'bank_ledger_app'


urlpatterns = [
    path('', views.index, name='index'),
    #CUSTOMER
    path('customer/profile-info/<str:pk>/', views.profile_info, name='profile-info'),
    path('customer/account-info/<str:pk>/', views.account_info, name='account-info'),
    path('customer/loan-info/<str:pk>/', views.loan_info, name='loan-info'),

    path('customer/loan/', views.loan, name='loan'),
    path('customer/pay-loan-partial/<str:pk>/', views.pay_loan_partial, name='pay-loan-partial'),
    path('customer/own-transfer/', views.own_transfer, name='own-transfer'),
    path('customer/other-transfer/', views.other_transfer, name='other-transfer'),

    # EMPLOYEE
    path('employee/customer-list-info/', views.customer_list_info, name='customer-list-info'),
    path('employee/customer-list-partial/', views.customer_list_partial, name='customer-list-partial'), 
    path('employee/customer-profile-info/<str:pk>/', views.customer_profile_info, name='customer-profile-info'),
    path('employee/customer-loan-info/<str:username>/<str:pk>/', views.customer_loan_info, name='customer-loan-info'),
    path('employee/customer-search/', views.search_customer, name='customer-search'),
    path('employee/create-customer/', views.create_customer, name='create-customer'),
    path('employee/update-customer-rank-partial/<str:pk>/', views.update_customer_rank_partial, name='update-customer-rank-partial'),
    path('employee/create-account-partial/<str:pk>/', views.create_account_partial, name='create-account-partial'),
    

    # SUPERUSER
    path('superuser/employee-list-info/', views.employee_list_info, name='employee-list-info'),
    path('superuser/create-employee/', views.create_employee, name='create-employee'),

    # API
    path('api/', include('api.urls')),

    # 2FA
    path('two_factor/profile/profile', views.profile_info_2fa, name='profile-info-2fa')


]
