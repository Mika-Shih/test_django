from django.urls import path, include

from . import pulsar_views
app_name = "pulsar"
urlpatterns = [
    path("pulsar/", pulsar_views.pulsar, name="pulsar"),
    path("add_device_tool_list/", pulsar_views.add_device_tool_list, name="add_device_tool_list"),
    path("add_version/", pulsar_views.add_version, name="add_version"),
    

    path("create_device_tool/", pulsar_views.create_device_tool, name="create_device_tool"),
    
    path("select_short_name/", pulsar_views.select_short_name, name="select_short_name"),
    path("select_long_name/", pulsar_views.select_long_name, name="select_long_name"),
    path("select_subdevice/", pulsar_views.select_subdevice, name="select_subdevice"),
    path("create_version/", pulsar_views.create_version, name="create_version"),

    path("select_hardware_id/", pulsar_views.select_hardware_id, name="select_hardware_id"),
    path("select_version/", pulsar_views.select_version, name="select_version"),
    path("select1_version/", pulsar_views.select1_version, name="select1_version"),

    path("download_version/", pulsar_views.download_version, name="download_version"),
    path("device_info/", pulsar_views.device_info, name="device_info"),
  
]