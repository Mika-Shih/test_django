from O365 import FileSystemTokenBackend, Account, MSGraphProtocol
from O365.utils import BaseTokenBackend





mail_address = 'bill.chang@hp.com'


# token : https://login.microsoftonline.com/common/oauth2/nativeclient?code=0.AQoAooF5ylp4PUa4Kj24ffw85jD42WFHRdtIuNDnpXYMeecKAAA.AgABAAIAAAD--DLA3VO7QrddgJg7WevrAgDs_wUA9P_TtrRGOfv-N6yJIbuE5bg9acc3rhlaZylfgI5krCaVzfNFyFFtyt71Yog5Rurv3zNCz_EY7T9eei8E-vXL3H3JeYM9TRVYC1h0qLT6LhCWyYsk7HGzLRHmLKrNezZAX8tyyF2VtMxxEt6aGMILwKSkNpBziK5hTKf74bV9FAtdmWpmdk9f_jk8kjg4qJAAlMHZ7hR4gATaXseapFG_Kk0v2A9MndaDu1IXnF8CAV_HsaTcjcPAiGfXBRujYS0MadLSgNB_XdK0htbcxSlD4Od5P2_B-dbJJYdVBf7-1PmifWbvH-G3zJ1AAGvLEX62gkIksJlcnyUZOInBGlDX9iWueLuPllUHX_CKu1w1_JC7YH1QYU_OSTqfgYQcp9Fb_dLet5_0ylyyFVOoIGrJ3OL-gnXgRQxrmHcsBZ_H3_CpGgixHlSM__c8h2GLJKiQCozplsUz_q8P32Gx3StYfM18BDPrHB7iZha-OUtZcnSestJQ86C5E8DI8bF5UrTJeNTNUBAFlR1VoulWnvgiUq5yiWG4o_CeXmmiJBMxxaI6hWkRDfeTHnDeO-8_V2lJkpu4VKdYS6rNHAr00MKNzGDBI-v7MdVE-8hz7ClLLkRuXNJX75v3Rl3Xgh6_sm0P96SBehMbjruZezYSLaX27HnkycgqCLGujad8uaFP5dubXMZfSFjFzgen8EV_fbYEu_lh9B65GZEvAd0QOyFeWq31wT-4BnVDaZY64AAWqUroopsKuh29Z8WEIPJ9VI-ps2bOYPqbMf2pnumu9oFQ4V6k9TnJgUSo955D4r8J9KkHW70w-M_Fa-KReKJhlglD4sVBp06P-1jU-DoxkHh2EyAyMOtaToPHjI2Ruu6VGzCbsfktzo2jekmxTsdBoT0qjYUBnXA1dAsya08xDD5C4OQzT1yuNKjC4ZJTdXwpN87ygf6AaUc&state=Z0e93gPfmBFdAowr6j2K79L46zF4fN&session_state=12d93549-3fe0-41c6-b402-31238d442130

#https://login.microsoftonline.com/common/oauth2/nativeclient
# 值 : HtN8Q~HjMvixbJ6flyDvRnBXH300pR9oeU1OwbmC
# 用戶識別碼 : 61d9f830-4547-48db-b8d0-e7a5760c79e7
# 秘密識別碼 : 79e4a0d2-acef-4eff-b5ce-5282edafb345

#@app.command()

credentials = ('61d9f830-4547-48db-b8d0-e7a5760c79e7','HtN8Q~HjMvixbJ6flyDvRnBXH300pR9oeU1OwbmC')
#credentials = (token_data['credentials']['appid'],token_data['credentials']['secret'])
if credentials:
    protocal   = MSGraphProtocol(api_version='beta')
    account = Account(credentials,protocol=protocal)
    '''
    if account.authenticate(scopes=['basic','users','address_book','message_all','onedrive_all','sharepoint']):
        print('Authenticated!')
        print('Mail will be sent')
    '''   
    m = account.new_message()
    m.to.add([mail_address])
    m.subject = 'Authenticated !'
    m.body = "Send Mail success"
    m.send()
    print('o365_token.txt will be generated')
else:
    print('Unable to get credentials')    