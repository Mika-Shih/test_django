from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import psycopg2
import jwt
import bcrypt
import pytz #時間區域
from dateutil.parser import parse #時間字串改回時間 用於時間比較
import uuid #亂數碼
import json
from mail import mail_views as mail_views
from log import log_views as log_views
from django.db import connection
from db_utils import connect_to_database

def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

def sign_up(request):
    return render(request, "polls/sign_up.html")

def login(request):
    return render(request, "polls/login.html")

@api_view(["post"])
@csrf_exempt
# 創建帳號並發送激活郵件
def create_account(request):
    conn, cursor, close_database = connect_to_database()
    username = request.data.get('username')
    password = request.data.get('password')
    user = (username, password)
    print(user)
    username="bill.chang@hp.com"
    
    username_condition = f"AND (ui.user_info->>'user_email') = %s"
    query = f'''
    SELECT ui.user_info->>'last_update_time' AS last_update_time,
        ui.user_info->>'certificate' AS certificate
    FROM user_info AS ui
    WHERE 1=1 {username_condition}
    '''
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    if result:
        last_update_time = result[0]
        certificate = result[1]
        close_database()
        response_data = {
        'error': '此用戶已存在',  # 替換成實際的重定向 URL
        }
        return JsonResponse(response_data)
    else:   
        activation_code = activation_code_generate()       
        # 構建激活連結
        activation_link = f'http://localhost:8000/user/activate/{activation_code}/'
        #生成brcypt密碼
        hashed_password = generate_hashed_password(password)
        # 發送激活郵件
        mail_views.send_activation_email(username, activation_link)
        current_time = datetime.now() + timedelta(days=7)
        timezone = pytz.timezone('Asia/Taipei')
        last_update_time = current_time.astimezone(timezone)
        user_info = {
            "user_email": username,
            "password": hashed_password,
            "activation_code": activation_code,
            'last_update_time': last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        user_info_json = json.dumps(user_info)
        query = f"INSERT INTO user_info (user_info, user_name) VALUES (%s, %s)"
        cursor.execute(query, (user_info_json, 'null'))
        close_database()
        response_data = {
        'redirect_url': '/user/login/',  # 替換成實際的重定向 URL
        }
        return JsonResponse(response_data)


@api_view(["post"])
@csrf_exempt
@with_db_connection
def verify(cursor, request):
    username = request.data.get('email')
    password = request.data.get('password')
    user = (username, password)
    print(user)
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
            # 生成 Token
            payload = {
                'user_id': username,  # 可以在 Token 中包含使用者的身份信息
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
    'error': 'account or password error',  # 替換成實際的重定向 URL
    }
    return JsonResponse(response_data)
    
    
def activate_account(request, activation_code):
    conn, cursor, close_database = connect_to_database()
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
    close_database()
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
def activation_code_generate():
    conn, cursor, close_database = connect_to_database()    
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
    close_database() 
    if result_activation_code:
        return activation_code_generate()
    else: 
        return activation_code 
    

# view account token 
@with_db_connection
def view_token(cursor, request):
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