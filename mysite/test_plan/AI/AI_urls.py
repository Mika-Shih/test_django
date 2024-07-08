from django.urls import path
from . import AI_views

urlpatterns = [
    path('get_case_suggestion/', AI_views.get_case_suggestion),
]
