from django.shortcuts import render
from django.http import JsonResponse, FileResponse
import json
from datetime import datetime
import pytz # time zone
from django.views.decorators.csrf import csrf_exempt
from O365 import Account, MSGraphProtocol
#post
from rest_framework.decorators import api_view, parser_classes
#post attach file
from rest_framework.parsers import MultiPartParser
#template 
from django.template.loader import get_template

from account import account_views as account_views
from mail import mail_views as mail_views
from log import log_views as log_views
from user import user_views as user_views
from tool import tool_views as tool_views
from sharepoint import sharepoint_views as sharepoint_views
from user.token import LoginRequiredMiddleware #request.uesr_id
from django.db import connection
import inspect

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def format_time(input_time):
    input_datetime = datetime.fromisoformat(input_time)
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    year = input_datetime.year
    month = month_names[input_datetime.month - 1]
    day = input_datetime.day
    hour = input_datetime.strftime("%I")
    minute = input_datetime.strftime("%M")
    am_pm = input_datetime.strftime("%p").lower()

    formatted_time = f"{month} {day}, {year}, {hour}:{minute} {am_pm}"
    
    return formatted_time
    
def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

@with_db_connection
def hint_machine_arrive_mail(cursor, request):
    query = f'''
        SELECT COUNT(*) OVER () AS row_count
        FROM (
            SELECT DISTINCT ON (ur.uut_id) *
            FROM unit_record AS ur
            ORDER BY ur.uut_id, ur.last_update_time DESC
        ) subquery
        JOIN (
            SELECT *
            FROM unit_list AS ul
            WHERE 1=1 AND ul.machine_arrive_mail = True
        )AS ul ON subquery.uut_id = ul.id
        WHERE subquery.uut_id NOT IN (
            SELECT ur.uut_id
            FROM unit_record AS ur
            WHERE ur.status = 'Delete' 
        ) 
        ORDER BY subquery.last_update_time DESC
        limit 1
    '''
    cursor.execute(query, (True,))
    result = cursor.fetchone()
    record_count = result[0]
    response_data = {
        'record_count': record_count
    }
    return JsonResponse(response_data)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def filter_option(cursor, request):
    finaldatas = request.data
    if finaldatas["target"]:
        targetset = set(finaldatas["target"])
        target_condition = f"AND pi.target IN ({', '.join(['%s'] * len(targetset))})"
    else:
        targetset = set("")
        target_condition = ''  
    if finaldatas["group"]:
        groupset = set(finaldatas["group"])
        group_condition = f"AND pi.product_group IN ({', '.join(['%s'] * len(groupset))})"
    else:
        groupset = set("")
        group_condition = ''
    if len(finaldatas["platform"]) > 0:
        platformset = set(finaldatas["platform"])
    else:
        platformset = set("") 
    if len(finaldatas["cycle"]) > 0:
        cycleset = set(finaldatas["cycle"])
    else:
        cycleset = set("")

    if len(finaldatas["phase"]) > 0:
        phaseset = set(finaldatas["phase"])
    else:
        phaseset = set("") 
    print(finaldatas["status"])
    if len(finaldatas["status"]) > 0:
        statusset = set(finaldatas["status"])
        if "Machine arrive mail" in statusset :
            statusset.remove("Machine arrive mail")
    else:
        statusset = set("")
    if any("Machine arrive mail" in status for status in finaldatas.get("status", [])):    
        machine_arrive_mail_set = set(["true"])     
    else:
        machine_arrive_mail_set = set("")                

    platformsearch_placeholders = ', '.join(['%s'] * len(platformset))
    cyclesearch_placeholders = ', '.join(['%s'] * len(cycleset))
    phasesearch_placeholders = ', '.join(['%s'] * len(phaseset))
    statussearch_placeholders = ', '.join(['%s'] * len(statusset))
    machine_arrive_mail_search_placeholders = ', '.join(['%s'] * len(machine_arrive_mail_set))

    platformsearch = tuple(platformset)
    cyclesearch = tuple(cycleset)
    phasesearch = tuple(phaseset)
    statussearch = tuple(statusset)

    platform_condition = ''    
    if len(platformset) > 0:
        platform_condition = f"AND pi.codename IN ({platformsearch_placeholders})"
    cycle_condition = ''
    if len(cycleset) > 0:
        cycle_condition = f"AND pi.cycle IN ({cyclesearch_placeholders})"
    phase_condition = ''
    if len(phaseset) > 0:
        phase_condition = f"AND ul.phase IN ({phasesearch_placeholders})" 
    status_condition = ''
    if len(statusset) > 0: 
            status_condition = f"AND subquery.status IN ({statussearch_placeholders})"
    machine_arrive_mail_condition = ''
    if  machine_arrive_mail_set:
        machine_arrive_mail_condition = f"AND ul.machine_arrive_mail IN ({machine_arrive_mail_search_placeholders})"
    query = f'''
        SELECT DISTINCT pi.codename, ul.phase, pi.target, pi.product_group, pi.cycle, subquery.status, subquery.last_update_time
        FROM (
            SELECT DISTINCT ON (ur.uut_id) ur.record_id, ur.uut_id, ur.status, ur.last_update_time, ur.borrower_id, ur.remark
            FROM unit_record AS ur
            WHERE ur.status != 'Delete'
            ORDER BY ur.uut_id, ur.last_update_time DESC
        ) subquery
        JOIN unit_list AS ul ON subquery.uut_id = ul.id
        JOIN platform_info AS pi ON ul.platform_id = pi.id
        LEFT JOIN user_info AS ui ON subquery.borrower_id = ui.user_id
        WHERE subquery.uut_id NOT IN (
            SELECT ur.uut_id
            FROM unit_record AS ur
            WHERE ur.status = 'Delete' 
        ) {target_condition} {group_condition} {platform_condition} {cycle_condition} {phase_condition} {status_condition} {machine_arrive_mail_condition}
        ORDER BY subquery.last_update_time DESC
    '''
    cursor.execute(query, tuple(targetset) + tuple(groupset) +platformsearch+cyclesearch+phasesearch+statussearch+tuple(machine_arrive_mail_set))  #查詢  套用元組進行查詢
    rows = cursor.fetchall()
    if rows:
        platform = []
        phase = []
        target = []
        group = []
        cycle = []
        status = []
        for row in rows:
            platform.append(row[0]) if row[0] and row[0] not in platform else None
            phase.append(row[1]) if row[1] and row[1] not in phase else None
            target.append(row[2]) if row[2] and row[2] not in target else None
            group.append(row[3]) if row[3] and row[3] not in group else None
            cycle.append(row[4]) if row[4] and row[4] not in cycle else None
            status.append(row[5]) if row[5] and row[5] not in status else None
        response_data = {
            'finaldata': {
                'platform': platform,
                'phase': phase,
                'target': target,
                'group': group,
                'cycle': cycle,
                'status': status + ['Machine arrive mail']
            } 
        }
        return JsonResponse(response_data) 
    else:
        response_data = {
                'error': 'No matching data' 
                }
        return JsonResponse(response_data) 

@api_view(["post"])
@csrf_exempt
@with_db_connection
def filtersearch(cursor, request):
    finaldatas = request.data
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    if len(finaldatas["target"]) > 0:
        targetset = set(finaldatas["target"])
    else:
        targetset = set("")  
    if len(finaldatas["group"]) > 0:
        groupset = set(finaldatas["group"])
    else:
        groupset = set("")
    if len(finaldatas["platform"]) > 0:
        platformset = set(finaldatas["platform"])
    else:
        platformset = set("") 
    if len(finaldatas["cycle"]) > 0:
        cycleset = set(finaldatas["cycle"])
    else:
        cycleset = set("")
    if len(finaldatas["SN"]) > 0:
        SNset = set(finaldatas["SN"])
    else:
        SNset = set("")
    if len(finaldatas["phase"]) > 0:
        phaseset = set(finaldatas["phase"])
    else:
        phaseset = set("") 
    print(finaldatas["status"])
    if len(finaldatas["status"]) > 0:
        statusset = set(finaldatas["status"])
        if "Machine arrive mail" in statusset :
            statusset.remove("Machine arrive mail")
    else:
        statusset = set("")
    print
    if any("Machine arrive mail" in status for status in finaldatas.get("status", [])):    
    # if finaldatas['machine_arrive_mail']:
        machine_arrive_mail_set = set(["true"])     
    else:
        machine_arrive_mail_set = set("")                
    # 創建一個佔位符字串，用於動態生成目標條件的部分 """"""""前面參數不能放數字""""""
    targetsearch_placeholders = ', '.join(['%s'] * len(targetset))
    groupsearch_placeholders = ', '.join(['%s'] * len(groupset))
    platformsearch_placeholders = ', '.join(['%s'] * len(platformset))
    cyclesearch_placeholders = ', '.join(['%s'] * len(cycleset))
    SNsearch_placeholders = ', '.join(['%s'] * len(SNset))
    phasesearch_placeholders = ', '.join(['%s'] * len(phaseset))
    statussearch_placeholders = ', '.join(['%s'] * len(statusset))
    machine_arrive_mail_search_placeholders = ', '.join(['%s'] * len(machine_arrive_mail_set))
    # 創建一個包含目標條件的元組
    targetsearch = tuple(targetset)
    groupsearch = tuple(groupset)
    platformsearch = tuple(platformset)
    cyclesearch = tuple(cycleset)
    serial_number_values = tuple(f"%{value}%" for value in SNset)
    phasesearch = tuple(phaseset)
    statussearch = tuple(statusset)
    target_condition = ''
    if len(targetset) > 0:
        target_condition = f"AND pi.target IN ({targetsearch_placeholders})"
    group_condition = ''
    if len(groupset) > 0:
        group_condition = f"AND pi.product_group IN ({groupsearch_placeholders})"
    platform_condition = ''    
    if len(platformset) > 0:
        platform_condition = f"AND pi.codename IN ({platformsearch_placeholders})"
    cycle_condition = ''
    if len(cycleset) > 0:
        cycle_condition = f"AND pi.cycle IN ({cyclesearch_placeholders})"
    SN_condition = ''    
    if len(SNset) > 0:
        SN_condition = f"AND ul.serial_number ILIKE ANY (ARRAY[{SNsearch_placeholders}])"  
    phase_condition = ''
    if len(phaseset) > 0:
        phase_condition = f"AND ul.phase IN ({phasesearch_placeholders})" 
    status_condition = ''
    if len(statusset) > 0: 
            status_condition = f"AND subquery.status IN ({statussearch_placeholders})"
    machine_arrive_mail_condition = ''
    if  machine_arrive_mail_set:
        machine_arrive_mail_condition = f"AND ul.machine_arrive_mail IN ({machine_arrive_mail_search_placeholders})"
    query = f'''
        SELECT pi.codename, ul.phase, pi.target, pi.product_group, pi.cycle, ul.sku, ul.serial_number,
            ui.user_name AS borrower_name,
            subquery.status, ul.position_in_site,
            subquery.remark, subquery.last_update_time
        FROM (
            SELECT DISTINCT ON (ur.uut_id) ur.record_id, ur.uut_id, ur.status, ur.last_update_time, ur.borrower_id, ur.remark
            FROM unit_record AS ur
            WHERE ur.status != 'Delete'
            ORDER BY ur.uut_id, ur.last_update_time DESC
        ) subquery
        JOIN unit_list AS ul ON subquery.uut_id = ul.id
        JOIN platform_info AS pi ON ul.platform_id = pi.id
        LEFT JOIN user_info AS ui ON subquery.borrower_id = ui.user_id
        WHERE subquery.uut_id NOT IN (
            SELECT ur.uut_id
            FROM unit_record AS ur
            WHERE ur.status = 'Delete' 
        ) {target_condition} {group_condition} {platform_condition} {cycle_condition} {SN_condition} {phase_condition} {status_condition} {machine_arrive_mail_condition} AND subquery.last_update_time BETWEEN '{start_time}' AND '{end_time}'
        ORDER BY subquery.last_update_time DESC
    '''
    cursor.execute(query, targetsearch+groupsearch+platformsearch+cyclesearch+serial_number_values+phasesearch+statussearch+tuple(machine_arrive_mail_set))  #查詢  套用元組進行查詢
    rows = cursor.fetchall()

    if rows:
        filtersearch = []
        for row in rows:
            filtersearch_data = {
                'platform': row[0],
                'phase': row[1],
                'target': row[2],
                'group': row[3],
                'cycle': row[4],
                'sku': row[5],
                'sn': row[6],
                'borrower': row[7],
                'status': row[8],
                'position': row[9],
                'remark': row[10],
                'update_time': row[11]
            }
            filtersearch.append(filtersearch_data)
        response_data = {
                'finaldata': filtersearch 
                }
        return JsonResponse(response_data) 
    else:
        response_data = {
                'error': 'No matching data' 
                }
        return JsonResponse(response_data) 

@with_db_connection
def target(cursor, request):
    query = '''
    SELECT DISTINCT target
    FROM platform_info
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    target = {'target': [row[0] for row in rows]}
    return JsonResponse(target)

@with_db_connection
def group(cursor, request):
    query = '''
    SELECT product_group
    FROM (
    SELECT product_group, CASE WHEN product_group = '' THEN 1 ELSE 0 END AS sort_flag
    FROM platform_info
    GROUP BY product_group
    ) AS subquery
    ORDER BY sort_flag, product_group
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    group = {'group': [row[0] for row in rows]}
    return JsonResponse(group)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def platform(cursor, request):
    search = request.data
    if len(search["target"]) > 0:
        targetsearch2 = set(search["target"])
    else:
        targetsearch2 = set("")

    if len(search["group"]) > 0:
        groupsearch2 = set(search["group"])
    else:
        groupsearch2 = set("") 
    if len(search["cycle"]) > 0:
        cyclesearch2 = set(search["cycle"])
    else:
        cyclesearch2 = set("")          
    # 創建一個佔位符字串，用於動態生成目標條件的部分 """"""""前面參數不能放數字""""""
    targetsearch_placeholders = ', '.join(['%s'] * len(targetsearch2))
    groupsearch_placeholders = ', '.join(['%s'] * len(groupsearch2))
    cyclesearch_placeholders = ', '.join(['%s'] * len(cyclesearch2))
    # 創建一個包含目標條件的元組
    targetsearch3 = tuple(targetsearch2)
    groupsearch3 = tuple(groupsearch2)
    cyclesearch3 = tuple(cyclesearch2)
    target_condition = ''
    if len(targetsearch2) > 0:
        target_condition = f"AND pi.target IN ({targetsearch_placeholders})"
    group_condition = ''
    if len(groupsearch2) > 0:
        group_condition = f"AND pi.product_group IN ({groupsearch_placeholders})"
    cycle_condition = ''    
    if len(cyclesearch2) > 0:
        cycle_condition = f"AND pi.cycle IN ({cyclesearch_placeholders})"    
    query = f'''
        SELECT subquery.codename, array_agg(subquery.uut_id) AS uut_ids
        FROM (
            SELECT DISTINCT ON (ur.uut_id, pi.codename) ur.uut_id, pi.codename
            FROM unit_record AS ur
            JOIN unit_list AS ul ON ur.uut_id = ul.id
            JOIN platform_info AS pi ON ul.platform_id = pi.id
            LEFT JOIN user_info AS ui ON ur.borrower_id = ui.user_id
            WHERE 1=1 {target_condition} {group_condition} {cycle_condition}
            ORDER BY ur.uut_id, pi.codename
        ) subquery
        GROUP BY subquery.codename
        ORDER BY subquery.codename
    '''
    cursor.execute(query, targetsearch3+groupsearch3+cyclesearch3)
    rows = cursor.fetchall() 
    platform = {'platform': [row[0] for row in rows]}
    return JsonResponse(platform)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def cycle(cursor, request):
    search = request.data
    print(search)
    if len(search["target"]) > 0:
        targetsearch2 = set(search["target"])
        print(targetsearch2)
    else:
        targetsearch2 = set("")
    if len(search["group"]) > 0:
        groupsearch2 = set(search["group"]) 
    else:
        groupsearch2 = set("")    
    targetsearch_placeholders = ', '.join(['%s'] * len(targetsearch2))
    groupsearch_placeholders = ', '.join(['%s'] * len(groupsearch2))
    targetsearch3 = tuple(targetsearch2)
    groupsearch3 = tuple(groupsearch2)
    target_condition = ''
    if len(targetsearch2) > 0:
        target_condition = f"AND pi.target IN ({targetsearch_placeholders})"

    group_condition = ''
    if len(groupsearch2) > 0:
        group_condition = f"AND pi.product_group IN ({groupsearch_placeholders})"

    query = f'''
        SELECT subquery.cycle, array_agg(subquery.uut_id) AS uut_ids
        FROM (
            SELECT DISTINCT ON (ur.uut_id, pi.cycle) ur.uut_id, pi.cycle
            FROM unit_record AS ur
            JOIN unit_list AS ul ON ur.uut_id = ul.id
            JOIN platform_info AS pi ON ul.platform_id = pi.id
            LEFT JOIN user_info AS ui ON ur.borrower_id = ui.user_id
            WHERE 1=1 {target_condition} {group_condition}
            ORDER BY ur.uut_id, pi.cycle
        ) subquery
        GROUP BY subquery.cycle
        ORDER BY subquery.cycle
    '''
    cursor.execute(query, targetsearch3+groupsearch3)
    rows = cursor.fetchall()
    cycle = {'cycle': [row[0] for row in rows]}
    return JsonResponse(cycle)

@with_db_connection
def phase(cursor, request):
    query = '''
    SELECT DISTINCT phase
    FROM unit_list
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    phase = {'phase': [row[0] for row in rows]}
    return JsonResponse(phase) 

@with_db_connection
def status(cursor, request):
    query ='''
    SELECT DISTINCT status
    FROM unit_record
    WHERE status != 'Delete';
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    status = {'status': [row[0] for row in rows] + ['machine_arrive_mail']}
    return JsonResponse(status)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def widthsearch(cursor, request):   #SN/platform/borrower
    widthsearch=request.data
    search = set(widthsearch["keyword"])
    print(search)
    serial_number_placeholders = ', '.join(['%s'] * len(search)) #創建查詢列表 用,分隔/join串起來/%s為一個佔位符用於查詢乘上整個陣列元素數量
    codename_placeholders = ', '.join(['%s'] * len(search))
    user_name_placeholders = ', '.join(['%s'] * len(search))
    serial_number_values = tuple(f"%{value}%" for value in search)  #將['1','2','3'] 轉換成元組 ('1','2','3')
    codename_values = tuple(f"%{value}%" for value in search) # 創建value字串 %{value}%模糊搜索
    user_name_values = tuple(f"%{value}%" for value in search)
    conditionsn = f"AND ul.serial_number ILIKE ANY (ARRAY[{serial_number_placeholders}])" #IN是完全符合的關鍵字
    conditioncodename = f"AND pi.codename ILIKE ANY (ARRAY[{codename_placeholders}])" #LIKE ANY模糊搜尋
    conditionusername = f"AND ui.user_name ILIKE ANY (ARRAY[{user_name_placeholders}])" #ILIKE 忽略大小寫
    query = f'''
        SELECT pi.codename, ul.phase, pi.target, pi.product_group, pi.cycle, ul.sku, ul.serial_number,
            ui.user_name AS borrower_name,
            subquery.status, ul.position_in_site,
            subquery.remark, subquery.last_update_time
        FROM (
            SELECT DISTINCT ON (ur.uut_id) ur.record_id, ur.uut_id, ur.status, ur.last_update_time, ur.borrower_id, ur.remark
            FROM unit_record AS ur
            WHERE ur.status != 'Delete'
            ORDER BY ur.uut_id, ur.last_update_time DESC
        ) subquery
        JOIN unit_list AS ul ON subquery.uut_id = ul.id
        JOIN platform_info AS pi ON ul.platform_id = pi.id
        LEFT JOIN user_info AS ui ON subquery.borrower_id = ui.user_id
        WHERE subquery.uut_id NOT IN (
        SELECT ur.uut_id
        FROM unit_record AS ur
        WHERE ur.status = 'Delete' 
        ) AND ((1=1 {conditionsn}) OR (1=1 {conditioncodename}) OR (1=1 {conditionusername})) 
        ORDER BY subquery.last_update_time DESC
    '''
    cursor.execute(query, serial_number_values + codename_values + user_name_values) #查詢  套用元組進行查詢
    rows = cursor.fetchall()
    if rows:
        filtersearch = []
        for row in rows:
            filtersearch_data = {
                'platform': row[0],
                'phase': row[1],
                'target': row[2],
                'group': row[3],
                'cycle': row[4],
                'sku': row[5],
                'sn': row[6],
                'borrower': row[7],
                'status': row[8],
                'position': row[9],
                'remark': row[10],
                'update_time': row[11]
            }
            filtersearch.append(filtersearch_data)
        response_data = {
                'finaldata': filtersearch 
                }
        return JsonResponse(response_data) 
    else:
        response_data = {
                'error': 'No matching data' 
                }
        return JsonResponse(response_data) 

#change series
@api_view(["post"])
@csrf_exempt
@with_db_connection
def changeplatform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatas = request.data.get('finaldata')
    sn_list = []
    for finaldata in finaldatas:
        platform = finaldata["platform"]
        sn = finaldata["sn"]
        if platform == '' or sn == '':
            return JsonResponse({'error': '"Platform" or "SN" cannot be empty.'})
        status = machine_status_approve(sn)
        if status == 'Delete':
            return JsonResponse({'error': 'The machine has been deleted.'})
    for finaldata in finaldatas:
        try:
            platform = finaldata["platform"]
            phase = finaldata["phase"]
            target = finaldata["target"]
            group = finaldata["group"]
            cycle = finaldata["cycle"]
            sku = finaldata["sku"]
            sn = finaldata["sn"]
            borrower = finaldata["borrower"]
            status = finaldata["status"]
            position = finaldata["position"]
            remark = finaldata["remark"]
            update_time = finaldata["update_time"]

            platform_condition = ''
            platformparams = []
            if platform:  
                platform_condition = f"AND pi.codename IN (%s)"
                platformparams.append(platform)
            target_condition = ''
            targetparams = []
            if target: 
                target_condition = f"AND pi.target IN (%s)"
                targetparams.append(target)
            group_condition = ''
            groupparams = []
            if group:
                group_condition = f"AND pi.product_group IN (%s)"
                groupparams.append(group)
            cycle_condition = ''
            cycleparams = []
            if cycle:
                cycle_condition = f"AND pi.cycle IN (%s)" 
                cycleparams.append(cycle)     
            query = f'''
            WITH updated_platform AS (
                UPDATE platform_info AS pi
                SET remark = %s
                WHERE 1=1 {platform_condition} {target_condition} {group_condition} {cycle_condition}
                RETURNING id, pi.codename, pi.target, pi.product_group, pi.cycle
            )
            SELECT id, codename, target, product_group, cycle
            FROM updated_platform
            '''
            cursor.execute(query, (remark,) + tuple(platformparams) + tuple(targetparams) + tuple(groupparams) + tuple(cycleparams))  #(platform,) 當動態字元組
            platform_id=cursor.fetchone()[0] 

            sn_condition = f"AND ul.serial_number IN (%s)"

            query = f'''
            WITH updated_list AS (
                UPDATE unit_list AS ul
                SET platform_id = %s, phase = %s, sku = %s, position_in_site = %s, remark = %s
                WHERE 1=1 {sn_condition}
                RETURNING id
            )
            SELECT id
            FROM updated_list
            '''
            cursor.execute(query, (platform_id,) + (phase,) + (sku,) + (position,) + (remark,) + (sn,))
            uut_id=cursor.fetchone()[0] 
            operation = f"修改: {sn} 機台"
            log_views.log_operation(user_id, operation)
        except Exception as e:
            log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {sn}")
            sn_list.append(sn)
    if sn_list:
        response_data = {
            'error': f"Modification: {sn_list} machine failed.",
            }
    else:
        response_data = {
            'finaldata': 'successful',
            }
    return JsonResponse(response_data)

#return series
@api_view(["post"])
@csrf_exempt
@with_db_connection
def returnplatform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatas = request.data.get('finaldata')
    purpose = request.data.get('purpose')
    message = request.data.get('message')
    cc_mail = request.data.get('cc_mail')
    
    borrower_dict = {}  # 用於分類相同 SN 的字典
    borrower_set = set()  # 用於儲存不同的 SN

    for finaldata in finaldatas:
        status = machine_status_approve(finaldata["sn"])
        if status != 'Rent':
            return JsonResponse({'error': 'Please ensure that the status of each machine is Rent'})
    sn_list = []
    for finaldata in finaldatas:
        try:
            sn = finaldata["sn"]
            position = finaldata["position"]
            remark = finaldata["remark"]

            sn_condition = ''
            snparams = []
            if sn:
                sn_condition = f"AND ul.serial_number IN (%s)" 
                snparams.append(sn)            
            query = f'''
            WITH updated_list AS (
                UPDATE unit_list AS ul
                SET position_in_site = %s, remark = %s
                WHERE 1=1 {sn_condition} 
                RETURNING ul.id, ul.platform_id, ul.phase, ul.sku
            )
            SELECT id, platform_id, phase, sku
            FROM updated_list
            '''
            cursor.execute(query, (position,) + (remark,) + tuple(snparams))  
            result_ul=cursor.fetchone()  
            uut_id=result_ul[0]
            platform_id=result_ul[1]
            phase=result_ul[2]
            sku=result_ul[3]
            
            record_pi = platform_id_to_platform_info(platform_id)
            platform = record_pi[0]

            result_ur = uut_id_to_unit_record(uut_id)
            borrower_time = result_ur[2]
            borrower_id = result_ur[3]

            result_ui = borrower_id_to_user_info(borrower_id)
            borrower = result_ui[0]
            borrower_mail = json.loads(result_ui[2])["user_email"]

            newstatus = 'Keep On'
            last_update_time = timenow()
            cursor.execute("INSERT INTO unit_record (uut_id, status, last_update_time, remark) VALUES (%s, %s, %s, %s)", (uut_id, newstatus, last_update_time, purpose))
        
            iur_data = {
                'platform': platform,
                'phase': phase,
                'sku': sku,  
                'sn': sn,
                'borrower_id': borrower,
                'rent_time': borrower_time.strftime("%B %d, %Y, %I:%M %p"), 
                'back_time': last_update_time.strftime("%B %d, %Y, %I:%M %p")    
                }
            
            if borrower_mail in borrower_dict:
                borrower_dict[borrower_mail].append(iur_data)
            else:
                borrower_dict[borrower_mail] = [iur_data]

            borrower_set.add(borrower_mail)
            operation = f"歸還:{sn}機台"
            log_views.log_operation(user_id, operation)
        except Exception as e:
            log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {sn}")
            sn_list.append(sn)

    for borrower_mail in borrower_set:    
        # print(borrower_dict[borrower])
        try:
            send_rent_borrowed_mail(user=user_id, to=borrower_mail, cc=cc_mail, return_records=borrower_dict[borrower_mail], message=message)
        except Exception as e:
            log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"send_mail_fail: {borrower_mail}")
            return JsonResponse({'error': f"send_mail_fail: {borrower_mail}"})
    return JsonResponse({'finaldata': 'successful'})


# lend personnel
@with_db_connection
def lendpersonnel(cursor, request):
    query = '''
    SELECT DISTINCT user_name
    FROM user_info
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    query_mail = '''
    SELECT DISTINCT ui.user_info ->> 'user_email'
    FROM user_info AS ui
    '''
    cursor.execute(query_mail)
    rows_mail = cursor.fetchall()
    lendperson = {'user_name': [row[0] for row in rows], 'user_mail': [row_mail[0] for row_mail in rows_mail]}
    return JsonResponse(lendperson) 

#lend series
@api_view(["post"])
@csrf_exempt
@with_db_connection
def lendplatform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    lendpersonnel = request.data.get('lendperson')
    finaldatas = request.data.get('finaldata')
    cc_mail = request.data.get('cc_mail')
    message = request.data.get('message')
    purpose = request.data.get('purpose')
    for finaldata in finaldatas:
        status = machine_status_approve(finaldata["sn"])
        if status != 'Keep On':
            return JsonResponse({'error': 'Please ensure that the status of each machine is Keep On'})
    iur_mail=[]
    for finaldata in finaldatas:
        sn = finaldata["sn"]
        result_ul = sn_to_unit_list(sn)
        uut_id = result_ul[0]
        result_ur=uut_id_to_unit_record(uut_id)
        if result_ur[1] != 'Keep On':
            response_data = {
            'error': 'Please ensure that the status of each machine is Keep On',  
            }
            return JsonResponse(response_data)
    if lendpersonnel == '':
        response_data = {
        'error': 'The borrower cannot be null',  
        }
        return JsonResponse(response_data)
    '''log
    status_values = [data["sn"] for data in finaldatas]
    operation = f"借出: {' '.join(status_values)} 機台"
    log_views.log_operation(user_id, operation)
    '''
    for finaldata in finaldatas:
        try:
            sn = finaldata["sn"]

            result_ul = sn_to_unit_list(sn)
            uut_id = result_ul[0]
            platform_id = result_ul[1]
            phase = result_ul[2]
            sku = result_ul[3]
            remark = result_ul[6]
            
            rusult_pi = platform_id_to_platform_info(platform_id)
            platform = rusult_pi[0]

            lendpersonnel_condition = ''
            lendpersonnelparams = []
            if lendpersonnel:
                lendpersonnel_condition = f"AND user_info.user_info ->> 'user_email' IN (%s)" 
                lendpersonnelparams.append(lendpersonnel)            
            query = f'''
            SELECT user_id, user_name
            FROM user_info
            WHERE 1=1 {lendpersonnel_condition} 
            '''
            cursor.execute(query, tuple(lendpersonnelparams))  
            [borrower_id, user_name]=cursor.fetchone()

            newstatus = 'Rent'
            last_update_time = timenow()
            cursor.execute("INSERT INTO unit_record (uut_id, status, last_update_time, borrower_id, remark) VALUES (%s, %s, %s, %s, %s)", (uut_id, newstatus, last_update_time, borrower_id, remark))
            print(last_update_time)
            iur_data = { 
                'platform': platform,
                'phase': phase,
                'sku': sku,  
                'sn': sn,
                'borrower_id': user_name,
                'purpose': purpose,
                'rent_time': last_update_time.strftime("%B %d, %Y, %I:%M %p"),    
                }
            iur_mail.append(iur_data)
            operation = f"借出: {sn} 機台"
            log_views.log_operation(user_id, operation)
        except Exception as e:
            log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {sn}")
    try:
        send_rent_borrowed_mail(user=user_id, to=lendpersonnel, cc=cc_mail, borrow_records=iur_mail, message=message)
    except Exception as e:
        log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"send_mail_fail: {lendpersonnel}")
        return JsonResponse({'error': 'Failed to send email, please check if the token has expired'})
    return JsonResponse({'finaldata': 'successful'})

#scrap series
@api_view(["post"])
@csrf_exempt
@with_db_connection
def scrapped_platform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatas = request.data.get('finaldata')
    for finaldata in finaldatas:
        status = machine_status_approve(finaldata["sn"])
        if status != 'Keep On':
            return JsonResponse({'error': 'Please ensure that the status of each machine is Keep On'})

    for finaldata in finaldatas:
        try:
            sn = finaldata["sn"]
            position = finaldata["position"]
            remark = finaldata["remark"]
            sn_condition = ''
            snparams = []
            if sn:
                sn_condition = f"AND ul.serial_number IN (%s)" 
                snparams.append(sn)            
            query = f'''
            WITH updated_list AS (
                UPDATE unit_list AS ul
                SET position_in_site = %s, remark = %s
                WHERE 1=1 {sn_condition} 
                RETURNING ul.id
            )
            SELECT id
            FROM updated_list
            '''
            cursor.execute(query, (position,) + (remark,) + tuple(snparams))  
            result_ul=cursor.fetchone()  
            uut_id=result_ul[0]

            newstatus = 'Scrapped'
            last_update_time = timenow()
            cursor.execute("INSERT INTO unit_record (uut_id, status, last_update_time, remark) VALUES (%s, %s, %s, %s)", (uut_id, newstatus, last_update_time, remark))
            operation = f"報廢: {sn} 機台"
            log_views.log_operation(user_id, operation)
        except Exception as e:
            log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"serial_number: {sn}")
            return JsonResponse({'error': f"Scrap: {sn} machine failed"})
    return JsonResponse({'finaldata': 'successful'})

# :x:/r open file 
# :u:/r download file
@api_view(["post"])
@csrf_exempt
@parser_classes([MultiPartParser])
@with_db_connection
def send_mail_newplatform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatas = json.loads(request.data.get('finaldata'))
    uploaded_file = request.FILES.get('file')
    folder_choose = json.loads(request.data.get('folder_choose'))
    print(folder_choose)
    if uploaded_file:
        folder_split = '/'.join(folder_choose)
        file_path = f'https://hp.sharepoint.com/:u:/r/teams/CommunicationsTechnologyTeam/Dogfood/IUR/{folder_split}/{uploaded_file.name}'
        file_link = f'<a href="{file_path}">{uploaded_file.name}</a>'
        folder_path = f'/IUR/{folder_split}'
    else:
        file_link = ''
    for finaldata in finaldatas:
        platform = finaldata["platform"]
        phase = finaldata["phase"]
        sku = finaldata["sku"]
        target = finaldata["target"]
        group = finaldata["group"]
        sn = finaldata["sn"]
        remark = finaldata["remark"]
        sn_condition = ''
        snparams = []
        if sn:
            sn_condition = f"AND ul.serial_number IN (%s)" 
            snparams.append(sn)            
        query = f'''
            SELECT id, machine_arrive_mail
            FROM unit_list AS ul
            WHERE 1=1 {sn_condition} 
        '''
        cursor.execute(query, tuple(snparams))  
        result_ul=cursor.fetchone()
        print(result_ul[0])
        print(result_ul[1])

        id_condition = f"AND ul.id IN (%s)"
        query = f'''
        UPDATE unit_list AS ul
        SET machine_arrive_mail = %s
        WHERE 1=1 {id_condition} 
        '''  
        cursor.execute(query, (False,) + (result_ul[0],))

        ''' 新增record 狀態為Keep On
        uut_id=result_ul[0]
        newstatus = 'Keep On'
        current_time = datetime.now()
        timezone = pytz.timezone('Asia/Taipei')
        last_update_time = current_time.astimezone(timezone)
        cursor.execute("INSERT INTO unit_record (uut_id, status, last_update_time, remark) VALUES (%s, %s, %s, %s)", (uut_id, newstatus, last_update_time, remark))
        '''
    group_target_dict = {}
    for item in finaldatas:
        group_target = (item["group"], item["target"])
        if group_target in group_target_dict:
            group_target_dict[group_target].append(item)
        else:
            group_target_dict[group_target] = [item]

    for group_target, items in group_target_dict.items():
        platform_phase_sku_count = {}
        for item in items:
            platform_phase_sku_key = (item["platform"], item["phase"], item["sku"])
            if platform_phase_sku_key in platform_phase_sku_count:
                platform_phase_sku_count[platform_phase_sku_key] += 1
            else:
                platform_phase_sku_count[platform_phase_sku_key] = 1
        group_target_dict[group_target] = platform_phase_sku_count

    #log
    status_values = [data["sn"] for data in finaldatas]
    operation = f"入庫發信: {' '.join(status_values)} 機台"
    log_views.log_operation(user_id, operation)
    
    for key, platform_phase_sku_count in group_target_dict.items():
       # print("Group: {}, Target: {}".format(key[0], key[1]))
        iur_title = []
        iur_data = []
        tilte_data = { 
            'group': key[0],
            'target': key[1]   
            }
        iur_title.append(tilte_data)
        for platform_phase_sku, count in platform_phase_sku_count.items():
            platform, phase, sku = platform_phase_sku
           # print("    Platform: {}, Phase: {}, SKU: {}, Count: {}".format(platform, phase, sku, count))
            print(platform, phase, sku, count, key[0], key[1])
            data = { 
                'platform': platform,
                'phase': phase,
                'sku': sku,  
                'count': count 
                }
            iur_data.append(data)

        template = get_template("polls/mail_machine_arrive_template.html")
        account = account_views.get_account(user_id)
        message = ''
        context = {
                        #'receiver':'  '.join([t.usernameincompany for t in to]),
                        'message':message,
                        'iur_title':iur_title,
                        'iur_data':iur_data,
                        'sender':account.get_current_user().full_name,
                        'att_files': file_link
                    }
        body = template.render(context)
        subject = "Machines arrived"
        '''
        if cc:
            cc = list(cc.values_list('user__email',flat=True)) 
        if to:
            to = list(to.values_list('user__email',flat=True))
        '''    
        to = ['cmitcommsw@hp.com', 'stevencommshwall@hp.com', 'COMMsPM@hp.com']
        cc = ''
        mail_views.HP_mail(account,to,cc,subject,body)
    if uploaded_file:   
        try:
            sharepoint_views.sharepoint_upload_file(user_id, uploaded_file, folder_path=folder_path) 
            operation = f"歸還機台, 附加檔案: {uploaded_file.name}"
            log_views.log_operation(user_id, operation)
        except Exception as e:
            log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"uploaded_file_fail: {uploaded_file.name}")
            return JsonResponse({'error': f"附加檔案: {uploaded_file.name} 上傳失敗"})
    response_data = {
        'finaldata': 'successful', 
        }
    return JsonResponse(response_data)

#platform target group cycle combination
@with_db_connection
def addplatformcombination(cursor, request):
    query = f'''
        SELECT pi.codename, pi.target, pi.product_group, pi.cycle
        FROM platform_info AS pi
        GROUP BY pi.codename, pi.target, pi.product_group, pi.cycle
    '''
    cursor.execute(query) 
    rows = cursor.fetchall()  
    iur = {'platform': [f'{row[0] if row[0] is not None else ""} - {row[1] if row[1] is not None else ""} - {row[2] if row[2] is not None else ""} - {row[3] if row[3] is not None else ""}' for row in rows]}
    return JsonResponse(iur, safe=False)

#platfrom target group cycle add
@api_view(["post"])
@csrf_exempt
@with_db_connection
def addplatformonly(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    platform = request.data.get('platform')
    target = request.data.get('target')
    group = request.data.get('group')
    cycle = request.data.get('cycle')
    if platform:
        query = f'''
        SELECT *
        FROM platform_info AS pi
        WHERE pi.codename = %s AND pi.target = %s AND pi.product_group = %s AND pi.cycle = %s
        '''
        cursor.execute(query, (platform,) + (target,) + (group,) + (cycle,))
        if cursor.fetchone():
            return JsonResponse({'error': 'The combination already exists.'})
        else:
            cursor.execute("INSERT INTO platform_info (codename, target, product_group, cycle) VALUES (%s, %s, %s, %s)", (platform, target, group, cycle))
            return JsonResponse({'successful': 'Added successfully.'}) 
    else:
        return JsonResponse({'error': 'Platform cannot be empty.'}) 
    
# add new platform    
@api_view(["post"])
@csrf_exempt
@with_db_connection
def addnewplatform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatasjson = request.data.get('finaldata')
    uploaded_file = request.FILES.get('file')
    finaldatas = json.loads(finaldatasjson)
    sn_set = set()

    for finaldata in finaldatas:
        sn = finaldata["sn"]
        sn_set.add(sn)

        if finaldata["platform"].strip() == "" or finaldata["sn"].strip() == "":
            return JsonResponse({'error': 'Platform or SN cannot be empty.'})
        
        query = f'''
            SELECT ul.serial_number
            FROM unit_list AS ul
            WHERE ul.serial_number IN (%s)
        '''
        cursor.execute(query, (sn,))  
        if cursor.fetchone():
            return JsonResponse({'error': f"The serial number [{sn}] already exists in the database, please check."})
    if len(sn_set) == len(finaldatas):
        for finaldata in finaldatas:
            platform = finaldata["platform"]
            phase = finaldata["phase"]
            target = finaldata["target"]
            group = finaldata["group"]
            cycle = finaldata["cycle"]
            sku = finaldata["sku"]
            sn = finaldata["sn"]
            acquirer = finaldata["acquirer"]
            position = finaldata["position"]
            remark = finaldata["remark"]
            platform_condition = ''
            platformparams = []
            if platform:  
                platform_condition = f"AND pi.codename IN (%s)"
                platformparams.append(platform)
            target_condition = ''
            targetparams = []
            if target: 
                target_condition = f"AND pi.target IN (%s)"
                targetparams.append(target)
            group_condition = ''
            groupparams = []
            if group:
                group_condition = f"AND pi.product_group IN (%s)"
                groupparams.append(group)
            cycle_condition = ''
            cycleparams = []
            if cycle:
                cycle_condition = f"AND pi.cycle IN (%s)" 
                cycleparams.append(cycle)            
            query = f'''
            WITH updated_platform AS (
                UPDATE platform_info AS pi
                SET remark = %s
                WHERE 1=1 {platform_condition} {target_condition} {group_condition} {cycle_condition}
                RETURNING id, pi.codename, pi.target, pi.product_group, pi.cycle
            )
            SELECT id, codename, target, product_group, cycle
            FROM updated_platform
            '''
            cursor.execute(query, (remark,) + tuple(platformparams) + tuple(targetparams) + tuple(groupparams) + tuple(cycleparams))  #(platform,) 當動態字元組
            
            platform_id=cursor.fetchone()[0] 
            
            site="TW"
            status="Keep On"
            last_update_time = timenow()
            
            cursor.execute("INSERT INTO unit_list (platform_id, serial_number, phase, sku, site, position_in_site, acquirer, remark) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id" , (platform_id, sn, phase, sku, site, position, acquirer, remark))
            uut_id=cursor.fetchone()[0]
            print(uut_id)

            cursor.execute("INSERT INTO unit_record (uut_id, status, last_update_time, remark) VALUES (%s, %s, %s, %s)" , (uut_id, status, last_update_time, remark))
            operation = f"新增: {sn} 機台"
            log_views.log_operation(user_id, operation)
        if uploaded_file:
            try:
                sharepoint_views.sharepoint_upload_file(user_id, uploaded_file)
                operation = f"新增附加檔案: {uploaded_file.name}"
                log_views.log_operation(user_id, operation)
            except Exception as e:
                log_views.log_error(__file__, inspect.currentframe().f_code.co_name, e, f"uploaded_file_fail: {uploaded_file.name}")
                return JsonResponse({'error': f"Attachment: {uploaded_file.name} upload failed"})

        return JsonResponse({'finaldata': 'successful'})       
    else:
        return JsonResponse({'error': "The input value for SN is duplicated, please check."})

# delete series
@api_view(["post"])
@csrf_exempt
@with_db_connection
def deleteplatform(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatas = request.data.get("finaldata")
    for finaldata in finaldatas:
        status = machine_status_approve(finaldata["sn"])
        if status != 'Keep On':
            return JsonResponse({'error': 'Please ensure that the status of each machine is Keep On'})
    for finaldata in finaldatas:
        sn = finaldata["sn"]
        remark = finaldata["remark"]

        sn_condition = ''
        snparams = []
        if sn:
            sn_condition = f"AND ul.serial_number IN (%s)"
            snparams.append(sn)
        query = f'''
            SELECT id
            FROM unit_list AS ul
            WHERE 1=1 {sn_condition}
        '''
        cursor.execute(query, tuple(snparams))  
        uut_id=cursor.fetchone()[0]  

        status='Delete'
        last_update_time = timenow()
        cursor.execute("INSERT INTO unit_record (uut_id, status, last_update_time, remark) VALUES (%s, %s, %s, %s)" , (uut_id, status, last_update_time, remark))
        operation = f"刪除: {sn} 機台"
        log_views.log_operation(user_id, operation)

    return JsonResponse({'finaldata': 'successful'})


#mail format
def send_rent_borrowed_mail(user,request=None,to=None,borrow_records=None,return_records=None,cc=None,message:str='',attachments:list=None):
    template = get_template("polls/mail_borrow_rent.html")
    account = account_views.get_account(user)
    print(borrow_records)
    print(return_records)
    if account:
        '''
        if return_records:
            
            return_member =  'bill.chang@hp.com'
            if to:
                to |= return_member #添加但去除相同的元素
            else:
                to = return_member
        '''
        #att_files = [ (file.name,file.share_with_link(share_scope='organization').share_link) for file in self.save_attachments_to_cloud(account,attachments)] if attachments else None
        attachments = None

        context = {
                    #'receiver':'  '.join([t.usernameincompany for t in to]),
                    'message':message,
                    'borrow_records':borrow_records,
                    'return_records':return_records,
                    'sender':account.get_current_user().full_name,
                    'att_files': attachments
                }
        
        body = template.render(context)
        subject = "IUR record update"
        '''
        if cc:
            cc = list(cc.values_list('user__email',flat=True)) 
        if to:
            to = list(to.values_list('user__email',flat=True))
        '''   
        return mail_views.HP_mail(account,to,cc,subject,body)


# @api_view(["post"])
# @csrf_exempt
# def proxy_mail(request):
#     data = request.data
#     print(data["subject"],data["to"],data["cc"],data["body"])
#     mail_views.send_email_proxy(data["subject"], data["to"], data["cc"], data["body"])
#     return JsonResponse({'redirect_url': '/polls/'})  

#machine record
@api_view(["post"])
@csrf_exempt
@with_db_connection
def machine_record(cursor, request):
    sn = request.data.get('sn')
    sn_condition = f"AND ul.serial_number IN (%s)"
    query = f'''
        SELECT pi.codename, ul.phase, pi.target, pi.product_group, pi.cycle, ul.sku, ul.serial_number, ul.acquirer,
            ui.user_name AS borrower_name,
            ur.status, ul.position_in_site,
            ur.remark, ur.last_update_time
        FROM unit_record AS ur
        JOIN unit_list AS ul ON ur.uut_id = ul.id
        JOIN platform_info AS pi ON ul.platform_id = pi.id
        LEFT JOIN user_info AS ui ON ur.borrower_id = ui.user_id
        WHERE 1=1 {sn_condition}
        ORDER BY ur.last_update_time DESC
    '''
    cursor.execute(query, (sn,))
    rows = cursor.fetchall()
    iur = []
    for row in rows:
        iur_data = {
            'platform': row[0],
            'phase': row[1],
            'target': row[2],
            'group': row[3],
            'cycle': row[4],
            'sku': row[5],
            'sn': row[6],
            'acquirer': row[7],
            'borrower': row[8],
            'status': row[9],
            'position': row[10],
            'remark': row[11],
            'update_time': row[12]
        }
        iur.append(iur_data)
    return JsonResponse({'iur_data': iur})  

@with_db_connection
def machine_status_approve(cursor, sn):
    sn_condition = f"AND ul.serial_number IN (%s)"      
    query = f'''
    SELECT DISTINCT ON (ur.uut_id) ur.status
    FROM unit_record AS ur
    LEFT JOIN unit_list AS ul ON ur.uut_id = ul.id
    WHERE 1=1 {sn_condition}
    ORDER BY ur.uut_id, ur.last_update_time DESC
    '''
    cursor.execute(query, (sn,))  
    result=cursor.fetchone()
    [status] = result
    return status

@with_db_connection
def sn_to_unit_list(cursor, sn):
    sn_condition = f"AND ul.serial_number IN (%s)"      
    query = f'''
    SELECT id, platform_id, phase, sku, site, position_in_site, remark
    FROM unit_list AS ul
    
    WHERE 1=1 {sn_condition} 
    '''
    cursor.execute(query, (sn,))  
    result=cursor.fetchone()
    [uut_id,platform_id,phase,sku,site,position_in_site,remark] = result
    return uut_id,platform_id,phase,sku,site,position_in_site,remark

@with_db_connection
def borrower_id_to_user_info(cursor, borrower_id):
    borrower_id_condition = f"AND ui.user_id IN (%s)"
    query = f'''
    SELECT user_name, user_site, user_info, access_group_id
    FROM user_info AS ui
    WHERE 1=1 {borrower_id_condition} 
    '''
    cursor.execute(query, (borrower_id,)) 
    result=cursor.fetchone() 
    user_name=result[0]
    user_site=result[1]
    user_info=result[2]
    access_group_id=result[3]
    return user_name,user_site,user_info,access_group_id 

@with_db_connection
def platform_id_to_platform_info(cursor, platform_id):
    platform_id_condition = f"AND pi.id IN (%s)"         
    query = f'''
    SELECT codename, product_group, target, cycle, remark
    FROM platform_info AS pi
    WHERE 1=1 {platform_id_condition} 
    '''
    cursor.execute(query, (platform_id,))
    result_pi=cursor.fetchone()
    platform=result_pi[0]
    group=result_pi[1]
    target=result_pi[2]
    cycle=result_pi[3]
    remark=result_pi[4]
    return platform,group,target,cycle,remark

@with_db_connection
def uut_id_to_unit_record(cursor, uut_id):
    uut_id_condition = f"AND ur.uut_id IN (%s)" 
    query = f'''
    SELECT record_id, status, last_update_time, borrower_id, remark
    FROM unit_record AS ur 
    WHERE 1=1 {uut_id_condition}
    ORDER BY last_update_time DESC
    LIMIT 1
    '''
    cursor.execute(query, (uut_id,))
    result_ur=cursor.fetchone()
    record_id=result_ur[0]
    status=result_ur[1]
    last_update_time=result_ur[2]
    borrower_id=result_ur[3]
    remark=result_ur[4]
    return record_id,status,last_update_time,borrower_id,remark  

@with_db_connection
def username_to_usermail(cursor, username):
    query = f'''
    SELECT user_info ->> 'user_email' AS user_email
    FROM user_info AS ui
    WHERE ui.user_name = %s
    '''
    cursor.execute(query, (username,))
    result=cursor.fetchone()
    user_email=result[0]
    return user_email

@with_db_connection
def user_info_mail(cursor, request):
    query = f'''
    SELECT DISTINCT ui.user_info ->> 'user_email' AS user_email
    FROM user_info AS ui
    WHERE (ui.user_info ->> 'user_email') IS NOT NULL AND (ui.user_info ->> 'user_email') <> '';
    '''
    cursor.execute(query)
    rows = cursor.fetchall()

    users_email = []
    for row in rows:
        users_email.append(row[0])
    return JsonResponse({'users_email': users_email})


@api_view(["post"])
@csrf_exempt
def excel_export(request):
    finaldatas = json.loads(request.data.get('data'))
    file_path = tool_views.excel_make(finaldatas)
    print(file_path)
    return FileResponse(open(file_path, 'rb'))

@api_view(["post"])
@csrf_exempt
def sharepoint_name_user(request):
    user_id = request.user_id
    folder_choose = request.data.get('folder_choose')
    print(folder_choose)
    folder_name = sharepoint_views.get_iur_sharepoint_folder(user_id, folder_choose)
    print(folder_name)
    return JsonResponse({'folder_name': folder_name})


def timenow():
    current_time = datetime.now()
    timezone = pytz.timezone('Asia/Taipei')
    last_update_time = current_time.astimezone(timezone)
    return last_update_time

import os,sys,shutil
def sharepoint_copy_file(request):
    exe_dir = os.path.dirname(sys.executable) #current_run_location
    script_dir = os.path.dirname(__file__)
    relative_path = '..\\log\\user_logs.txt' 
    uploaded_file_path = os.path.abspath(os.path.join(script_dir, relative_path))
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    target_file_path = os.path.join(downloads_path, 'user_logs.txt')
    shutil.copyfile(uploaded_file_path, target_file_path)
    return JsonResponse({'finaldata': 'successful'})
'''
class ActivationCode:
    def __init__(self, user_id):
        self.user_id = user_id
        self.code = str(uuid.uuid4())
        self.expires_at = datetime.datetime.now() + datetime.timedelta(days=7)

    def is_expired(self):
        return datetime.datetime.now() > self.expires_at

    def activate(self):
        # 在這裡實現激活帳號的邏輯
        # 可以使用 user_id 或其他方法來找到相應的使用者並標記為已激活
        pass
'''
'''
import schedule
import time

def autodelete():
    # 這裡放置你想要執行的自動刪除程式碼
    print("每1個小時觸發的自動刪除函數已執行")

# 設定每1個小時觸發一次的任務
schedule.every(1).hours.do(autodelete)

while True:
    # 執行排程的任務
    schedule.run_pending()
    # 每1秒檢查一次是否有任務需要執行
    time.sleep(1)
'''
'''
CREATE TABLE user_account(
    id bigint PRIMARY KEY,
    account character varying,
    password character varying,
    activation_code character varying,
    last_update_time character varying,
    certificate varchar(50)
);
CREATE TABLE user_admin(
    id bigint PRIMARY KEY,
    account character varying,
    password character varying,
);
'''
'''
ALTER TABLE user_account ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;
'''