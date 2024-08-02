from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, FileResponse
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
import os
import inspect
from django.db import connection
from account import account_views as account_views
from sharepoint import sharepoint_views as sharepoint_views
from tool import download_tool as download_tool
from log import log_views as log_views
from user import user_views as user_views

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

@with_db_connection
def machine_tool(cursor, request):
    query = '''
    SELECT serial_number, status, last_update_time, uut_info
    FROM test_unit_list 
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    machine_list = []
    for row in rows:
        machine_list_data ={
            "serial_number":row[0],
            "status":row[1],
            "last_update_time":row[2],
            "uut_info":row[3],
        }
        machine_list.append(machine_list_data)
    return JsonResponse(machine_list, safe=False)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def stop_machine(cursor, request):
    serial_number = request.data.get('serial_number')
    query = '''
    SELECT id, status
    FROM test_unit_list 
    WHERE serial_number = %s
    '''
    cursor.execute(query, (serial_number,))
    [test_unit_id, status] = cursor.fetchone()
    if status == "running" or "pause":
        query = '''
        SELECT id
        FROM test_unit_tasks
        WHERE test_unit_id = %s AND status = 'stop'
        '''
        cursor.execute(query, (test_unit_id,))
        result = cursor.fetchone()
        if result:
            return JsonResponse({"error": "status is exist"}) 
        else:
            cursor.execute("INSERT INTO test_unit_tasks (test_unit_id, status, add_time) VALUES (%s, %s, %s)", (test_unit_id, "stop", timenow()))    
            return JsonResponse({"finaldata": "successful"})
    else:
        return JsonResponse({"error": "status is changed"}) 

@api_view(["post"])
@csrf_exempt
@with_db_connection
def pause_machine(cursor, request):
    serial_number = request.data.get('serial_number')
    query = '''
    SELECT id, status
    FROM test_unit_list 
    WHERE serial_number = %s
    '''
    cursor.execute(query, (serial_number,))
    [test_unit_id, status] = cursor.fetchone()
    if status == "running":
        query = '''
        SELECT id
        FROM test_unit_tasks
        WHERE test_unit_id = %s AND (status = 'pause' OR status = 'stop')
        '''
        cursor.execute(query, (test_unit_id,))
        result = cursor.fetchone()
        if result:
            return JsonResponse({"error": "status is exist"}) 
        else:
            cursor.execute("INSERT INTO test_unit_tasks (test_unit_id, status, add_time) VALUES (%s, %s, %s)", (test_unit_id, "pause", timenow()))    
            return JsonResponse({"finaldata": "successful"}) 
    else:
        return JsonResponse({"error": "status is changed"})


@api_view(["post"])
@csrf_exempt
@with_db_connection
def continue_machine(cursor, request):
    serial_number = request.data.get('serial_number')
    query = '''
    SELECT id, status
    FROM test_unit_list 
    WHERE serial_number = %s
    '''
    cursor.execute(query, (serial_number,))
    [test_unit_id, status] = cursor.fetchone()
    if status == "pause":
        query = '''
        SELECT id
        FROM test_unit_tasks
        WHERE test_unit_id = %s AND (status = 'running' OR status = 'stop') AND testcontent is NULL
        '''
        cursor.execute(query, (test_unit_id,))
        result = cursor.fetchone()
        if result:
            return JsonResponse({"error": "status is exist"}) 
        else:
            cursor.execute("INSERT INTO test_unit_tasks (test_unit_id, status, add_time) VALUES (%s, %s, %s)", (test_unit_id, "running", timenow()))    
            return JsonResponse({"finaldata": "successful"})  
    else:
        return JsonResponse({"error": "status is changed"}) 

'''
[serial_number, tool_name, tool_version,
        bios_version, image_version, os_version, wifi,
        bt_name, bt_version, lan_name, lan_version, dock_lan_name, dock_lan_version,
        nfc_name, nfc_version, dock_name, dock_version, wlan_name, wlan_version, 
        usb_gnss_name, usb_gnss_version, 
        mcd_name, mcd_version, ude_name, ude_version, pcie_gnss_name, pcie_gnss_version, mbim_name, mbim_version, qmux_name, qmux_version, 
        wwannet_gnss_name, wwannet_gnss_version]= result
'''

# @with_db_connection 
# def machine_status_report(cursor, request):
#     query = f'''
#     WITH task_unit_data AS(
#     SELECT *
#         FROM unit_task
#         WHERE finish_time IS NOT NULL
#         ORDER BY finish_time DESC
#     )
#     SELECT pi.codename, ul.phase, tul.serial_number, tul.status, tul.remark, 
#     tud.request_info->>'tool_name', tud.request_info->>'tool_version',
#     tud.uut_info->>'BIOS_Version',
#     tud.uut_info->>'Image_Version',
#     tud.uut_info->>'OS_Version',
#     tud.uut_info->'WLAN'->>'Connected_WLAN_AP',
#     tud.uut_info->'BT'->>'BT_DeviceName', tud.uut_info->'BT'->>'BT_Driver_Version', 
#     tud.uut_info->'LAN'->>'LAN_DeviceName', tud.uut_info->'LAN'->>'LAN_Driver_Version', tud.uut_info->'LAN'->>'DOCK_LAN_DeviceName', tud.uut_info->'LAN'->>'DOCK_LAN_Driver_Version',
#     tud.uut_info->'NFC'->>'NFC_DeviceName', tud.uut_info->'NFC'->>'NFC_Driver_Version', 
#     tud.uut_info->'DOCK'->>'DOCK_DeviceName', tud.uut_info->'DOCK'->>'DOCK_Driver_Version',
#     tud.uut_info->'WLAN'->>'WLAN_DeviceName', tud.uut_info->'WLAN'->>'WLAN_Driver_Version',
#     tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_Driver_Version',
#     tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_Driver_Version',
#     tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_Driver_Version',
#     tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_Driver_Version',
#     tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_Version',
#     tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_Driver_Version',
#     tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_Driver_Version',
#     (tud.result_info->'s0'->'Idle'->>'count')::text || ' ' || (tud.result_info->'s0'->'Idle'->>'unit')::text AS s0_idle,
#     (tud.result_info->'s0'->'AirplaneMode'->>'count')::text || ' ' || (tud.result_info->'s0'->'AirplaneMode'->>'unit')::text AS s0_airplanemode,
#     (tud.result_info->'s0'->'OnlineStreaming-Test'->>'count')::text || ' ' || (tud.result_info->'s0'->'OnlineStreaming-Test'->>'unit')::text AS s0_onlinestreaming_test,
#     tud.result_info->'restart',
#     tud.result_info->'s4',
#     tud.result_info->'s0i3',
#     tud.result_info->'s0i3tos4',
#     tud.result_info->'total',
#     tud.finish_time

#     FROM test_unit_list AS tul
#     LEFT JOIN platform_info AS pi ON tul.platform_id = pi.id
#     LEFT JOIN unit_list AS ul ON tul.serial_number = ul.serial_number
#     LEFT JOIN task_unit_data AS tud ON tul.id = tud.test_unit_id
#     '''
#     cursor.execute(query)
#     rows = cursor.fetchall()
#     if rows:
#         print(rows)
#         machine_list = []
#         for row in rows:
#             machine_list_data ={
#                 "platform":row[0],
#                 "phase":row[1],
#                 "serial_number":row[2],
#                 "status":row[3],
#                 "remark":row[4],
#                 "tool_name":row[5],"tool_version":row[6],
#                 "bios_version":row[7],"image_version":row[8],"os_version":row[9],"wifi":row[10],
#                 "bt_name":row[11],"bt_version":row[12],"lan_name":row[13],"lan_version":row[14],
#                 "dock_lan_name":row[15],"dock_lan_version":row[16],"nfc_name":row[17],"nfc_version":row[18],
#                 "dock_name":row[19],"dock_version":row[20],"wlan_name":row[21],"wlan_version":row[22],
#                 "usb_gnss_name":row[23],"usb_gnss_version":row[24],
#                 "mcd_name":row[25],"mcd_version":row[26],"ude_name":row[27],"ude_version":row[28],
#                 "pcie_gnss_name":row[29],"pcie_gnss_version":row[30],"mbim_name":row[31],"mbim_version":row[32],
#                 "qmux_name":row[33],"qmux_version":row[34],
#                 "wwannet_gnss_name":row[35],"wwannet_gnss_version":row[36],
#                 "s0_idle":row[37],"s0_airplanemode":row[38],"s0_onlinestreaming_test":row[39],
#                 "restart":row[40],"s4":row[41],"s0i3":row[42],"s0i3tos4":row[43],"total":row[44],
#                 "finish_time":row[45]
#             }
#             machine_list.append(machine_list_data)
#         return JsonResponse(machine_list, safe=False)


# standby  = s0i3
@api_view(["post"])
@csrf_exempt
@with_db_connection 
def machine_status_report(cursor, request):
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    platform = request.data.get('platform')
    print(platform, start_time, end_time)
    if platform:
        platform_set = set(platform)
        platform_condition = f"AND pi.codename IN ({', '.join(['%s'] * len(platform_set))})"
    else:
        platform_condition = ''
        platform_set = set("")  
    module = request.data.get('module')
    
    query = f'''
    SELECT pi.codename, ul.phase, tul.serial_number, tul.status, tul.remark,
    tud.request_info->>'tool_name', tud.request_info->>'tool_version',
    tud.uut_info->>'BIOS_Version',
    tud.uut_info->>'Image_Version',
    tud.uut_info->>'OS_Version',
    tud.uut_info->'WLAN'->>'Connected_WLAN_AP',
    tud.uut_info->'BT'->>'BT_DeviceName', tud.uut_info->'BT'->>'BT_Driver_Version', 
    tud.uut_info->'LAN'->>'LAN_DeviceName', tud.uut_info->'LAN'->>'LAN_Driver_Version', tud.uut_info->'LAN'->>'DOCK_LAN_DeviceName', tud.uut_info->'LAN'->>'DOCK_LAN_Driver_Version',
    tud.uut_info->'NFC'->>'NFC_DeviceName', tud.uut_info->'NFC'->>'NFC_Driver_Version', 
    tud.uut_info->'DOCK'->>'DOCK_DeviceName', tud.uut_info->'DOCK'->>'DOCK_Driver_Version',
    tud.uut_info->'WLAN'->>'WLAN_DeviceName', tud.uut_info->'WLAN'->>'WLAN_Driver_Version',
    tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_Version',
    tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_Driver_Version',
    (tud.result_info->'s0'->'Idle'->>'count')::text || ' ' || (tud.result_info->'s0'->'Idle'->>'unit')::text AS s0_idle,
    (tud.result_info->'s0'->'AirplaneMode'->>'count')::text || ' ' || (tud.result_info->'s0'->'AirplaneMode'->>'unit')::text AS s0_airplanemode,
    (tud.result_info->'s0'->'OnlineStreaming-Test'->>'count')::text || ' ' || (tud.result_info->'s0'->'OnlineStreaming-Test'->>'unit')::text AS s0_onlinestreaming_test,
    tud.result_info->'restart',
    tud.result_info->'s4',
    tud.result_info->'standby', 
    tud.result_info->'standbytos4',
    tud.result_info->'total',
    tud.start_time,
    tud.finish_time,
    tud.issue_details_array_restart,
    tud.issue_details_array_s4,
    tud.issue_details_array_s0i3,
    tud.issue_details_array_s0i3tos4,
    tud.issue_details_array_total,
    tud.uut_info->'IOT_CATM'->>'DeviceName', 
    tud.uut_info->'IOT_CATM'->>'IOT_CATM_Status',
    tut.tasks_array

    FROM test_unit_list AS tul
    LEFT JOIN platform_info AS pi ON tul.platform_id = pi.id 
    LEFT JOIN unit_list AS ul ON tul.serial_number = ul.serial_number
    LEFT JOIN (
        SELECT 
            unit_task.id,
            unit_task.test_unit_id,
            unit_task.start_time,
            unit_task.finish_time,
            unit_task.uut_info,
            unit_task.request_info,
            unit_task.result_info,
            comm_task_issue.task_id,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'restart') AS issue_details_array_restart,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 's4') AS issue_details_array_s4,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'standby') AS issue_details_array_s0i3,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'standbytos4') AS issue_details_array_s0i3tos4,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'total') AS issue_details_array_total,
            ROW_NUMBER() OVER (PARTITION BY unit_task.test_unit_id ORDER BY unit_task.finish_time DESC) AS rn
        FROM 
            unit_task
        LEFT JOIN 
            comm_task_issue ON comm_task_issue.task_id = unit_task.id
        GROUP BY 
            unit_task.id,
            unit_task.test_unit_id,
            unit_task.start_time,
            unit_task.finish_time,
            unit_task.uut_info,
            unit_task.request_info,
            unit_task.result_info,
            comm_task_issue.task_id
    ) AS tud ON tul.id = tud.test_unit_id AND tud.rn = 1
    LEFT JOIN (
        SELECT
            test_unit_id, 
            ARRAY_AGG(
                jsonb_build_object(
                    'status', status,
                    'testcontent', testcontent
                )
            ) AS tasks_array
        FROM 
            test_unit_tasks
        GROUP BY 
            test_unit_id
    ) AS tut ON tul.id = tut.test_unit_id;
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    if rows:
        machine_list = []
        for row in rows:
            machine_list_data = {
                "platform":row[0],
                "phase":row[1],
                "serial_number":row[2],
                "status":row[3],
                "remark":row[4],
                "tool_name":row[5],"tool_version":row[6],
                "bios_version":row[7],"image_version":row[8],"os_version":row[9],"wifi":row[10],
                "bt_name":row[11],"bt_version":row[12],"lan_name":row[13],"lan_version":row[14],
                "dock_lan_name":row[15],"dock_lan_version":row[16],"nfc_name":row[17],"nfc_version":row[18],
                "dock_name":row[19],"dock_version":row[20],"wlan_name":row[21],"wlan_version":row[22],
                "usb_gnss_name":row[23],"usb_gnss_version":row[24],
                "mcd_name":row[25],"mcd_version":row[26],"ude_name":row[27],"ude_version":row[28],
                "pcie_gnss_name":row[29],"pcie_gnss_version":row[30],"mbim_name":row[31],"mbim_version":row[32],
                "qmux_name":row[33],"qmux_version":row[34],
                "wwannet_gnss_name":row[35],"wwannet_gnss_version":row[36],
                "s0_idle":row[37],"s0_airplanemode":row[38],"s0_onlinestreaming_test":row[39],
                "restart":row[40],
                "s4":row[41],
                "s0i3":row[42],
                "s0i3tos4":row[43],
                "total":row[44],
                "start_time":row[45],
                "finish_time":row[46],
                "issue_restart": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"), 
                     "add_time": json.loads(data).get("add_time")
                     } for data in row[47]
                ] if row[47] is not None else None,
                "issue_s4": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"), 
                     "add_time": json.loads(data).get("add_time")
                     } for data in row[48]
                ] if row[48] is not None else None,
                "issue_s0i3": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[49]
                ]   if row[49] is not None else None,
                "issue_s0i3tos4": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[50]
                ]   if row[50] is not None else None,
                "issue_total": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[51]
                ]   if row[51] is not None else None,
                "IOT_CATM_devicename": row[52],
                "IOT_CATM_status": row[53] if row[52] == "FB520" else "",
                "task_unit_array": [
                    {"status": json.loads(data).get("status"),
                     "testcontent": json.loads(data).get("testcontent")
                    } for data in row[54]
                ]   if row[54] is not None else None,
            }
            machine_list.append(machine_list_data)
        return JsonResponse(machine_list, safe=False)

@api_view(["post"])
@csrf_exempt
@with_db_connection 
def filter_machine_status_report(cursor, request):
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    platform = request.data.get('platform')
    module = request.data.get('module')
    print(platform, module)
    if platform:
        platform_set = set(platform)
        platform_condition = f"AND platform_info.codename IN ({', '.join(['%s'] * len(platform_set))})"
    else:
        platform_condition = ''
        platform_set = set("")  
    
    if module:
        module_set = set(module)
        module_condition = f"AND unit_task.uut_info::text LIKE ANY(ARRAY[{', '.join(['%s'] * len(module_set))}])"
    else:
        module_condition = ''
        module_set = set("") 
    query = f'''
    SELECT pi.codename, ul.phase, tul.serial_number, tul.status, tul.remark,
    tud.request_info->>'tool_name', tud.request_info->>'tool_version',
    tud.uut_info->>'BIOS_Version',
    tud.uut_info->>'Image_Version',
    tud.uut_info->>'OS_Version',
    tud.uut_info->'WLAN'->>'Connected_WLAN_AP',
    tud.uut_info->'BT'->>'BT_DeviceName', tud.uut_info->'BT'->>'BT_Driver_Version', 
    tud.uut_info->'LAN'->>'LAN_DeviceName', tud.uut_info->'LAN'->>'LAN_Driver_Version', tud.uut_info->'LAN'->>'DOCK_LAN_DeviceName', tud.uut_info->'LAN'->>'DOCK_LAN_Driver_Version',
    tud.uut_info->'NFC'->>'NFC_DeviceName', tud.uut_info->'NFC'->>'NFC_Driver_Version', 
    tud.uut_info->'DOCK'->>'DOCK_DeviceName', tud.uut_info->'DOCK'->>'DOCK_Driver_Version',
    tud.uut_info->'WLAN'->>'WLAN_DeviceName', tud.uut_info->'WLAN'->>'WLAN_Driver_Version',
    tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_Version',
    tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_Driver_Version',
    (tud.result_info->'s0'->'Idle'->>'count')::text || ' ' || (tud.result_info->'s0'->'Idle'->>'unit')::text AS s0_idle,
    (tud.result_info->'s0'->'AirplaneMode'->>'count')::text || ' ' || (tud.result_info->'s0'->'AirplaneMode'->>'unit')::text AS s0_airplanemode,
    (tud.result_info->'s0'->'OnlineStreaming-Test'->>'count')::text || ' ' || (tud.result_info->'s0'->'OnlineStreaming-Test'->>'unit')::text AS s0_onlinestreaming_test,
    tud.result_info->'restart',
    tud.result_info->'s4',
    tud.result_info->'standby', 
    tud.result_info->'standbytos4',
    tud.result_info->'total',
    tud.start_time,
    tud.finish_time,
    tud.issue_details_array_restart,
    tud.issue_details_array_s4,
    tud.issue_details_array_s0i3,
    tud.issue_details_array_s0i3tos4,
    tud.issue_details_array_total,
    tud.uut_info->'IOT_CATM'->>'DeviceName', 
    tud.uut_info->'IOT_CATM'->>'IOT_CATM_Status'

    FROM test_unit_list AS tul
    INNER JOIN (
        SELECT *
        FROM platform_info
        WHERE 1=1 {platform_condition}
    )AS pi ON tul.platform_id = pi.id 
    LEFT JOIN unit_list AS ul ON tul.serial_number = ul.serial_number
    INNER JOIN (
        SELECT 
            unit_task.id,
            unit_task.test_unit_id,
            unit_task.start_time,
            unit_task.finish_time,
            unit_task.uut_info,
            unit_task.request_info,
            unit_task.result_info,
            comm_task_issue.task_id,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'restart') AS issue_details_array_restart,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 's4') AS issue_details_array_s4,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'standby') AS issue_details_array_s0i3,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'standbytos4') AS issue_details_array_s0i3tos4,
            ARRAY_AGG(
                jsonb_build_object(
                    'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                    'short_description', comm_task_issue.issue_short_description,
                    'failed_device_info', comm_task_issue.failed_device_info,
                    'servity', comm_task_issue.servity,
                    'add_time', comm_task_issue.add_time
                )
            ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'total') AS issue_details_array_total,
            ROW_NUMBER() OVER (PARTITION BY unit_task.test_unit_id ORDER BY unit_task.finish_time DESC) AS rn
        FROM 
            unit_task
        LEFT JOIN 
            comm_task_issue ON comm_task_issue.task_id = unit_task.id
        WHERE 
            unit_task.finish_time IS NOT NULL {module_condition} AND finish_time BETWEEN '{start_time}' AND '{end_time}'
        GROUP BY 
            unit_task.id,
            unit_task.test_unit_id,
            unit_task.start_time,
            unit_task.finish_time,
            unit_task.uut_info,
            unit_task.request_info,
            unit_task.result_info,
            comm_task_issue.task_id
    ) AS tud ON tul.id = tud.test_unit_id AND tud.rn = 1;
    '''
    cursor.execute(query, tuple(platform_set) + tuple(f"%{value}%" for value in module_set))
    rows = cursor.fetchall()
    machine_list = []
    if rows:
        for row in rows:
            machine_list_data = {
                "platform":row[0],
                "phase":row[1],
                "serial_number":row[2],
                "status":row[3],
                "remark":row[4],
                "tool_name":row[5],"tool_version":row[6],
                "bios_version":row[7],"image_version":row[8],"os_version":row[9],"wifi":row[10],
                "bt_name":row[11],"bt_version":row[12],"lan_name":row[13],"lan_version":row[14],
                "dock_lan_name":row[15],"dock_lan_version":row[16],"nfc_name":row[17],"nfc_version":row[18],
                "dock_name":row[19],"dock_version":row[20],"wlan_name":row[21],"wlan_version":row[22],
                "usb_gnss_name":row[23],"usb_gnss_version":row[24],
                "mcd_name":row[25],"mcd_version":row[26],"ude_name":row[27],"ude_version":row[28],
                "pcie_gnss_name":row[29],"pcie_gnss_version":row[30],"mbim_name":row[31],"mbim_version":row[32],
                "qmux_name":row[33],"qmux_version":row[34],
                "wwannet_gnss_name":row[35],"wwannet_gnss_version":row[36],
                "s0_idle":row[37],"s0_airplanemode":row[38],"s0_onlinestreaming_test":row[39],
                "restart":row[40],
                "s4":row[41],
                "s0i3":row[42],
                "s0i3tos4":row[43],
                "total":row[44],
                "start_time":row[45],
                "finish_time":row[46],
                "issue_restart": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"), 
                     "add_time": json.loads(data).get("add_time")
                     } for data in row[47]
                ] if row[47] is not None else None,
                "issue_s4": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"), 
                     "add_time": json.loads(data).get("add_time")
                     } for data in row[48]
                ] if row[48] is not None else None,
                "issue_s0i3": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[49]
                ]   if row[49] is not None else None,
                "issue_s0i3tos4": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[50]
                ]   if row[50] is not None else None,
                "issue_total": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[51]
                ]   if row[51] is not None else None,
                "IOT_CATM_devicename": row[52],
                "IOT_CATM_status": row[53] if row[52] == "FB520" else "",
            }
            machine_list.append(machine_list_data)
        return JsonResponse({"finaldata": machine_list}, safe=False)
    else:
        return JsonResponse({"error": "null"}, safe=False)

    
@api_view(["post"])
@csrf_exempt
@with_db_connection
def filter_module(cursor, request):
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    print(start_time, end_time)
    if start_time and end_time:
        current_time = datetime.now()
        query = f'''
        WITH latest_record AS (
            SELECT DISTINCT ON (test_unit_id)
                test_unit_id,
                uut_info->'BT'->>'BT_DeviceName' AS BT_device,
                uut_info->'LAN'->>'LAN_DeviceName' AS LAN_device,
                uut_info->'LAN'->>'DOCK_LAN_DeviceName' AS DOCK_LAN_device,
                uut_info->'NFC'->>'NFC_DeviceName' AS NFC_device,
                uut_info->'DOCK'->>'DOCK_DeviceName' AS DOCK_device,
                uut_info->'WLAN'->>'WLAN_DeviceName' AS WLAN_device,
                uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_DeviceName' AS GNSS_device,
                uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_DeviceName' AS MCD_device,
                uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_DeviceName' AS UDE_device, 
                uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_DeviceName' AS GNSS_device_pcie,
                uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_DeviceName' AS MBIM_device,
                uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_DeviceName' AS QMUX_device,
                uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_DeviceName' AS GNSS_device_wwannet
            FROM unit_task
            WHERE finish_time IS NOT NULL
            AND finish_time BETWEEN '{start_time}' AND '{end_time}'
            ORDER BY test_unit_id, finish_time DESC
        )
        SELECT
            json_agg(DISTINCT BT_device) FILTER (WHERE BT_device IS NOT NULL AND BT_device <> '') AS BT_result,
            json_agg(DISTINCT LAN_device) FILTER (WHERE LAN_device IS NOT NULL AND LAN_device <> '') AS LAN_result,
            json_agg(DISTINCT DOCK_LAN_device) FILTER (WHERE DOCK_LAN_device IS NOT NULL AND DOCK_LAN_device <> '') AS DOCK_LAN_result,
            json_agg(DISTINCT NFC_device) FILTER (WHERE NFC_device IS NOT NULL AND NFC_device <> '') AS NFC_result,
            json_agg(DISTINCT DOCK_device) FILTER (WHERE DOCK_device IS NOT NULL AND DOCK_device <> '') AS DOCK_result,
            json_agg(DISTINCT WLAN_device) FILTER (WHERE WLAN_device IS NOT NULL AND WLAN_device <> '') AS WLAN_result,
            json_agg(DISTINCT GNSS_device) FILTER (WHERE GNSS_device IS NOT NULL AND GNSS_device <> '') AS GNSS_result,
            json_agg(DISTINCT MCD_device) FILTER (WHERE MCD_device IS NOT NULL AND MCD_device <> '') AS MCD_result,
            json_agg(DISTINCT UDE_device) FILTER (WHERE UDE_device IS NOT NULL AND UDE_device <> '') AS UDE_result,
            json_agg(DISTINCT GNSS_device_pcie) FILTER (WHERE GNSS_device_pcie IS NOT NULL AND GNSS_device_pcie <> '') AS GNSS_pcie_result,
            json_agg(DISTINCT MBIM_device) FILTER (WHERE MBIM_device IS NOT NULL AND MBIM_device <> '') AS MBIM_result,
            json_agg(DISTINCT QMUX_device) FILTER (WHERE QMUX_device IS NOT NULL AND QMUX_device <> '') AS QMUX_result,
            json_agg(DISTINCT GNSS_device_wwannet) FILTER (WHERE GNSS_device_wwannet IS NOT NULL AND GNSS_device_wwannet <> '') AS GNSS_wwannet_result
        FROM latest_record;
        '''
        cursor.execute(query, (start_time,) + (end_time,))
        row = cursor.fetchone()
        if row:
            machine_list ={
                "bt":row[0],
                "lan":row[1],
                "dock_lan":row[2],
                "nfc":row[3],
                "dock":row[4],
                "wlan":row[5],
                "usb_gnss":row[6],
                "mcd":row[7],
                "ude":row[8],
                "pcie_gnss":row[9],
                "mbim":row[10],
                "qmux":row[11],
                "wwannet_gnss":row[12],
            }
            return JsonResponse(machine_list, safe=False)
        else :
            machine_list = { "data": "no data" } 
            return JsonResponse(machine_list, safe=False)
    else:
        machine_list = { "data": "請輸入時間" } 
        return JsonResponse(machine_list, safe=False)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def filter_platform(cursor, request):
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    print(start_time, end_time)
    if start_time and end_time:
        query = f'''
            SELECT DISTINCT ON (pi.codename) pi.codename
            FROM unit_task
            LEFT JOIN test_unit_list ON unit_task.test_unit_id = test_unit_list.id
            LEFT JOIN platform_info AS pi ON test_unit_list.platform_id = pi.id
            WHERE unit_task.finish_time IS NOT NULL AND finish_time BETWEEN '{start_time}' AND '{end_time}'
        '''
        cursor.execute(query, (start_time,) + (end_time,))
        rows = cursor.fetchall()
        platform = {'platform': [row[0] for row in rows if row[0] is not None and row[0] != ""]}
        return JsonResponse(platform, safe=False)
    else:
        machine_list = { "data": "請輸入時間" }
        return JsonResponse(machine_list, safe=False)
    

@api_view(["post"])
@csrf_exempt
@with_db_connection
def filter_version(cursor, request):
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    print(start_time, end_time)
    if start_time and end_time:
        current_time = datetime.now()
        query = f'''
        WITH latest_record AS (
            SELECT DISTINCT ON (test_unit_id)
                test_unit_id,
                uut_info->'BT'->>'BT_DeviceName' AS BT_device,
                uut_info->'LAN'->>'LAN_DeviceName' AS LAN_device,
                uut_info->'LAN'->>'DOCK_LAN_DeviceName' AS DOCK_LAN_device,
                uut_info->'NFC'->>'NFC_DeviceName' AS NFC_device,
                uut_info->'DOCK'->>'DOCK_DeviceName' AS DOCK_device,
                uut_info->'WLAN'->>'WLAN_DeviceName' AS WLAN_device,
                uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_DeviceName' AS GNSS_device,
                uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_DeviceName' AS MCD_device,
                uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_DeviceName' AS UDE_device,
                uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_DeviceName' AS GNSS_device_pcie,
                uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_DeviceName' AS MBIM_device,
                uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_DeviceName' AS QMUX_device,
                uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_DeviceName' AS GNSS_device_wwannet
            FROM unit_task
            WHERE finish_time IS NOT NULL
            AND finish_time BETWEEN '{start_time}' AND '{end_time}'
            ORDER BY test_unit_id, finish_time DESC
        )
        SELECT
            json_agg(DISTINCT BT_device) FILTER (WHERE BT_device IS NOT NULL AND BT_device <> '') AS BT_result,
            json_agg(DISTINCT LAN_device) FILTER (WHERE LAN_device IS NOT NULL AND LAN_device <> '') AS LAN_result,
            json_agg(DISTINCT DOCK_LAN_device) FILTER (WHERE DOCK_LAN_device IS NOT NULL AND DOCK_LAN_device <> '') AS DOCK_LAN_result,
            json_agg(DISTINCT NFC_device) FILTER (WHERE NFC_device IS NOT NULL AND NFC_device <> '') AS NFC_result,
            json_agg(DISTINCT DOCK_device) FILTER (WHERE DOCK_device IS NOT NULL AND DOCK_device <> '') AS DOCK_result,
            json_agg(DISTINCT WLAN_device) FILTER (WHERE WLAN_device IS NOT NULL AND WLAN_device <> '') AS WLAN_result,
            json_agg(DISTINCT GNSS_device) FILTER (WHERE GNSS_device IS NOT NULL AND GNSS_device <> '') AS GNSS_result,
            json_agg(DISTINCT MCD_device) FILTER (WHERE MCD_device IS NOT NULL AND MCD_device <> '') AS MCD_result,
            json_agg(DISTINCT UDE_device) FILTER (WHERE UDE_device IS NOT NULL AND UDE_device <> '') AS UDE_result,
            json_agg(DISTINCT GNSS_device_pcie) FILTER (WHERE GNSS_device_pcie IS NOT NULL AND GNSS_device_pcie <> '') AS GNSS_pcie_result,
            json_agg(DISTINCT MBIM_device) FILTER (WHERE MBIM_device IS NOT NULL AND MBIM_device <> '') AS MBIM_result,
            json_agg(DISTINCT QMUX_device) FILTER (WHERE QMUX_device IS NOT NULL AND QMUX_device <> '') AS QMUX_result,
            json_agg(DISTINCT GNSS_device_wwannet) FILTER (WHERE GNSS_device_wwannet IS NOT NULL AND GNSS_device_wwannet <> '') AS GNSS_wwannet_result
        FROM latest_record;
        '''
        cursor.execute(query, (start_time,) + (end_time,))
        row = cursor.fetchone()
        if row:
            machine_list ={
                "bt":row[0],
                "lan":row[1],
                "dock_lan":row[2],
                "nfc":row[3],
                "dock":row[4],
                "wlan":row[5],
                "usb_gnss":row[6],
                "mcd":row[7],
                "ude":row[8],
                "pcie_gnss":row[9],
                "mbim":row[10],
                "qmux":row[11],
                "wwannet_gnss":row[12],
            }
            return JsonResponse(machine_list, safe=False)
        else :
            machine_list = { "data": "no data" } 
            return JsonResponse(machine_list, safe=False)
    else:
        machine_list = { "data": "請輸入時間" } 
        return JsonResponse(machine_list, safe=False)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def download_cth(cursor, request):
    version = request.data.get('version')
    file_name =f'https://hp.sharepoint.com/:u:/r/teams/CommunicationsTechnologyTeam/Dogfood/IUR/test_folder_Bill/{version}.zip'
    return JsonResponse({'url': file_name}) 

@api_view(["post"])
@csrf_exempt
@with_db_connection
def create_task(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    task_list = request.data.get('task')
    machine_list = request.data.get('machine')
    if not task_list or not machine_list:
        return JsonResponse({'error': 'Please enter task and machine'})
    for machine in machine_list:
        query = f'''
            SELECT tul.status
            FROM test_unit_list AS tul
            WHERE tul.serial_number IN (%s)
        '''
        cursor.execute(query, (machine,))
        result = cursor.fetchone()
        if result is None:
            return JsonResponse({'error': 'Machine not found'})
        else:
            [status] = result
            if status != 'idle':
                return JsonResponse({'error': 'Machine is not idle'})
    for machine in machine_list:
        query = f'''
            SELECT id
            FROM test_unit_list AS tul
            WHERE tul.serial_number IN (%s)
        '''
        cursor.execute(query, (machine,))
        result = cursor.fetchone()
        [test_unit_id] = result
        for task in task_list:
            update_time = timenow()
            task_json = json.dumps(task)
            cursor.execute("INSERT INTO test_unit_tasks (test_unit_id, status, testcontent, add_time) VALUES (%s, %s, %s, %s) RETURNING id" , (test_unit_id, "running", task_json, update_time))
    
    return JsonResponse({'finaldata': 'successful'})

import tempfile
@api_view(["post"])
@csrf_exempt
@with_db_connection 
def select_machine_report(cursor, request):
    serial_number = json.loads(request.data.get('serial_number'))
    print(serial_number)
    if serial_number:
        serial_number_set = set(serial_number)
        serial_number_condition = f"AND tul.serial_number IN ({', '.join(['%s'] * len(serial_number_set))})"
    else:
        serial_number_set = set("")
        serial_number_condition = ''
          

    query = f'''
    SELECT pi.codename, ul.phase, tul.serial_number, tul.status, tul.remark,
    tud.request_info->>'tool_name', tud.request_info->>'tool_version',
    tud.uut_info->>'BIOS_Version',
    tud.uut_info->>'Image_Version',
    tud.uut_info->>'OS_Version',
    tud.uut_info->'WLAN'->>'Connected_WLAN_AP',
    tud.uut_info->'BT'->>'BT_DeviceName', tud.uut_info->'BT'->>'BT_Driver_Version', 
    tud.uut_info->'LAN'->>'LAN_DeviceName', tud.uut_info->'LAN'->>'LAN_Driver_Version', tud.uut_info->'LAN'->>'DOCK_LAN_DeviceName', tud.uut_info->'LAN'->>'DOCK_LAN_Driver_Version',
    tud.uut_info->'NFC'->>'NFC_DeviceName', tud.uut_info->'NFC'->>'NFC_Driver_Version', 
    tud.uut_info->'DOCK'->>'DOCK_DeviceName', tud.uut_info->'DOCK'->>'DOCK_Driver_Version',
    tud.uut_info->'WLAN'->>'WLAN_DeviceName', tud.uut_info->'WLAN'->>'WLAN_Driver_Version',
    tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'USB'->'GNSS'->>'GNSS_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MCD'->>'MCD_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'UDE'->>'UDE_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'GNSS'->>'GNSS_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'MBIM'->>'MBIM_Version',
    tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'QMUX'->>'QMUX_Driver_Version',
    tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_DeviceName', tud.uut_info->'WWAN'->'PCIE'->'WWANNET'->>'GNSS_Driver_Version',
    (tud.result_info->'s0'->'Idle'->>'count')::text || ' ' || (tud.result_info->'s0'->'Idle'->>'unit')::text AS s0_idle,
    (tud.result_info->'s0'->'AirplaneMode'->>'count')::text || ' ' || (tud.result_info->'s0'->'AirplaneMode'->>'unit')::text AS s0_airplanemode,
    (tud.result_info->'s0'->'OnlineStreaming-Test'->>'count')::text || ' ' || (tud.result_info->'s0'->'OnlineStreaming-Test'->>'unit')::text AS s0_onlinestreaming_test,
    tud.result_info->'restart',
    tud.result_info->'s4',
    tud.result_info->'standby', 
    tud.result_info->'standbytos4',
    tud.result_info->'total',
    tud.start_time,
    tud.finish_time,
    tud.issue_details_array_restart,
    tud.issue_details_array_s4,
    tud.issue_details_array_s0i3,
    tud.issue_details_array_s0i3tos4,
    tud.issue_details_array_total,
    tud.uut_info->'IOT_CATM'->>'DeviceName', 
    tud.uut_info->'IOT_CATM'->>'IOT_CATM_Status',
    tut.tasks_array

    FROM
        test_unit_list AS tul
        LEFT JOIN platform_info AS pi ON tul.platform_id = pi.id 
        LEFT JOIN unit_list AS ul ON tul.serial_number = ul.serial_number
        LEFT JOIN (
            SELECT 
                unit_task.id,
                unit_task.test_unit_id,
                unit_task.start_time,
                unit_task.finish_time,
                unit_task.uut_info,
                unit_task.request_info,
                unit_task.result_info,
                comm_task_issue.task_id,
                ARRAY_AGG(
                    jsonb_build_object(
                        'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                        'short_description', comm_task_issue.issue_short_description,
                        'failed_device_info', comm_task_issue.failed_device_info,
                        'servity', comm_task_issue.servity,
                        'add_time', comm_task_issue.add_time
                    )
                ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'restart') AS issue_details_array_restart,
                ARRAY_AGG(
                    jsonb_build_object(
                        'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                        'short_description', comm_task_issue.issue_short_description,
                        'failed_device_info', comm_task_issue.failed_device_info,
                        'servity', comm_task_issue.servity,
                        'add_time', comm_task_issue.add_time
                    )
                ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 's4') AS issue_details_array_s4,
                ARRAY_AGG(
                    jsonb_build_object(
                        'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                        'short_description', comm_task_issue.issue_short_description,
                        'failed_device_info', comm_task_issue.failed_device_info,
                        'servity', comm_task_issue.servity,
                        'add_time', comm_task_issue.add_time
                    )
                ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'standby') AS issue_details_array_s0i3,
                ARRAY_AGG(
                    jsonb_build_object(
                        'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                        'short_description', comm_task_issue.issue_short_description,
                        'failed_device_info', comm_task_issue.failed_device_info,
                        'servity', comm_task_issue.servity,
                        'add_time', comm_task_issue.add_time
                    )
                ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'standbytos4') AS issue_details_array_s0i3tos4,
                ARRAY_AGG(
                    jsonb_build_object(
                        'issue_detail', comm_task_issue.issue_info ->> 'issue_detail',
                        'short_description', comm_task_issue.issue_short_description,
                        'failed_device_info', comm_task_issue.failed_device_info,
                        'servity', comm_task_issue.servity,
                        'add_time', comm_task_issue.add_time
                    )
                ) FILTER (WHERE comm_task_issue.issue_info ->> 'power_state' = 'total') AS issue_details_array_total,
                ROW_NUMBER() OVER (PARTITION BY unit_task.test_unit_id ORDER BY unit_task.finish_time DESC) AS rn
            FROM 
                unit_task
            LEFT JOIN 
                comm_task_issue ON comm_task_issue.task_id = unit_task.id
            GROUP BY 
                unit_task.id,
                unit_task.test_unit_id,
                unit_task.start_time,
                unit_task.finish_time,
                unit_task.uut_info,
                unit_task.request_info,
                unit_task.result_info,
                comm_task_issue.task_id
        ) AS tud ON tul.id = tud.test_unit_id AND tud.rn = 1
        LEFT JOIN (
            SELECT
                test_unit_id, 
                ARRAY_AGG(
                    jsonb_build_object(
                        'status', status,
                        'testcontent', testcontent
                    )
                ) AS tasks_array
            FROM 
                test_unit_tasks
            GROUP BY 
                test_unit_id
        ) AS tut ON tul.id = tut.test_unit_id
    WHERE
        1=1
        {serial_number_condition};
    '''
    cursor.execute(query, tuple(serial_number_set))
    rows = cursor.fetchall()
    if rows:
        machine_list = []
        for row in rows:
            machine_list_data = {
                "platform":row[0],
                "phase":row[1],
                "serial_number":row[2],
                "status":row[3],
                "remark":row[4],
                "tool_name":row[5],"tool_version":row[6],
                "bios_version":row[7],"image_version":row[8],"os_version":row[9],"wifi":row[10],
                "bt_name":row[11],"bt_version":row[12],"lan_name":row[13],"lan_version":row[14],
                "dock_lan_name":row[15],"dock_lan_version":row[16],"nfc_name":row[17],"nfc_version":row[18],
                "dock_name":row[19],"dock_version":row[20],"wlan_name":row[21],"wlan_version":row[22],
                "usb_gnss_name":row[23],"usb_gnss_version":row[24],
                "mcd_name":row[25],"mcd_version":row[26],"ude_name":row[27],"ude_version":row[28],
                "pcie_gnss_name":row[29],"pcie_gnss_version":row[30],"mbim_name":row[31],"mbim_version":row[32],
                "qmux_name":row[33],"qmux_version":row[34],
                "wwannet_gnss_name":row[35],"wwannet_gnss_version":row[36],
                "s0_idle":row[37],"s0_airplanemode":row[38],"s0_onlinestreaming_test":row[39],
                "restart":row[40],
                "s4":row[41],
                "s0i3":row[42],
                "s0i3tos4":row[43],
                "total":row[44],
                "start_time":row[45],
                "finish_time":row[46],
                "issue_restart": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"), 
                     "add_time": json.loads(data).get("add_time")
                     } for data in row[47]
                ] if row[47] is not None else None,
                "issue_s4": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"), 
                     "add_time": json.loads(data).get("add_time")
                     } for data in row[48]
                ] if row[48] is not None else None,
                "issue_s0i3": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[49]
                ]   if row[49] is not None else None,
                "issue_s0i3tos4": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[50]
                ]   if row[50] is not None else None,
                "issue_total": [
                    {"servity": json.loads(data).get("servity"),
                     "short_description": json.loads(data).get("short_description"),
                     "issue_detail": json.loads(data).get("issue_detail"),
                     "failed_device_info": json.loads(data).get("failed_device_info"),
                     "add_time": json.loads(data).get("add_time")
                    } for data in row[51]
                ]   if row[51] is not None else None,
                "IOT_CATM_devicename": row[52],
                "IOT_CATM_status": row[53] if row[52] == "FB520" else "",
                "task_unit_array": [
                    {"status": json.loads(data).get("status"),
                     "testcontent": json.loads(data).get("testcontent")
                    } for data in row[54]
                ]   if row[54] is not None else None,
            }
            machine_list.append(machine_list_data)
        machine_count = len(serial_number)    
        total_restart = sum(int(machine_data["restart"].strip().strip('"')) if machine_data["restart"] and machine_data["restart"] != '"null"' else 0 for machine_data in machine_list)
        total_s4 = sum(int(machine_data["s4"].strip().strip('"')) if machine_data["s4"] and machine_data["s4"] != '"null"' else 0 for machine_data in machine_list)
        total_s0i3 = sum(int(machine_data["s0i3"].strip().strip('"')) if machine_data["s0i3"] and machine_data["s0i3"] != '"null"' else 0 for machine_data in machine_list)
        total_s0i3tos4 = sum(int(machine_data["s0i3tos4"].strip().strip('"')) if machine_data["s0i3tos4"] and machine_data["s0i3tos4"] != '"null"' else 0 for machine_data in machine_list)
        total = sum(int(machine_data["total"].strip().strip('"')) if machine_data["total"] and machine_data["total"] != '"null"' else 0 for machine_data in machine_list)
        # idle = sum(int(machine_data["s0_idle"].split()[0].strip().strip('"')) for machine_data in machine_list if machine_data["s0_idle"] is not None)
        template = get_template("polls/machine_report.html")
        print(machine_count, total_restart, total_s4, total_s0i3, total_s0i3tos4, total)
        context = {
            'machine_count': machine_count,
            'total_restart': total_restart,
            'total_s4': total_s4,
            'total_s0i3': total_s0i3,
            'total_s0i3tos4': total_s0i3tos4,
            'total': total,
        }
        html_content = template.render(context)
        temp_dir = tempfile.mkdtemp()
        file_name = "machine_report.html"
        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return FileResponse(open(file_path, 'rb'))