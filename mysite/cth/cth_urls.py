from django.urls import path

from . import cth_views
app_name = "cth"
urlpatterns = [
    #path("log_operation/", log_views.log_operation, name="log_operation"),
    path("machine_status/", cth_views.machine_status, name="machine_status"),
    path("new_task_machine/", cth_views.new_task_machine, name="new_task_machine"),
    path("new_machine/", cth_views.new_machine, name="new_machine"),
    path("issue_create/", cth_views.issue_create, name="issue_create"),
    path("end_task_machine/", cth_views.end_task_machine, name="end_task_machine"),
    path("test_database/", cth_views.test_database, name="test_database"),
]
