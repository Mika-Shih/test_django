from django.urls import path
from . import test_case_record_views

urlpatterns = [
    path('create_case_record/', test_case_record_views.create_case_record),
    path('get_all_case_record/', test_case_record_views.get_all_case_record),
    path('get_personal_case_record/', test_case_record_views.get_personal_case_record),
    path('get_personal_case_specific_record/', test_case_record_views.get_personal_case_specific_record),
    path('get_version_specific_record/', test_case_record_views.get_version_specific_record),
    path('get_personal_plan_cases/', test_case_record_views.get_personal_plan_cases),
    path('get_case_record/<int:case_id>/', test_case_record_views.get_case_record),
    path('get_category_all_case/', test_case_record_views.get_category_all_case),
    path('get_all_version_record/', test_case_record_views.get_all_version_record),
    path('update_case_record_status/<int:case_id>/', test_case_record_views.update_case_record_status),
    path('update_case_record_ai_suggestion/', test_case_record_views.update_case_record_ai_suggestion),
    path('delete_case_from_plan/', test_case_record_views.delete_case_from_plan),
    path('delete_case_record/', test_case_record_views.delete_case_record),
]
