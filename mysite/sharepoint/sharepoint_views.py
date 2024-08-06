from shareplum import Site
from shareplum import Office365
from shareplum.site import Version
from O365 import Account
from django.db import connection
import json
from O365.utils import BaseTokenBackend
import os, sys
from pathlib import Path
#file_path = "C:/Users/CHBI965/Desktop/0.xlsx"
# SERVER_HOST_NAME = "env-lab.eba-jpevj6xq.ap-southeast-1.elasticbeanstalk.com"
def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper
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
        #filesys_token_backend = FileSystemTokenBackend(
        #    token_path=self.__resource_path, token_filename='o365_token.txt')
        #self.token = filesys_token_backend.get_token()
        #if (database_token_backend.token and self.token) and (
        #        database_token_backend.token.expiration_datetime >
        #        self.token.expiration_datetime):
        #    self.token = database_token_backend.token
        #    return database_token_backend
        #return filesys_token_backend
    @property
    def curdir(self):
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        elif __file__:
            return Path(__file__).parent
            
    @property
    def get_account(self):
        credential = self.get_credential
        #print(self.get_token_backend())
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
    def file_from_sharepoint(self, path: str):
        file = []
        try:
            for item in self.get_validation_lib.get_item_by_path(path).get_items(): 
                file.append(item.name)
            return file    
        except:
            return file
    def upload_to_path(self, path: str, file_path: str):
            try:
                print(self.get_validation_lib)
                drive_path = self.get_validation_lib.get_item_by_path(path)
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as file:
                    drive_path.upload_file(file_path, filename)
            except Exception as e:        
                print("Error uploading file:", e)

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


import tempfile
def sharepoint_upload_file(user, uploaded_file, folder_path=None, file_name=None, get_share_link=False):                
    sharepoint_upload = token_prove(user)
    if folder_path is None:
        folder_path = f'/IUR/test_folder_Bill'
    #臨時文件夾位置C:\Users\CHBI965\AppData\Local\Temp\tmpzoliawib
    if file_name is None:
        file_name = uploaded_file.name
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file_name)
    
    with open(temp_file_path, 'wb') as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
            
    sharepoint_upload.upload_to_path(folder_path, temp_file_path)
    os.remove(temp_file_path)
    os.rmdir(temp_dir)

def sharepoint_download_file_zip(user, file_name, folder_path=None):
    sharepoint_download = token_prove(user)
    if folder_path is None:
        folder_path = f'/IUR/test_folder_Bill'
    
    print(file_name)
    file = sharepoint_download.download_from_sharepoint(folder_path, file_name)    
    return file

def get_iur_sharepoint_folder(user, folder_choose):
    sp_instance = token_prove(user)
    folder_choose = [item for item in folder_choose if item.strip()]
    folder_string = '/'.join(folder_choose)
    folder_path = f'/IUR/{folder_string}'
    folder_name = sp_instance.iur_from_sharepoint(folder_path)
    return  folder_name

def get_sharepoint_file_location(user, folder_choose):
    sp_instance = token_prove(user)
    folder_choose = [item for item in folder_choose if item.strip()]
    folder_string = '/'.join(folder_choose)
    folder_path = f'/IUR/{folder_string}'
    file_name = sp_instance.file_from_sharepoint(folder_path)
    return  file_name
