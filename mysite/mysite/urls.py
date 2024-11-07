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
    path("api/polls/", include("polls.urls")),
    path("api/user/", include("user.user_urls")),
    path("api/mail/", include("mail.mail_urls")),
    path("api/sharepoint/", include("sharepoint.sharepoint_urls")),
    path("api/log/", include("log.log_urls")),
    path("api/pulsar/", include("pulsar.pulsar_urls")),
    path("api/cat/", include("cat.cat_urls")),
    path("api/cth/", include("cth.cth_urls")),
    path("api/account/", include("account.account_urls")),
    path("api/test_driver_validation/", include("test_driver_validation.tdv_urls")),
    path("api/test_plans/", include("test_plans.test_plan_urls")),
    path("api/test_plan/", include("test_plan.test_plan_urls")),
]
