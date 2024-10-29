from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import jwt
import bcrypt
import pytz #時間區域
from dateutil.parser import parse #時間字串改回時間 用於時間比較
import uuid #亂數碼
import hashlib, hmac, base64
import json
from django.template.loader import get_template
from mail import mail_views as mail_views
from account import account_views as account_views
from log import log_views as log_views
from user.token import LoginRequiredMiddleware
from django.db import connection

def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

def login(request):
    return render(request, 'polls/login.html')

def sign_up(request):
    return render(request, 'polls/sign_up.html')
# @api_view(["post"])
# @csrf_exempt
# # 創建帳號並發送激活郵件
# def create_account(request):
#     conn, cursor, close_database = connect_to_database()
#     username = request.data.get('username')
#     password = request.data.get('password')
#     user = (username, password)
#     print(user)
#     username="bill.chang@hp.com"
    
#     username_condition = f"AND (ui.user_info->>'user_email') = %s"
#     query = f'''
#     SELECT ui.user_info->>'last_update_time' AS last_update_time,
#         ui.user_info->>'certificate' AS certificate
#     FROM user_info AS ui
#     WHERE 1=1 {username_condition}
#     '''
#     cursor.execute(query, (username,))
#     result = cursor.fetchone()
#     if result:
#         last_update_time = result[0]
#         certificate = result[1]
#         close_database()
#         response_data = {
#         'error': '此用戶已存在',  # 替換成實際的重定向 URL
#         }
#         return JsonResponse(response_data)
#     else:   
#         activation_code = activation_code_generate()       
#         # 構建激活連結
#         activation_link = f'http://localhost:8000/user/activate/{activation_code}/'
#         #生成brcypt密碼
#         hashed_password = generate_hashed_password(password)
#         # 發送激活郵件
#         mail_views.send_activation_email(username, activation_link)
#         current_time = datetime.now() + timedelta(days=7)
#         timezone = pytz.timezone('Asia/Taipei')
#         last_update_time = current_time.astimezone(timezone)
#         user_info = {
#             "user_email": username,
#             "password": hashed_password,
#             "activation_code": activation_code,
#             'last_update_time': last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
#         }

#         user_info_json = json.dumps(user_info)
#         query = f"INSERT INTO user_info (user_info, user_name) VALUES (%s, %s)"
#         cursor.execute(query, (user_info_json, 'null'))
#         close_database()
#         response_data = {
#         'redirect_url': '/user/login/',  # 替換成實際的重定向 URL
#         }
#         return JsonResponse(response_data)


@api_view(["post"])
@csrf_exempt
@with_db_connection
def verify(cursor, request):
    username = request.data.get('email')
    password = request.data.get('password')
    print(username)
    certificate = 'True'
    certificate_condition = f"AND (ui.user_info->>'certificate') IN (%s)"
    accont_condition = f"AND (ui.user_info->>'user_email') IN (%s)"      
    query = f'''
    SELECT ui.user_info->>'password' AS password, user_id 
    FROM user_info AS ui
    WHERE 1=1 {accont_condition} {certificate_condition}
    '''
    cursor.execute(query, (username,) + (certificate,)) 
    result=cursor.fetchone()
    if  result:
        print(result[0])
        hashed_password=result[0]
        verify=verify_password(password, hashed_password)  
        if verify:
            cursor.execute(
                f'''
                SELECT ui.user_info->'token'->>'update_time' AS update_time
                FROM user_info AS ui
                WHERE 1=1 {accont_condition} {certificate_condition} AND ui.user_info ? 'token'
                ''',
                (username, certificate)
            )
            result_updatetime = cursor.fetchone()
            if result_updatetime:
                [update_time] = result_updatetime 
                update_time = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                if (current_time - update_time).days > 80:
                    return JsonResponse({'error': 'Token expired'})
            payload = {
                'user_id': username,
                'exp': datetime.utcnow() + timedelta(days=365 * 100)
                # 'exp': datetime.utcnow() + timedelta(hours=1)  
            }
            token = jwt.encode(payload, 'your-secret-key', algorithm='HS256')  # your-secret-key 是你的私鑰，保護 Token 的安全性
            log_views.log_operation(username, "Logged in")
            response_data = {
            'success': True,  
            'token': token,    
            'user': {
              '_id': result[1],  
              'username': username,
              'email': username,
            },  
            }
            return JsonResponse(response_data)       
    response_data = {
    'error': 'account or password error', 
    }
    return JsonResponse(response_data)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def change_password(cursor, request):
    user_id = request.user_id
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    if new_password != confirm_password:
        response_data = {
            'error': 'New password and confirm password do not match.', 
        }
        return JsonResponse(response_data)
    accont_condition = f"AND (ui.user_info->>'user_email') IN (%s)" 
    query = f'''
    SELECT user_id, ui.user_info->>'password' AS password 
    FROM user_info AS ui
    WHERE 1=1 {accont_condition}
    '''
    cursor.execute(query, (user_id,)) 
    result=cursor.fetchone()
    [id, hashed_password]=result
    verify = verify_password(old_password, hashed_password) 
    if verify:
        key = 'change-password'
        A = str(uuid.uuid4())
        B = base64.urlsafe_b64encode(hmac.new(key.encode(), A.encode(), hashlib.sha256).digest()).decode()[:7]
        system_mail(user='bill.chang@hp.com', to=user_id, message=B)
        response_data = {
        'finaldata': A, 
        }
    else:
        response_data = {
        'error': 'password error', 
        }
    return JsonResponse(response_data)

@api_view(["post"])
@csrf_exempt
@with_db_connection
def active_code(cursor, request):
    user_id = request.user_id
    A = request.data.get('A')
    B = request.data.get('B')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    if new_password != confirm_password:
        response_data = {
            'error': 'New password and confirm password do not match.', 
        }
        return JsonResponse(response_data)
    key = 'change-password'
    expected_B = base64.urlsafe_b64encode(hmac.new(key.encode(), A.encode(), hashlib.sha256).digest()).decode()[:7]
    if B == expected_B:
        query = '''
        UPDATE user_info AS ui
        SET user_info = jsonb_set(user_info, '{password}', %s::jsonb)
         WHERE user_info->>'user_email' = %s
        '''
        cursor.execute(query, (json.dumps(generate_hashed_password(new_password)), user_id))
        response_data = {
            'finaldata': 'password change success', 
        }
    else:
        response_data = {
            'error': 'activate code error', 
        }    
    return JsonResponse(response_data)   
        


@with_db_connection    
def activate_account(cursor, request, activation_code):
    activation_code_condition = f"AND (ui.user_info->>'activation_code') IN (%s)"
    query = f'''
    SELECT user_id, user_info, ui.user_info->>'last_update_time' AS last_update_time 
    FROM user_info AS ui
    WHERE 1=1 {activation_code_condition}
    '''
    cursor.execute(query, (activation_code,)) 
    result=cursor.fetchone()
    user_id=result[0]
    user_info=result[1]
    last_update_time=result[2]
    print(result)
    current_time = datetime.now()
    timezone = pytz.timezone('Asia/Taipei')
    last_update_time_now = current_time.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S")
    #if (parse(last_update_time) > last_update_time_now):
    print('yes')
    del user_info['activation_code']
    user_info['last_update_time'] = last_update_time_now
    user_info['certificate'] = 'True'
    print(user_info)
    user_info_json = json.dumps(user_info)
    update_query = f"UPDATE user_info SET user_info = %s WHERE user_id = %s"
    cursor.execute(update_query, (user_info_json, user_id))
    return HttpResponseRedirect("/user/login")


def logout(request):
    # 清除存儲在 Cookie 中的 Token
    response = JsonResponse({'redirect_url': '/user/login/'}) 
    response.delete_cookie('token')
    return response






# 生成加密後的密碼
def generate_hashed_password(password):
    salt = bcrypt.gensalt()  # 生成隨機的鹽值
    hashed_password = bcrypt.hashpw(password.encode(), salt)  # 將密碼與鹽值進行哈希計算
    return hashed_password.decode()  # 將二進制哈希值轉換為字串格式

# 驗證密碼是否正確
def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

# 生成激活碼
@with_db_connection   
def activation_code_generate(cursor):
    activation_code = str(uuid.uuid4())
    activation_code_condition = f"AND (ui.user_info->>'activation_code') IN (%s)"
    query = f'''
    SELECT user_id, ui.user_info->>'last_update_time' AS last_update_time
    FROM user_info AS ui
    WHERE 1=1 {activation_code_condition}
    '''
    cursor.execute(query, (activation_code,))
    result_activation_code=cursor.fetchone()
    print(result_activation_code)
    if result_activation_code:
        return activation_code_generate()
    else: 
        return activation_code 
    

# view account token 
@with_db_connection
def view_token(cursor, request):
    user_id = request.user_id
    if account_views.user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    query = f'''
    SELECT ui.user_info -> 'user_email' , ui.user_info -> 'token' ->> 'appid', ui.user_info -> 'token' ->> 'secret',
    ui.user_info -> 'token' ->> 'approve', ui.user_info -> 'token' ->> 'signin_url'
    FROM user_info AS ui
    WHERE ui.user_info ->> 'token' IS NOT NULL;
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    if rows:
        token_data = []
        for row in rows:
            data = {
                'email': row[0],
                'appid': row[1],
                'secret': row[2],
                'approve': row[3],
                'signin_url': row[4]
            }
            token_data.append(data)
    return JsonResponse ({'finaldata': token_data})


def system_mail(user,request=None,to=None,cc=None,message:str=''):
    template = get_template("polls/activate_code.html")
    account = account_views.get_account(user)
    if to:
        to_user = to.split('@')[0]
    if account:
        context = {
                    'receiver':to_user,
                    'message':message,
                }
        body = template.render(context)
        subject = "Activate code"   
        return mail_views.HP_mail(account,to,cc,subject,body)
    
@with_db_connection
def member(cursor, request):
    query = f'''
    SELECT ui.user_name, ui.user_info -> 'user_email', ui.user_site, ui.user_id
    FROM user_info AS ui
    WHERE ui.user_name != '' and ui.user_name != 'GUEST';
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    if rows:
        member_data = []
        for row in rows:
            data = {
                'name': row[0],
                'email': row[1].strip('"'),
                'site': row[2],
                'id': row[3],
            }
            member_data.append(data)
    return JsonResponse ({'finaldata': member_data})

