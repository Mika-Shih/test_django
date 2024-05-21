from django.urls import path

from . import cat_views
app_name = "cat"
urlpatterns = [
    #path("log_operation/", log_views.log_operation, name="log_operation"),
    path("machine_tool/", cat_views.machine_tool, name="machine_tool"),
    path("pause_machine_tool/", cat_views.pause_machine_tool, name="pause_machine_tool"),
    path("continue_machine_tool/", cat_views.continue_machine_tool, name="continue_machine_tool"),
    path("machine_report/", cat_views.machine_report, name="machine_report"),
    path("machine_status_report/", cat_views.machine_status_report, name="machine_status_report"),
    path("filter_machine_status_report/", cat_views.filter_machine_status_report, name="filter_machine_status_report"),
    path("filter_module/", cat_views.filter_module, name="filter_module"),
    path("filter_platform/", cat_views.filter_platform, name="filter_platform"),
    path("filter_version/", cat_views.filter_version, name="filter_version"),
    path("download_cth/", cat_views.download_cth, name="download_cth"),
    path("create_task/", cat_views.create_task, name="create_task"),
]