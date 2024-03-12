'''
import requests
from requests.auth import HTTPBasicAuth
from O365.utils import BaseTokenBackend
import os, sys
from pathlib import Path
from O365 import Account
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


class sharepoint:
    def __init__(self):
        self.__set_token_database_config()
        self.token_backend = self.get_token_backend()
        self.token = self.token_backend.load_token()
        self.account = self.get_account
    def __set_token_database_config(self):
        self.server = SERVER_HOST_NAME
        self.token_url = f'http://{self.server}/api/mstoken/6'

    @property
    def get_credential(self):
        try:
            token_url = f'http://{self.server}/api/mstoken/6'
            token_data = requests.get(token_url)
            credentials = None
            if token_data.status_code == 200:
                token_data = token_data.json()
                credentials = (token_data['credentials']['appid'],token_data['credentials']['secret'])
            if credentials:
                return credentials
        except:
            return None

    def __get_token_from_database(self):
        try:
            r = requests.get(self.token_url,
                            auth=HTTPBasicAuth('admin', 'admin'))
            r = r.json()
            return r
        except Exception as e:
            print(e)
        return None
    
    def get_token_backend(self):
        database_token = self.__get_token_from_database()
        database_token_backend = JustToken()
        database_token_backend.token = database_token['token']
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
                path = to_path
            updater_binery[0].download(path)

sharepoint_download = sharepoint()
folder_path = f'/IUR/test_folder_Bill'
sharepoint_download.download_from_sharepoint(folder_path, "PowerStressTest-2.1.0.0_CTH_Test.zip")

'''