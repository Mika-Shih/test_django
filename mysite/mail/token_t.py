from shareplum import Site
from shareplum import Office365
from shareplum.site import Version
from O365 import Account, FileSystemTokenBackend, MSGraphProtocol
import requests
import typer

mail_address = 'bill.chang@hp.com'
SERVER_HOST_NAME = "env-lab.eba-jpevj6xq.ap-southeast-1.elasticbeanstalk.com" 

app = typer.Typer()
@app.command()
def token_create(mail_address:str,id=6):
    token_url = f'http://{SERVER_HOST_NAME}/api/mstoken/{id}'
    token_data = requests.get(token_url)
    credentials = None
    if token_data.status_code == 200:
        token_data = token_data.json()
        credentials = (token_data['credentials']['appid'],token_data['credentials']['secret'])
    if credentials:
        protocal  = MSGraphProtocol(api_version='beta')
        account = Account(credentials,protocol=protocal)
        if account.authenticate(scopes=['basic','users','address_book','message_all','onedrive_all','sharepoint']):
            print('Authenticated!')
            print('Mail will be sent')
        m = account.new_message()
        m.to.add([mail_address])
        m.subject = 'Authenticated !'
        m.body = "Send Mail success"
        m.send()
        print('o365_token.txt will be generated')
    else:
        print('Unable to get credentials')    
token_create(mail_address)    