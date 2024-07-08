from django.urls import path
from . import test_case_views

urlpatterns = [
    path('create_case/', test_case_views.create_case),
    path('get_case/<int:case_id>/', test_case_views.get_case),
    path('update_case/<int:case_id>/', test_case_views.update_case),
    path('delete_case/<int:case_id>/', test_case_views.delete_case),
]
