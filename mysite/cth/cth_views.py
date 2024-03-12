from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
#from django.template import loader
from django.views import generic
from django.urls import reverse
import json

from datetime import datetime, timedelta
from dateutil.parser import parse #時間字串改回時間 用於時間比較
from django.utils.dateparse import parse_datetime #時間用 目前沒用到
from dateutil import parser #時間用 目前沒用到

import pytz #時間區域
#跨站偽造
from django.views.decorators.csrf import csrf_exempt
#post
from rest_framework.decorators import api_view, parser_classes
#post 掛檔
from rest_framework.parsers import MultiPartParser
#模板渲染
from django.template.loader import get_template
#清除緩存
from django.views.decorators.cache import cache_control
#token 屏蔽
import jwt 
import inspect
from log import log_views as log_views
from django.db import connection

def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

def timenow():
    current_time = datetime.now()
    timezone = pytz.timezone('Asia/Taipei')
    last_update_time = current_time.astimezone(timezone)
    return last_update_time

@api_view(["post"])
@csrf_exempt
@with_db_connection
def machine_status(cursor, request):
    serial_number = request.data.get('serial_number')
    try:
        serial_number_condition = f"AND tul.serial_number IN (%s)" 
        query =f'''
        SELECT id, status
        FROM test_unit_list AS tul
        WHERE 1=1 {serial_number_condition}
        '''
        cursor.execute(query, (serial_number,))
        result_SN = cursor.fetchone()
        if result_SN:
            [id, status] = result_SN
            status = {'status': [id, status]}
        else:
            status = {'status': None}
        return JsonResponse(status, safe=True)
    except Exception as e:
        log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {serial_number}")
    
@api_view(["post"])
@csrf_exempt
@with_db_connection
def new_task_machine(cursor, request):
    id = request.data.get('id')
    uut_info_json = request.data.get('uut_info')
    request_info_json = request.data.get('request_info')
    last_update_time = timenow()
    status = "running"
    try:
        query = f'''
        UPDATE test_unit_list
        SET status = %s, last_update_time = %s, uut_info = %s
        WHERE id = %s;
        '''
        cursor.execute(query, (status,) + (last_update_time,) +  (uut_info_json,) + (id,)) 
        cursor.execute("INSERT INTO unit_task (test_unit_id, request_info, uut_info, status, start_time) VALUES (%s, %s, %s, %s, %s)", (id, request_info_json, uut_info_json, status, last_update_time))
        return JsonResponse({"status": "successful"}, safe=True)
    except Exception as e:
        log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"test_unit_list id: {id}")

@api_view(["post"])
@csrf_exempt
@with_db_connection
def new_machine(cursor, request):
    serial_number = request.data.get('serial_number')
    product_name = request.data.get('product_name')
    uut_info_json = request.data.get('uut_info')
    request_info_json = request.data.get('request_info')
    serial_number_condition = f"AND ul.serial_number IN (%s)" 
    last_update_time = timenow()
    status = "running"
    try:
        query = f'''
        SELECT platform_id
        FROM unit_list AS ul
        WHERE 1=1 {serial_number_condition}
        '''
        cursor.execute(query, (serial_number,))
        result_SN = cursor.fetchone()
        if result_SN:
            [platform_id] = result_SN
            # 寫入你的product_name到platform_info
        else:
            platform_info_condition = f"AND pi.platform_info @> %s" 
            query = f'''
            SELECT id
            FROM platform_info AS pi
            WHERE 1=1 {platform_info_condition}
            '''
            cursor.execute(query, (json.dumps({"product_name": product_name}),))
            result_platform = cursor.fetchone()
            if result_platform:
                [platform_id] = result_platform
            else:
                [platform_id] = [0]
        cursor.execute("INSERT INTO test_unit_list (platform_id, serial_number, status, last_update_time, uut_info) VALUES (%s, %s, %s, %s, %s) RETURNING id", (platform_id, serial_number, status, last_update_time, uut_info_json)) 
        result_unit_list_id = cursor.fetchone()
        cursor.execute("INSERT INTO unit_task (test_unit_id, request_info, uut_info, status, start_time) VALUES (%s, %s, %s, %s, %s)", (result_unit_list_id[0], request_info_json, uut_info_json, status, last_update_time))
        return JsonResponse({"status": "successful"}, safe=True)
    except Exception as e:
        log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {serial_number}")

@api_view(["post"])
@csrf_exempt
@with_db_connection
def issue_create(cursor, request):
    serial_number = request.data.get('serial_number')
    title = request.data.get('title') 
    level = request.data.get('level')
    power_state = request.data.get('power_state')
    description = request.data.get('description')
    device_driver = request.data.get('device_driver')
    formatted_time = request.data.get('add_time')
    add_time = datetime.strptime(formatted_time, "%Y%m%d-%H%M%S").strftime("%Y-%m-%d %H:%M:%S.%f+00")
    print(serial_number, title, level, power_state, description, device_driver, add_time)
    try:
        serial_number_condition = f"AND tul.serial_number IN (%s)"
        query = f'''
        SELECT ut.id, ut.uut_info->>UPPER(%s)
        FROM unit_task AS ut
        JOIN test_unit_list AS tul ON ut.test_unit_id = tul.id
        WHERE ut.finish_time is null and ut.uut_info->>UPPER(%s) is not null {serial_number_condition} 
        ORDER by ut.start_time DESC
        limit 1
        '''
        cursor.execute(query, (device_driver,) + (device_driver,) + (serial_number,))
        result_id = cursor.fetchone()
        if result_id:
            [unit_task_id, device_info_json] = result_id
            # device_info_json = json.dumps(device_info)
            issue_info_json = json.dumps({'issue_detail': description, 'power_state': power_state})
            cursor.execute("INSERT INTO comm_task_issue (task_id, issue_short_description, failed_device_info, issue_info, servity, add_time) VALUES (%s, %s, %s, %s, %s, %s)", (unit_task_id, title, device_info_json, issue_info_json, level, add_time))
            return JsonResponse({"status": "successful"}, safe=True)
        else:
            return JsonResponse({"status": "failed"}, safe=True)
    except Exception as e:
        log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {serial_number}")


@api_view(["post"])
@csrf_exempt
@with_db_connection
def end_task_machine(cursor, request):
    id = request.data.get('id')
    finish_info_json = request.data.get('finish_info') 
    last_update_time = timenow()
    try:
        test_unit_id_condition = f"AND ut.test_unit_id IN (%s)"
        query = f'''
        SELECT id
        FROM unit_task AS ut
        WHERE finish_time is null {test_unit_id_condition}
        ORDER by start_time DESC
        '''
        cursor.execute(query, (id,))
        result_id = cursor.fetchone()
        if result_id:
            [unit_task_id] = result_id
            status = "idle"
            query = f'''
            UPDATE test_unit_list
            SET status = %s, last_update_time = %s
            WHERE id = %s;
            '''
            cursor.execute(query, (status, last_update_time, id))
            status_task = "finish"
            query = f'''
            UPDATE unit_task
            SET status = %s, result_info = %s, finish_time = %s
            WHERE id = %s;
            '''
            cursor.execute(query, (status_task, finish_info_json, last_update_time, unit_task_id))
            return JsonResponse({"status": "successful"}, safe=True)
        return JsonResponse({"status": "failed"}, safe=True)
    except Exception as e:
        log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"test_unit_list_id: {id}")

@with_db_connection
def test_database(cursor, request):
    title = "BT"
    query = f'''
        SELECT ut.id, ut.uut_info->%s
        FROM unit_task AS ut
        WHERE ut.uut_info->%s IS NOT NULL;
        '''
    cursor.execute(query, (title,) + (title,))
    result = cursor.fetchone()
    print(result)
    return JsonResponse({"status": "successful"}, safe=True)
