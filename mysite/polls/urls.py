from django.urls import path, include

from . import views

app_name = "polls"
urlpatterns = [
    path("hint_machine_arrive_mail/", views.hint_machine_arrive_mail, name="hint_machine_arrive_mail"), 
    path("filter_option/", views.filter_option, name="filter_option"),
    path("api/filtersearch/", views.filtersearch, name="filtersearch"),
    path("api/widthsearch/", views.widthsearch, name="widthsearch"),
    path("api/target/", views.target, name="target"),
    path("api/group/", views.group, name="group"),
    path("api/platform/", views.platform, name="platform"),
    path("api/cycle/", views.cycle, name="cycle"),
    path("api/phase/", views.phase, name="phase"),
    path("api/status/", views.status, name="status"),

    path("changeplatform/", views.changeplatform, name="changeplatform"),

    path("lendpersonnel/", views.lendpersonnel, name="lendpersonnel"),
    path("lendplatform/", views.lendplatform, name="lendplatform"),

    path("returnplatform/", views.returnplatform, name="returnplatform"),

    path("deleteplatform/", views.deleteplatform, name="deleteplatform"),

    path("send_mail_newplatform/", views.send_mail_newplatform, name="send_mail_newplatform"),

    path("api/addplatformcombination/", views.addplatformcombination, name="addplatformcombination"),
    path("api/addplatformonly/", views.addplatformonly, name="addplatformonly"),
    path("addnewplatform/", views.addnewplatform, name="addnewplatform"),

    path('scrapped_platform/', views.scrapped_platform, name='scrapped_platform'),
    # path("proxy_mail/", views.proxy_mail, name="proxy_mail"),
    path("machine_record/", views.machine_record, name="machine_record"),
    
    path("user_info_mail/", views.user_info_mail, name="user_info_mail"),

    path("excel_export/", views.excel_export, name="excel_export"),
    path("sharepoint_name_user/", views.sharepoint_name_user, name="sharepoint_name_user"), #choose_folder
    path("file_location/", views.file_location, name="file_location"), #choose_file
    path("sharepoint_copy_file/", views.sharepoint_copy_file, name="sharepoint_copy_file"),
]