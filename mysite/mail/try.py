from pyOutlook import OutlookAccount, Recipient

# 創建 Outlook 帳戶對象
account = OutlookAccount()

# 設置發件人（代理人）
sender = Recipient(email_address="COMMs_system@hp.com")

# 設置收件人
recipients = [Recipient(email_address="bill.chang@hp.com")]

# 創建郵件對象
mail = account.new_mail(subject="test", body="empty", sender=sender, recipients=recipients)

# 發送郵件
mail.send()

