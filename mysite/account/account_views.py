from O365 import Account
from O365.utils import BaseTokenBackend
import sys
from pathlib import Path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import connection
import json
import tempfile, os
def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

def admin_approve(user):
    if user == "bill.chang@hp.com" or user == "seanl@hp.com":
        return True
    else:
        return False

def user_account_approve(user, permission=None):
    if permission == "Microsoft":
        if user == "bill.chang@hp.com" or user == "catherine.jia@hp.com" or user == "timothy.wang1@hp.com" or user == "seanl@hp.com" or user == "yvonne.lai@hp.com" or user == "raizel.lee@hp.com":
            return True
        else:
            return False
    else:
        if user == "bill.chang@hp.com" or user == "catherine.jia@hp.com" or user == "timothy.wang1@hp.com" or user == "seanl@hp.com" or user == "yvonne.lai@hp.com" or user == "raizel.lee@hp.com":
            return True
        else:    
            return False

class JustToken(BaseTokenBackend):
    def __init__(self):
        super().__init__()

    def load_token(self):
        if self.token:
            return self.token
        return None

    def save_token(self):
        return self.token

    def check_token(self):
        return self.token is not None

class token_prove:
    def __init__(self, user):
        #self.account = Account(credentials=credentials, token_backend=token_backend)
        self.user = user
        self.token_backend = self.get_token_backend()
        self.token = self.token_backend.load_token()
        self.account = self.get_account

    @property
    @with_db_connection
    def get_credential(cursor, self):
        user_condition = f"AND ui.user_info->>'user_email' IN (%s)"
        query = f''' 
                SELECT ui.user_info -> 'token' ->> 'appid', ui.user_info -> 'token' ->> 'secret' 
                FROM user_info AS ui
                WHERE 1=1 {user_condition}
                '''
        cursor.execute(query, (self.user,))
        user_data = cursor.fetchone()
        [appid, secret] = user_data
        credentials = (appid, secret)
        print(credentials)
        return credentials

    @with_db_connection
    def __get_token_from_database(cursor, self):
        user_condition = f"AND ui.user_info->>'user_email' IN (%s)"
        query = f''' 
                SELECT ui.user_info
                FROM user_info AS ui
                WHERE 1=1 {user_condition}
                '''
        cursor.execute(query, (self.user,))
        user_token = cursor.fetchone()[0]
        return user_token
    
    def get_token_backend(self):
        database_token = self.__get_token_from_database()
        database_token_backend = JustToken()
        database_token_backend.token = json.loads(database_token)['token']['approve']             
        database_token_backend.load_token()
        self.token = database_token_backend.token
        return database_token_backend

    @property
    def curdir(self):
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        elif __file__:
            return Path(__file__).parent
            
    @property
    def get_account(self):
        credential = self.get_credential
        if self.token_backend.check_token():
            print("完成驗證account")
            return Account(credentials=credential,
                           token_backend=self.token_backend)
        else:
            if credential:
                account = Account(credential)
                if account.authenticate(scopes=[
                        'basic', 'users', 'address_book', 'message_all',
                        'onedrive_all', 'sharepoint'
                ]):
                    print('Authenticated')
                    return account
            else:
                print('Authenticate Fail !')
                return None

    @property
    def sharepoint(self):
        return self.account.sharepoint() if self.account else None
    @property
    def commsite(self):
        ret = self.sharepoint.search_site('comm tech')
        if len(ret) > 0: return ret[0]
        else: None
    @property
    def get_validation_lib(self):
        if self.account:
            validation_lib = [
                lib for lib in self.commsite.list_document_libraries()
                if lib.name == 'Validation and Quality Program'
            ][0]
            return validation_lib
        return None
    def get_folder_under_validation_lib(self, path):
        return self.get_validation_lib.get_item_by_path(path)
    def iur_from_sharepoint(self, path: str):
        folder = []
        for item in self.get_validation_lib.get_item_by_path(path).get_items():
            if item.is_folder: 
                folder.append(item.name)
        return folder
    def download_from_sharepoint(self, path: str, name: str, to_path=None):
        updater_binery = [
            i for i in self.get_validation_lib.get_item_by_path(path).get_items() if i.name == name
        ]
        if updater_binery:
            path = self.curdir.absolute().as_posix()
            if to_path:
                updater_binery[0].download(to_path)
                return None
            else:
                temp_dir = tempfile.mkdtemp()
                print("完成temp_dir", temp_dir)
                updater_binery[0].download(temp_dir)
                print("完成download0")
                temp_file_path = os.path.join(temp_dir, name)
                print(temp_file_path)  
                print("完成download")
                return temp_dir
def get_account(user):
    sp_instance = token_prove(user)
    account = sp_instance.account
    return account

def get_iur_sharepoint_folder(user):
    sp_instance = token_prove(user)
    folder_path = f'/IUR'
    folder_name = sp_instance.iur_from_sharepoint(folder_path)
    return  folder_name




@api_view(["post"])
@csrf_exempt
@with_db_connection
def add_member(cursor, request):
    user_id = request.user_id
    if user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    finaldatas = request.data.get('finaldata')
    print(finaldatas)
    for finaldata in finaldatas:
        if finaldata["email"].strip() == "" or finaldata["site"].strip() == "" or finaldata["username"].strip() == "":
            return JsonResponse({'error': 'User / email / site cannot be empty.'})
        if not finaldata["email"].strip().endswith("@hp.com"):
            return JsonResponse({'error': 'Email must end with @hp.com.'})
        query = f'''
            SELECT *
            FROM user_info AS ui
            WHERE ui.user_info ->> 'user_email' IN (%s)
        '''
        cursor.execute(query, (finaldata["email"],))
        if cursor.fetchone():
            return JsonResponse({'error': f"[{finaldata['email']}] already exists in the database, please check."})
    for finaldata in finaldatas:
        user_name = finaldata["username"]
        site = finaldata["site"]
        email = finaldata["email"]
        user_info = json.dumps({"user_email": email})
        cursor.execute("INSERT INTO user_info (user_name, user_site, user_info) VALUES (%s, %s, %s)", (user_name, site, user_info)) 
    return JsonResponse({'finaldata': 'successful'})

@api_view(["post"])
@csrf_exempt
@with_db_connection
def edit_member(cursor, request):
    id = request.data.get('id')
    name = request.data.get('name')
    email = request.data.get('email')
    site = request.data.get('site')
    user_id = request.user_id
    if user_account_approve(user_id) == False:
        return JsonResponse({'error': 'Insufficient permissions'})
    if not name or not email or not site:
        return JsonResponse({'error': "User / email / site cannot be empty."})
    cursor.execute(
        '''
        UPDATE user_info
        SET user_name = %s,
        user_info = jsonb_set(user_info, '{user_email}', %s::jsonb), 
        user_site = %s
        WHERE user_id = %s;
        ''',
        (name, json.dumps(email), site, id)
    )
    if cursor.rowcount == 0:
        return JsonResponse({'error': "User does not exist."})
    return JsonResponse({'finaldata': "successful"})