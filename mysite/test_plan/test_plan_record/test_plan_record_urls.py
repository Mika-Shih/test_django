from django.urls import path
from . import test_plan_record_views

urlpatterns = [
    path('create_plan_record/', test_plan_record_views.create_plan_record),
    path('get_all_plan_record/', test_plan_record_views.get_all_plan_record),
    path('get_plan_record/<int:plan_id>/', test_plan_record_views.get_plan_record),
    path('get_personal_plan_record/', test_plan_record_views.get_personal_plan_record),
    path('get_personal_specific_plan_record/', test_plan_record_views.get_personal_specific_plan_record),
    path('update_plan_record_status/<int:plan_id>/', test_plan_record_views.update_plan_record_status),
    path('delete_plan_record/', test_plan_record_views.delete_plan_record),
]
 