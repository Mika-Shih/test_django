from django.urls import path, include
from .test_plan import test_plan_urls
from .test_case import test_case_urls
urlpatterns = [
    path('test_plan/', include(test_plan_urls)),
    path('test_case/', include(test_case_urls)),
]