from django.template.loader import get_template

# import win32com.client as win32

# def send_email_proxy(subject, to, cc, body):
#     outlook = win32.Dispatch("Outlook.Application")
#     mail = outlook.CreateItem(0)  # 0表示olMailItem，代表Outlook郵件項目
#     mail.Subject = subject
#     mail.To = to
#     mail.Body = body
#     if cc:
#         mail.cc.add(cc)   
#     mail.SentOnBehalfOfName = "commslab@hp.com"
#     if to=="bill.chang@hp.com" or to=="catherine.jia@hp.com":
#         mail.Send() 


# def send_activation_email(username, activation_link):
#     template = get_template("polls/mail_borrow_rent.html")
#     credentials = ('61d9f830-4547-48db-b8d0-e7a5760c79e7','HtN8Q~HjMvixbJ6flyDvRnBXH300pR9oeU1OwbmC')
#     protocal   = MSGraphProtocol(api_version='beta')
#     account = Account(credentials,protocol=protocal)
#     message = f'請點擊以下連結來激活您的帳號：\n\n{activation_link}'
#     '''
#     context = {
#                     #'receiver':'  '.join([t.usernameincompany for t in to]),
#                     'message':activation_link,
#                     'sender':account.get_current_user().full_name,
#                     'att_files':'None'#att_files
#                 }  
#     body = template.render(context)
#     '''
#     subject = '啟動帳號激活'
#     to = username
#     body = message
#     #(account,to,cc=None,subject='',body='',attachments:list=None):
#     cc=''
#     return HP_mail(account,to,cc,subject,body)

#mail    
def HP_mail(account,to,cc=None,subject='',body='',attachments:list=None):
    mail = account.new_message()
    to = 'bill.chang@hp.com'
    #to = 'catherine.jia@hp.com'
    mail.to.add(to)
    mail.body=body
    mail.subject = subject
    cc = 'bill.chang@hp.com'
    # cc = 'catherine.jia@hp.com'
    if cc:
        if isinstance(cc, list):
            mail.cc.add(cc)
        else:
            mail.cc.add(cc)
    if attachments:
        mail.attachments.add(attachments)
    # if to=="bill.chang@hp.com" or to=="catherine.jia@hp.com": 
    return mail.send()      
