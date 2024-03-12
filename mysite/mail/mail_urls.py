from django.urls import path

from . import mail_views
app_name = "mail"
urlpatterns = [
    path("send_activation_email/", mail_views.send_activation_email, name="send_activation_email"),
    path("send_email_proxy/", mail_views.send_email_proxy, name="send_email_proxy"),
]