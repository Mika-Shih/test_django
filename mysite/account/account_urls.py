from django.urls import path

from . import account_views
app_name = "account"
urlpatterns = [
    #path("log_operation/", log_views.log_operation, name="log_operation"),
    path("add_member/", account_views.add_member, name="add_member"),
    path("edit_member/", account_views.edit_member, name="edit_member"),
]