from django.urls import path

from . import user_views
app_name = "user"
urlpatterns = [
    path("login/", user_views.login, name="login"),
    path("verify/", user_views.verify, name="verify"),
    # path("create_account/", user_views.create_account, name="create_account"),
    path("sign_up/", user_views.sign_up, name="sign_up"),
    path('activate/<str:activation_code>/', user_views.activate_account, name='activate_account'),
    path("change_password/", user_views.change_password, name="change_password"),
    path("active_code/", user_views.active_code, name="active_code"),
    path("logout/", user_views.logout, name="logout"),
    path("view_token/", user_views.view_token, name="view_token"),
    path("edit_token/", user_views.edit_token, name="edit_token"),
    path("member/", user_views.member, name="member"),
    # path("mail/", include("mail.mail_urls")),
    # path("log/", include("log.log_urls")),
]