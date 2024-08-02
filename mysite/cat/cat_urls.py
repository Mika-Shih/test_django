from django.urls import path

from . import cat_views
app_name = "cat"
urlpatterns = [
    path("machine_tool/", cat_views.machine_tool, name="machine_tool"),
    path("stop_machine/", cat_views.stop_machine, name="stop_machine"),
    path("pause_machine/", cat_views.pause_machine, name="pause_machine"),
    path("continue_machine/", cat_views.continue_machine, name="continue_machine"),
    path("machine_status_report/", cat_views.machine_status_report, name="machine_status_report"),  #enter_web
    path("filter_machine_status_report/", cat_views.filter_machine_status_report, name="filter_machine_status_report"), #filter
    path("filter_module/", cat_views.filter_module, name="filter_module"),
    path("filter_platform/", cat_views.filter_platform, name="filter_platform"),
    path("filter_version/", cat_views.filter_version, name="filter_version"), #not use
    path("download_cth/", cat_views.download_cth, name="download_cth"),
    path("create_task/", cat_views.create_task, name="create_task"),
    path("select_machine_report/", cat_views.select_machine_report, name="select_machine_report"),#report_get
]