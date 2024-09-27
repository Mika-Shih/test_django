from django.urls import path
from . import test_plan_views

urlpatterns = [
    path('create_plan/', test_plan_views.create_plan),
    path('get_plan/<int:plan_id>/', test_plan_views.get_plan),
    path('update_plan/<int:plan_id>/', test_plan_views.update_plan),
    path('delete_plan/<int:plan_id>/', test_plan_views.delete_plan),
]
