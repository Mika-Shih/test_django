from shareplum import Site
from shareplum import Office365
from shareplum.site import Version
from O365 import Account, FileSystemTokenBackend, MSGraphProtocol


to = 'bill.chang@hp.com'

credentials = ('61d9f830-4547-48db-b8d0-e7a5760c79e7','HtN8Q~HjMvixbJ6flyDvRnBXH300pR9oeU1OwbmC')
if credentials:
    protocal   = MSGraphProtocol(api_version='beta')
    account = Account(credentials,protocol=protocal)
    if account.authenticate(scopes=['basic','users','address_book','message_all','onedrive_all','sharepoint']):
        print('Authenticated!')
        print('Mail will be sent')
    m = account.new_message()
    m.to.add(to)
    m.subject = 'Authenticated !'
    m.body = "Send Mail success"
    m.send()
    print('o365_token.txt will be generated')
else:
    print('Unable to get credentials')    
 

