#寄信用
from O365 import Account,FileSystemTokenBackend,MSGraphProtocol, Message
from O365.utils import BaseTokenBackend

credentials = ('61d9f830-4547-48db-b8d0-e7a5760c79e7','HtN8Q~HjMvixbJ6flyDvRnBXH300pR9oeU1OwbmC')
protocal   = MSGraphProtocol(api_version='beta')
account = Account(credentials,protocol=protocal)
scopes = ['basic', 'message_all']

if not account.is_authenticated:
    account.authenticate(scopes=scopes)
   
message = 'good'
body = 'none'
subject = "Machines arrived"
to='bill.chang@hp.com'    
cc=''

mail = account.new_message()
mail.sent_on_behalf_of = 'COMMs_system@hp.com'
mail.to.add(to)
mail.body=body
mail.subject = subject
if cc:
    mail.cc.add(cc)
    
mail.send()