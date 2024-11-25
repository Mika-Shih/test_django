from django.http import JsonResponse
from rest_framework.decorators import api_view
from datetime import datetime
import pytz 
import json
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from user.token import LoginRequiredMiddleware #request.uesr_id
from mail import mail_views as mail_views
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

# authorizer
authorizer = "bill.chang@hp.com"

@with_db_connection
def list_task(cursor, request):
    user_id = request.user_id

    cursor.execute(
        '''
        SELECT id, requester_id, task_detail, request_detail, date_detail, update_time, status
        FROM test_arrangement_record
        ''',
    )
    rows = cursor.fetchall()
    all_data = []
    if rows:
        for row in rows:
            [id, requester_id, task_detail, request_detail, date_detail, update_time, status] = row
            requester_name = user_views.userid_to_mail(requester_id)[0]
            requester_email = user_views.userid_to_mail(requester_id)[1]

            data = {
                "id": id,
                "edit_access" : user_id == requester_id,
                "requester_name": requester_name,
                "requester_email": requester_email,
                "task_detail": {
                    "module": json.loads(task_detail)["module"],
                    "driver": json.loads(task_detail)["driver"],
                    "os": json.loads(task_detail)["os"],
                    "bios_version": json.loads(task_detail)["bios_version"],      
                },
                "request_detail": {
                    "request_detail": json.loads(request_detail)["request_detail"],
                    "message": json.loads(request_detail)["message"],
                },
                "date_detail": {
                    "release_date": json.loads(date_detail)["release_date"],
                    "validation_start_date":json.loads(date_detail)["validation_start_date"],
                    "validation_end_date": json.loads(date_detail)["validation_end_date"],
                },
                "update_time": update_time,
                "status": status,
            }
            all_data.append(data)
    return JsonResponse({"finaldata": all_data, "permission": user_id == authorizer})


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
    os = request.data.get('OS')
    bios_version = request.data.get('BIOS_version')
    message = request.data.get('message')
    validation_start_time = request.data.get('validation_start_time')
    validation_end_time = request.data.get('validation_end_time')
    if not all([request_email, release_date, module, driver, detail, os, bios_version, validation_start_time, validation_end_time]):
        return JsonResponse({"error": "Missing required fields."})
    request_id = user_views.mail_to_userid(request_email)
    task_info = {
        "module": module,
        "driver": driver,
        "os": os,
        "bios_version": bios_version,
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
        INSERT INTO test_arrangement_record (requester_id, task_detail, request_detail, date_detail, update_time, status)
        VALUES (%s, %s, %s, %s, %s, %s);
        ''',
        (request_id, json.dumps(task_info), json.dumps(request_info), json.dumps(date_info), timenow(), "Pending")
    )
    tdv_mail = []
    tdv_data = {
        "requester": request_email,
        "release_date": release_date,
        "module": module,
        "driver": driver,
        "detail": detail,
        "os": os,
        "bios_version": bios_version,
        "duration_start_date": validation_start_time,
        "duration_end_date": validation_end_time,
    }
    tdv_mail.append(tdv_data)
    try:
        # sent mail use the system authorizer
        mail_views.tdv_new_task_mail(authorizer, to=[authorizer, request_email], record=tdv_mail, message=message)
    except Exception as e:
        return JsonResponse({"error": "Failed to send email."})
    return JsonResponse({"finaldata": "successful"})


# f'"{assgin}"' creates a string representation (quoted text), not a JSON number.
@api_view(["post"])
@csrf_exempt
@with_db_connection
def approve_task(cursor, request):
    user_id = request.user_id
    assgin = request.data.get('assgin')
    email = request.data.get('email')
    cc_mail = request.data.get('cc_mail')
    task_id = request.data.get('task_id')
    print(user_id, authorizer, assgin, email, cc_mail, task_id)
    if user_id != authorizer:
        return JsonResponse({'error': 'Insufficient permissions'})
    if not assgin:
        return JsonResponse({'error': 'Assgin tester is required'})
    cursor.execute(
        '''
        UPDATE test_arrangement_record
        SET status = %s, 
            update_time = %s,
            request_detail = jsonb_set(request_detail, %s, %s::jsonb, true)
        WHERE id = %s
        ''',
        ("Approved", timenow(), '{assgin_tester}', json.dumps(user_views.mail_to_userid(assgin)), task_id)
    )
    return JsonResponse({"finaldata": "successful"})

@api_view(["post"])
@csrf_exempt
@with_db_connection
def edit_task(cursor, request):
    user_id = request.user_id
    task_id = request.data.get('task_id')
    request_email = request.data.get('email')
    release_date = request.data.get('release_date')
    module = request.data.get('module')
    driver = request.data.get('driver')
    detail = request.data.get('detail')
    os = request.data.get('OS')
    bios_version = request.data.get('BIOS_version')
    validation_start_time = request.data.get('validation_start_time')
    validation_end_time = request.data.get('validation_end_time')
    if user_id != authorizer and user_id != request_email:
        return JsonResponse({'error': 'Insufficient permissions'})
    cursor.execute(
        '''
        UPDATE test_arrangement_record
        SET status = %s, update_time = %s
        WHERE id = %s
        ''',
        ("Approved", timenow(), task_id)
    )
    return JsonResponse({"finaldata": "successful"})


