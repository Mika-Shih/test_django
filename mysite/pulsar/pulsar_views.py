from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse, FileResponse, StreamingHttpResponse
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from datetime import datetime, timedelta
import psycopg2
import pytz #時間區域
from dateutil.parser import parse #時間字串改回時間 用於時間比較
import uuid #亂數碼
import json, os, time
import inspect #取得對象訊息/代碼可讀
#清除緩存
from django.views.decorators.cache import cache_control
#跨站偽造
from django.views.decorators.csrf import csrf_exempt

from django.db import connection
from user.token import LoginRequiredMiddleware #request.uesr_id
from sharepoint import sharepoint_views as sharepoint_views
from log import log_views as log_views
from user import user_views as user_views

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    
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

    
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def pulsar(request):
    return render(request, "polls/pulsar.html")

def add_device_tool_list(request):
    return render(request, "polls/add_device_tool_list.html")
    
def add_version(request):
    return render(request, "polls/add_version.html")

@api_view(["post"])
@csrf_exempt 
@with_db_connection
def create_device_tool(cursor, request):
    shortname = request.data.get('shortname')
    longname = request.data.get('longname')
    category = request.data.get('category')
    subdevice = request.data.get('subdevice')
    hw_id = request.data.get('hw_id')
    print(shortname, longname, category, subdevice, hw_id)
    if shortname:
        query = f'''
        SELECT id 
        FROM device_tool_list AS dtl
        WHERE dtl.short_name IN (%s)
        '''
        cursor.execute(query, (shortname,)) 
        result_shortname=cursor.fetchone() 
        if result_shortname is None:
            if (category == 'TOOL'):
                cursor.execute("INSERT INTO device_tool_list (short_name, category, sub_device) VALUES (%s, %s, %s) RETURNING id", (shortname, category, subdevice))  
                response_data = {
                'redirect_url': '/pulsar/pulsar/',  
                }
                return JsonResponse(response_data) 
            else:
                if longname and hw_id:
                    #hw_id_condition = f"AND (dl.hardware_id->>'hw_id') = %s" 
                    hw_id_condition = f"AND dtl.hardware_id->'hw_id' ? %s"
                    query = f'''
                    SELECT id
                    FROM device_tool_list AS dtl
                    WHERE 1=1 {hw_id_condition} 
                    '''
                    cursor.execute(query, (hw_id,)) 
                    result=cursor.fetchone()

                    if result is None:
                        shortname_condition = f"AND dtl.short_name IN (%s)"
                        longname_condition = f"AND dtl.long_name IN (%s)"
                        subdevice_condition = f"AND dtl.sub_device IN (%s)"
                        query = f'''
                        SELECT id, hardware_id
                        FROM device_tool_list AS dtl
                        WHERE 1=1 {shortname_condition} {longname_condition} {subdevice_condition}
                        '''
                        cursor.execute(query, (shortname,) + (longname,) + (subdevice,))
                        result_hwid=cursor.fetchone()
                        if result_hwid:
                            query = f'''
                            UPDATE device_tool_list
                            SET hardware_id = jsonb_set(
                                hardware_id,
                                '{{hw_id}}', 
                                (hardware_id->'hw_id') || jsonb_build_array('{hw_id}')
                            )
                            WHERE id = %s;
                            '''
                            cursor.execute(query, (result_hwid[0],))
                            '''
                            SET hardware_id = jsonb_set(    jsonb_set是sq內置函數
                                hardware_id,                hardware_id為欄位名稱
                                '{{hw_id}}',         '{{hw_id}}'為位置 = 這個key的陣列   '{{hw_id}}->>0' = 這個key第一個值
                                (hardware_id->'hw_id') || jsonb_build_array('{hw_id}')    (hardware_id->'hw_id')取出陣列 和(||) 加入{hw_id}這筆資料
                            )
                            '''
                        else:    
                            hardware_id = {
                                "hw_id": [hw_id]           
                            }
                            hw_id_json = json.dumps(hardware_id)
                            cursor.execute("INSERT INTO device_tool_list (short_name, long_name, category, sub_device, hardware_id) VALUES (%s, %s, %s, %s, %s) RETURNING id", (shortname, longname, category, subdevice, hw_id_json))
                            new_record_id = cursor.fetchone()[0]
                            print(new_record_id)    
                        response_data = {
                        'redirect_url': '/pulsar/pulsar/',  
                        }
                        return JsonResponse(response_data)    
                    else:
                        response_data = {
                        'error': 'HW_ID 已存在',  # 替換成實際的重定向 URL
                        }
                        return JsonResponse(response_data)  
                else:
                    response_data = {
                    'error': '欄位不可為空',  
                    }
                    return JsonResponse(response_data)    
        else:
            response_data = {
            'error': 'shortname名稱已有',  
            }
            return JsonResponse(response_data)   
    else:
        response_data = {
        'error': '欄位不可為空',  
        }
        return JsonResponse(response_data)

@with_db_connection  
def select_short_name(cursor, request):
    query = '''
    SELECT DISTINCT short_name
    FROM device_tool_list
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    short_name = {'short_name': [row[0] for row in rows]}
    return JsonResponse(short_name)


@api_view(["post"])
@csrf_exempt
@with_db_connection 
def select_long_name(cursor, request):
    shortname = request.data.get('shortname')
    if shortname:
        shortname_set = set(shortname)  #set送進來的數值  要是["ABC"] 才會變成 {"ABC"}   /    如果送ABC就會變成{"A","B","C"}
        shortname_condition = f"AND dtl.short_name IN ({', '.join(['%s'] * len(shortname_set))})"
    else:
        shortname_set = set("")
        shortname_condition = ""
    query = f'''
    SELECT DISTINCT long_name
    FROM device_tool_list AS dtl
    WHERE 1=1 {shortname_condition}
    '''
    cursor.execute(query, (tuple(shortname_set)))
    rows = cursor.fetchall()
    long_name = {'long_name': [row[0] for row in rows]}
    return JsonResponse(long_name)
    

@api_view(["post"])
@csrf_exempt
@with_db_connection  
def select_subdevice(cursor, request):
    short_name = request.data.get('shortname')
    long_name = request.data.get('longname')
    if short_name:
        short_name_set = set(short_name)
        short_name_condition = f"AND dtl.short_name IN ({', '.join(['%s'] * len(short_name_set))})"
    else:
        short_name_set = set("")
        short_name_condition = ""
    if long_name:
        long_name_set = set(long_name)
        long_name_condition = f"AND dtl.long_name IN ({', '.join(['%s'] * len(long_name_set))})"
    else:
        long_name_set = set("")
        long_name_condition = ""
    query = f'''
    SELECT DISTINCT sub_device
    FROM device_tool_list AS dtl
    WHERE 1=1 {short_name_condition} {long_name_condition}
    '''
    cursor.execute(query, tuple(short_name_set) + tuple(long_name_set))
    rows = cursor.fetchall()
    subdevice = {'subdevice': [row[0] for row in rows]}
    return JsonResponse(subdevice)


@api_view(["post"])
@csrf_exempt 
@parser_classes([MultiPartParser]) 
@with_db_connection
def create_version(cursor, request):
    user = request.user_id
    shortname = json.loads(request.data.get('shortname'))
    longname = json.loads(request.data.get('longname'))
    subdevice = json.loads(request.data.get('subdevice'))
    packageversion = json.loads(request.data.get('package_version'))
    detailversion = json.loads(request.data.get('detail_version'))
    uploaded_file = request.FILES.get('file')
    if shortname and longname and subdevice and packageversion and detailversion and uploaded_file:
        packageversion_condition = f"AND dv.version->>%s IS NOT NULL"
        query = f'''
        SELECT id
        FROM deliverable_version AS dv
        WHERE 1=1 {packageversion_condition}
        '''
        cursor.execute(query, (packageversion,))
        result_data = cursor.fetchone()
        print(shortname, longname, subdevice, packageversion, detailversion)
        if result_data is None:
            shortname_condition = f"AND dtl.short_name IN (%s)"
            long_name_condition = f"AND dtl.long_name IN (%s)"
            sub_device_condition = f"AND dtl.sub_device IN (%s)"
            query = f'''
            SELECT id
            FROM device_tool_list AS dtl
            WHERE 1=1 {shortname_condition} {long_name_condition} {sub_device_condition}
            '''
            cursor.execute(query, (shortname,)+ (longname,) + (subdevice,))
            result = cursor.fetchone()
            device_tool_id = result[0]
            last_update_time = timenow()
            version = {
                packageversion : detailversion
            }
            version_json = json.dumps(version)
            cursor.execute("INSERT INTO deliverable_version (device_tool_id, version, update_time) VALUES (%s, %s, %s)", (device_tool_id, version_json, last_update_time))
            
            if uploaded_file:
                new_filename = f'{packageversion}.zip'
                sharepoint_views.sharepoint_upload_file(user, uploaded_file = uploaded_file, file_name = new_filename)
            print("OK")
            return JsonResponse({'finaldata': 'successful'})
        else:
            return JsonResponse({'error': 'packageversion 已存在'})  
    else:
        return JsonResponse({'error': '請填寫完整 資料不可為空'}) 
    
@api_view(["post"])
@csrf_exempt
@with_db_connection
def select_hardware_id(cursor, request):
    shortname = request.data.get('shortname')
    longname = request.data.get('longname')
    subdevice = request.data.get('subdevice')
    print(shortname, longname, subdevice)
    shortname_condition = ""
    if shortname:
        shortname_set = set(shortname)
        shortname_placeholders = ', '.join(['%s'] * len(shortname_set))
        shortname_condition = f"AND dtl.short_name IN ({shortname_placeholders})"
    else:
        shortname_set = set("")
    longname_condition = ""
    if longname:
        longname_set = set(longname)
        longname_placeholders = ', '.join(['%s'] * len(longname_set))
        longname_condition = f"AND dtl.long_name IN ({longname_placeholders})"
    else:
        longname_set = set("")
    subdevice_condition = ""
    if subdevice:
        subdevice_set = set(subdevice)
        subdevice_placeholders = ', '.join(['%s'] * len(subdevice_set))
        subdevice_condition = f"AND dtl.sub_device IN ({subdevice_placeholders})"
    else:   
        subdevice_set = set("")

    query = f'''
    SELECT short_name, long_name, category, sub_device, hardware_id->>'hw_id'
    FROM device_tool_list AS dtl
    WHERE 1=1 {shortname_condition} {longname_condition} {subdevice_condition}
    ''' 
    cursor.execute(query, tuple(shortname_set) + tuple(longname_set) + tuple(subdevice_set))
    rows = cursor.fetchall()
    if rows:
        hardware_id = []
        for row in rows:
            hardware_id_data = {
                'short name': row[0],
                'long name': row[1],
                'category': row[2],
                'sub device': row[3],
                'hardware ID': row[4]
            }
            print(row[4])
            hardware_id.append(hardware_id_data)
        response_data = {
            'hardware_id': hardware_id
            }       
        print(response_data)    
        return JsonResponse(response_data)
    else:
        response_data = {
            'error': '無匹配資料'
            }
        print(response_data)
        return JsonResponse(response_data)
    
@api_view(["post"])
@csrf_exempt
@with_db_connection
def select_version(cursor, request):
    shortname = request.data.get('shortname')
    longname = request.data.get('longname')
    subdevice = request.data.get('subdevice')
    if shortname:
        shortname_set = set(shortname)
        shortname_condition = f"AND dtl.short_name IN ({', '.join(['%s'] * len(shortname_set))})"
    else:
        shortname_set = set("")
        shortname_condition = ""
    if longname:
        longname_set = set(longname)
        longname_condition = f"AND dtl.long_name IN ({', '.join(['%s'] * len(longname_set))})"
    else:
        longname_set = set("")
        longname_condition = ""
    subdevice_condition = ""
    if subdevice:
        subdevice_set = set(subdevice)
        subdevice_condition = f"AND dtl.sub_device IN ({', '.join(['%s'] * len(subdevice_set))})"
    else:   
        subdevice_set = set("")
        subdevice_condition = ""

    query = f'''
    SELECT dtl.short_name, dtl.long_name, dtl.category, dtl.sub_device, jsonb_object_keys(dv.version) AS version_key, dv.version->>jsonb_object_keys(dv.version) AS version_value, dv.update_time
    FROM deliverable_version AS dv       
    INNER JOIN device_tool_list AS dtl ON dv.device_tool_id = dtl.id       
    WHERE 1=1 {shortname_condition} {longname_condition} {subdevice_condition}
    ORDER BY dv.update_time DESC
    '''
    cursor.execute(query, tuple(shortname_set) + tuple(longname_set) + tuple(subdevice_set))
    rows = cursor.fetchall()
    if rows:
        version_list = []
        for row in rows:
            version_list_data = {
                'short_name': row[0],
                'long_name': row[1],
                'category': row[2],
                'sub_device': row[3],
                'package_version': row[4],
                'detail_version': row[5],
                'update_time': row[6]
            }
            version_list.append(version_list_data)
        return JsonResponse({'finaldata': version_list})
    else:
        return JsonResponse({'error': '無匹配資料'})


@api_view(["post"])
@csrf_exempt
@with_db_connection
def select1_version(cursor, request):
    devicetool = request.data.get('devicetool')
    subdevice = request.data.get('subdevice')
    if devicetool:
        devicetool_set = set(devicetool)
    else:
        devicetool_set = set("")
    if subdevice:
        subdevice_set = set(subdevice)
    else:
        subdevice_set = set("")
    devicetool_placeholders = ', '.join(['%s'] * len(devicetool_set))
    subdevice_placeholders = ', '.join(['%s'] * len(subdevice_set))

    devicetool_condition = ""
    if devicetool:
        devicetool_condition = f"AND cdt.deliverable_name IN ({devicetool_placeholders})"

    subdevice_condition = ""
    if subdevice:
        subdevice_condition = f"AND cdt.sub_device IN ({subdevice_placeholders})"
    query = f'''
    SELECT cdt.version, cdt.deliverable_name, cdt.sub_device
    FROM comm_device_tool AS cdt
    WHERE 1=1 {devicetool_condition} {subdevice_condition}
    '''
    cursor.execute(query, tuple(devicetool_set) + tuple(subdevice_set))
    rows = cursor.fetchall()
    version_list = []
    for row in rows:
        if row[0] is not None:
            for key, value in row[0].items():
                print(f"key: {key}, value: {value}")
                version_list.append(f"deliverable_name: {row[1]}, sub_device: {row[2]}, key: {key}, value: {value}")
    response_data = {
        'version': version_list
    }
    print(response_data)
    return JsonResponse(response_data)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def download_version(cursor, request):
    version = request.data.get('version')
    file_name =f'https://hp.sharepoint.com/:u:/r/teams/CommunicationsTechnologyTeam/Dogfood/IUR/test_folder_Bill/{version}.zip'
    return JsonResponse({'url': file_name}) 

@api_view(["post"])
@csrf_exempt 
@with_db_connection   
def device_info(cursor, request):
    category = request.data.get('category')
    category_condition = f"AND cdl.category IN (%s)"
    keyword = "hardware_id"
    query = f'''
        SELECT subquery.id, json_agg(jsonb_build_object(subquery.title, subquery.content)) AS grouped_data
        FROM (
            SELECT id, jsonb_object_keys(cdl.info) AS title, cdl.info->>jsonb_object_keys(cdl.info) AS content
            FROM comm_device_tool_list AS cdl
            WHERE 1=1 {category_condition}
        ) AS subquery
        WHERE subquery.title ILIKE %s
        GROUP BY subquery.id
    '''
    cursor.execute(query, (category, f"%{keyword}%"))
    results = cursor.fetchall()
    hardware_id = []
    print(results)
    
    print("+++++++++++++++++++++++++++++")
    for result in results:
        data = " // ".join([f"{k}: {v}" for item in result[1] for k, v in item.items()])
        hardware_id_data = {
            'hardware' : data
        }
        hardware_id.append(hardware_id_data)
    response_data = {
            'hardware': hardware_id
            }
    return JsonResponse(response_data) 

# cleanup_queue_new = []
# cleanup_queue = []    
# import threading    
# def cleanup_temp_files():
#     global cleanup_queue_new
#     global cleanup_queue
#     while True:
#         if cleanup_queue:
#             for queue in cleanup_queue:
#                 temp_file_path, temp_dir = queue
#                 os.remove(temp_file_path)
#                 os.rmdir(temp_dir)
#         cleanup_queue = cleanup_queue_new
#         cleanup_queue_new = []
#         time.sleep(60)  

# cleanup_thread = threading.Thread(target=cleanup_temp_files)
# cleanup_thread.start()