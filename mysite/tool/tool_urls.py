from django.urls import path

from . import tool_views
app_name = "tool"
urlpatterns = [
    path("time_transmit/", tool_views.time_transmit, name="time_transmit"),
]