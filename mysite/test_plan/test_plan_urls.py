from django.urls import path, include
from .test_plan import test_plan_urls
from .test_plan_record import test_plan_record_urls
from .test_case import test_case_urls
from .test_case_record import test_case_record_urls
from .category import category_urls
from .AI import AI_urls
urlpatterns = [
    path('test_plan/', include(test_plan_urls)),
    path('test_plan_record/', include(test_plan_record_urls)),
    path('test_case/', include(test_case_urls)),
    path('test_case_record/', include(test_case_record_urls)),
    path('category/', include(category_urls)),
    path('ai/', include(AI_urls)),
]