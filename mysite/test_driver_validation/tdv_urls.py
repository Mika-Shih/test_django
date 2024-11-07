from django.urls import path

from . import tdv_views
app_name = "tdv"
urlpatterns = [
    # path("create/", tdv_views.pulsar, name="pulsar"),
    path("create_new_task/", tdv_views.create_new_task, name="create_new_task"),
    
]