from django.urls import path
from . import test_plan_views

urlpatterns = [
    path('create_plan/', test_plan_views.create_plan),
]
