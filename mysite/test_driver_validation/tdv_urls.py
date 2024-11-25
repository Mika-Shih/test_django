from django.urls import path

from . import tdv_views
app_name = "tdv"
urlpatterns = [
    path("list_task/", tdv_views.list_task, name="list_task"),
    path("create_new_task/", tdv_views.create_new_task, name="create_new_task"),
    path("approve_task/", tdv_views.approve_task, name="approve_task"),
    path("edit_task/", tdv_views.edit_task, name="edit_task"),
]