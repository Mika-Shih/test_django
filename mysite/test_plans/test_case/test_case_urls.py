from django.urls import path
from . import test_case_views

urlpatterns = [
    path('list_case/', test_case_views.list_case),
    path('create_case/', test_case_views.create_case),
    path('edit_case/', test_case_views.edit_case),
]
