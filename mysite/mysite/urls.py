"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("polls/", include("polls.urls")),
    path("user/", include("user.user_urls")),
    path("mail/", include("mail.mail_urls")),
    path("sharepoint/", include("sharepoint.sharepoint_urls")),
    path("log/", include("log.log_urls")),
    path("pulsar/", include("pulsar.pulsar_urls")),
    path("cat/", include("cat.cat_urls")),
    path("cth/", include("cth.cth_urls")),
    path("account/", include("account.account_urls")),
]
