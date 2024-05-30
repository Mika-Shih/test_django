from datetime import datetime, timedelta
import jwt
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings

def LoginRequiredMiddleware(get_response):
    def middleware(request):
        
        # 檢查是否為登入、註冊或驗證頁面，如果是，則直接允許訪問
        '''
        allowed_paths = ['/user/login/', '/user/sign_up/', '/user/verify/']
        if request.path in allowed_paths:
            return get_response(request)
        '''
        allowed_paths = ['/api/user/', '/api/cth/']
        if any(request.path.startswith(path) for path in allowed_paths):
            return get_response(request)

        token = request.headers.get('Authorization', '').split('Bearer ')[-1]
        if not token:
            token = request.COOKIES.get('token')
        if not token:
            # 未登入，返回錯誤回應或執行其他操作
            return redirect('user:login')
        try:
            # 解析 Token，驗證是否有效
            payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            user_id = payload.get('user_id')
            request.user_id = user_id
            # 這裡可以進一步檢查 Token 的有效期等其他信息
           # return user_id
        except jwt.ExpiredSignatureError:
            # Token 過期
            return JsonResponse({'error': 'Token has expired.'}, status=401)

        except jwt.InvalidTokenError:
            # Token 無效
            return JsonResponse({'error': 'Invalid Token.'}, status=401)

        response = get_response(request)
        return response
    
    return middleware
'''
def analyze(request):
    token = request.COOKIES.get('token')
    payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
    user_id = payload.get('user_id')
    return user_id
    '''