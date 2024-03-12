from django.urls import path

from . import log_views
app_name = "log"
urlpatterns = [
    path("log_operation/", log_views.log_operation, name="log_operation"),
    path("log_error/", log_views.log_error, name="log_error"),
]