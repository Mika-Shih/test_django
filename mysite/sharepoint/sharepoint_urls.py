from django.urls import path

from . import sharepoint_views
app_name = "sharepoint"
urlpatterns = [
    path("sharepoint_upload_file/", sharepoint_views.sharepoint_upload_file, name="sharepoint_upload_file"),
    path("sharepoint_download_file_zip/", sharepoint_views.sharepoint_download_file_zip, name="sharepoint_download_file_zip"),
]