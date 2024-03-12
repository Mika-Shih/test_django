from O365 import Account, MSGraphProtocol, FileSystemTokenBackend
from O365.utils import BaseTokenBackend
import os
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path
import sys

file_path = "C:/Users/CHBI965/Desktop/156165.xlsx"
SERVER_HOST_NAME = "env-lab.eba-jpevj6xq.ap-southeast-1.elasticbeanstalk.com"

token_url = f'http://env-lab.eba-jpevj6xq.ap-southeast-1.elasticbeanstalk.com/api/mstoken/6'
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


class YourClass:
    def __init__(self):
        #self.account = Account(credentials=credentials, token_backend=token_backend)
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
            #source = os.path.join(self.__resource_path, 'credentials.json')
            #with open(source, 'r') as f:
                #data = json.load(f)
                #credentials = (data['appid'], data['secret'])
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
        print(self.get_token_backend())
        if self.token_backend.check_token():
            print('Authenticated')
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
            print("完成抓取_lib", validation_lib)
            return validation_lib
        return None
    
    def get_folder_under_validation_lib(self, path):
        return self.get_validation_lib.get_item_by_path(path)
    

    @property
    def get_tool_root(self):
        if self.account:
            return self.get_validation_lib.get_item_by_path(
                '/IUR/test_folder_Bill')
        return None
    
    def update_service_from_sharepoint(self, path: str, name: str, to_path=None):
        updater_binery = [
            i for i in self.get_validation_lib.get_item_by_path(path).get_items() if i.name == name
        ]
        if updater_binery:
            path = self.curdir.absolute().as_posix()
            if to_path:
                path = to_path
            print(path)    
            updater_binery[0].download(path)
            print("完成download")





    def upload_to_path(self, path: str, file_path: str):
            """Uploads a file to the specified path in the validation library.
            Args:
                path (str): The path of the file in the validation library.
                file_path (str): The path of the file to be uploaded.
            """

            print(self.get_validation_lib)
            drive_path = self.get_validation_lib.get_item_by_path(path)
            filename = os.path.basename(file_path)
            #覆蓋檔案
            with open(file_path, "rb") as file:
                drive_path.upload_file(file_path, filename)
                print("success upload file")           
            '''
             # 获取文件夹中的一个文件
                files_in_folder = drive_path.get_items()
                print(files_in_folder)
                if files_in_folder:
                     # 假设我们选择第一个文件
                    first_file = next(files_in_folder)
                    print(first_file)
                    # 获取文件元数据
                    file_metadata = first_file
                    print(file_metadata)
                    # 提取共享链接
                    #share_info = file_metadata.Copy_link("view")
                    share_link=file_metadata.share_with_link(share_scope='organization', account=self.account ).share_link
                    
                    print("Share link:", share_link)   
''' 

    def get_folder_share_link(self ,site_id, drive_id, folder_id, file_name):
        site_id = self.commsite
        print(site_id)
        '''
        access_token = self.token_backend.token
        file_path = f"/sites/{site_id}/drives/{drive_id}/items/{folder_id}/{file_name}"
        url = f"https://graph.microsoft.com/v1.0{file_path}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        print(access_token)
        response = requests.get(url, headers=headers)
        print(response)
        '''
        '''
        url = f"https://graph.microsoft.com/v1.0/drive/items/{file_id}/createLink"

            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "type": "view"  # 或者其他类型，如 edit
        }

        response = requests.post(url, headers=headers, json=data)
        print(response)
        if response.status_code == 200:
            share_info = response.json()
            share_link = share_info["link"]["webUrl"]
            return share_link
        else:
            print("Error getting folder share link:", response.text)
            return None
        '''
    def send_rent_borrowed_mail(self,request=None,to=None,borrow_records=None,return_records=None,cc=None,message:str='',attachments:list=None):    
        
        att_files = [ (file.name,file.share_with_link(share_scope='organization').share_link) for file in self.save_attachments_to_cloud(self.account,attachments)] if attachments else None
        print(att_files)
    def save_attachments_to_cloud(self,account,attachments) :
        '''
        save attachments to default onedrive and return list of urls
        '''
        print(attachments)
        att_files=[]
        root_folder = account.storage().get_default_drive().get_root_folder()
        print(root_folder)
        # get Attachment folder
        attachment_folder = None
        for f in root_folder.get_items():
            if 'Attachments' in f.name:
                attachment_folder = f
                break
        else:
            if not attachment_folder:
                attachment_folder = root_folder.create_child_folder('Attachments')
        
        for att in attachments:
            att_files.append(attachment_folder.upload_file(att))
            #att_urls.append(f.share_with_link(share_scope='organization').share_link)

        return att_files
         
your_instance = YourClass()
folder_path = f'/IUR/test_folder_Bill'
download_path = f'C:/Users/CHBI965/Downloads'
#your_instance.upload_to_path(folder_path, file_path)
#your_instance.get_folder_share_link('Comm Tech Team Sharepoint Site', 'Validation and Quality Program', folder_path, '156165.xlsx')
#your_instance.send_rent_borrowed_mail(attachments=file_path )
u='2222'
your_instance.update_service_from_sharepoint(folder_path, f'{u}.zip', download_path)