from O365 import Account
from O365.utils import BaseTokenBackend
import sys
from pathlib import Path
from django.db import connection
import json

def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

def user_account_approve(user, permission=None):
    if permission == "Microsoft":
        if user == "bill.chang@hp.com" or user == "catherine.jia@hp.com":
            return True
        else:
            return False
    else:
        if user == "bill.chang@hp.com" or user == "catherine.jia@hp.com":
            return True
        else:    
            return False


SERVER_HOST_NAME = "env-lab.eba-jpevj6xq.ap-southeast-1.elasticbeanstalk.com"
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

def get_account(user):
    sp_instance = token_prove(user)
    account = sp_instance.account
    return account