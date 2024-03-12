from django.template.loader import get_template
from O365 import Account,FileSystemTokenBackend,MSGraphProtocol
from O365.utils import BaseTokenBackend
import sys
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path

import win32com.client as win32

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
        #print(database_token)
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

def get_account():
    sp_instance = token_prove()
    account = sp_instance.account
    return account

def send_email_proxy(subject, to, cc, body):
    outlook = win32.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # 0表示olMailItem，代表Outlook郵件項目
    mail.Subject = subject
    mail.To = to
    mail.Body = body
    if cc:
        mail.cc.add(cc)   
    mail.SentOnBehalfOfName = "commslab@hp.com"
    if to=="bill.chang@hp.com" or to=="catherine.jia@hp.com":
        mail.Send() 


def send_activation_email(username, activation_link):
    template = get_template("polls/mail_borrow_rent.html")
    credentials = ('61d9f830-4547-48db-b8d0-e7a5760c79e7','HtN8Q~HjMvixbJ6flyDvRnBXH300pR9oeU1OwbmC')
    protocal   = MSGraphProtocol(api_version='beta')
    account = Account(credentials,protocol=protocal)
    message = f'請點擊以下連結來激活您的帳號：\n\n{activation_link}'
    '''
    context = {
                    #'receiver':'  '.join([t.usernameincompany for t in to]),
                    'message':activation_link,
                    'sender':account.get_current_user().full_name,
                    'att_files':'None'#att_files
                }  
    body = template.render(context)
    '''
    subject = '啟動帳號激活'
    to = username
    body = message
    #(account,to,cc=None,subject='',body='',attachments:list=None):
    cc=''
    return HP_mail(account,to,cc,subject,body)

#mail    
def HP_mail(account,to,cc=None,subject='',body='',attachments:list=None):
    mail = account.new_message()
    to = 'bill.chang@hp.com'
    #to = 'catherine.jia@hp.com'
    mail.to.add(to)
    mail.body=body
    mail.subject = subject
    cc = 'bill.chang@hp.com'
    #cc = 'catherine.jia@hp.com'
    if cc:
        if isinstance(cc, list):
            mail.cc.add(cc)
        else:
            mail.cc.add(cc)
        # mail.cc.add(cc)
    if attachments:
        mail.attachments.add(attachments)
    if to=="bill.chang@hp.com" or to=="catherine.jia@hp.com": 
        return mail.send()
