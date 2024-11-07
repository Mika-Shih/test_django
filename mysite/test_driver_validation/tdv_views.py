from django.http import JsonResponse
from rest_framework.decorators import api_view
from datetime import datetime
import pytz 
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from user.token import LoginRequiredMiddleware #request.uesr_id
from sharepoint import sharepoint_views as sharepoint_views
from log import log_views as log_views
from user import user_views as user_views

def timenow():
    current_time = datetime.now()
    timezone = pytz.timezone('Asia/Taipei')
    last_update_time = current_time.astimezone(timezone)
    return last_update_time    

def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

@api_view(["post"])
@csrf_exempt
@with_db_connection
def create_new_task(cursor, request):
    user_id = request.user_id
    request_email = request.data.get('email')
    release_date = request.data.get('release_date')
    module = request.data.get('module')
    driver = request.data.get('driver')
    detail = request.data.get('detail')
    os = request.data.get('os')
    bios_version = request.data.get('bios_version')
    message = request.data.get('message')
    validation_start_time = request.data.get('validation_start_time')
    validation_end_time = request.data.get('validation_end_time')
    if not all([request_email, release_date, module, driver, detail, os, bios_version, validation_start_time, validation_end_time]):
        return JsonResponse({"error": "Missing required fields."})
    request_id = user_views.mail_to_userid(request_email)
    task_info = {
        module: module,
        driver: driver,
        os: os,
        bios_version: bios_version,
    }
    request_info = {
        "request_detail": detail,
        "message": message,
    }
    date_info = {
        "release_date": release_date,
        "validation_start_date": validation_start_time,
        "validation_end_date": validation_end_time,
    }
    cursor.execute(
        '''
        INSERT INTO test_arrangement_record (requester_id, task_detail, request_detail, date_detail, update_time)
        VALUES (%s, %s, %s, %s, %s);
        ''',
        (request_id, task_info, request_info, date_info, timenow())
    )
    return JsonResponse({"finaldata": "successful"})
