from django.urls import path
from . import test_case_views

urlpatterns = [
    path('list_case/', test_case_views.list_case),
    path('create_case/', test_case_views.create_case),
    path('edit_case/', test_case_views.edit_case),
    path('add_category/', test_case_views.add_category),
    path('view_category/', test_case_views.view_category),
    path('edit_permission/', test_case_views.edit_permission),
    path('select_case/', test_case_views.select_case),
    path('delete_case/', test_case_views.delete_case),
    path('restore_case/', test_case_views.restore_case),
]
