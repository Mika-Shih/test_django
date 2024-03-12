import datetime
import os


# 函數用於將操作記錄寫入日誌文件
def log_operation(user_id, operation, note=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - User {user_id}: {operation} // Note:{note}\n"
    print(log_entry)
  
    with open("log\\user_logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)
        print("Log operation written successfully")

def log_error(file_name, function, operation, note=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} -  {file_name}/{function}: {operation} // Note:{note}\n"
    print(log_entry)
  
    with open("log\\error_logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)
        print("Log error written successfully")

def cth_log_error(file_name, function, operation, note=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} -  {file_name}/{function}: {operation} // Note:{note}\n"
    print(log_entry)
  
    with open("log\\cth_error_logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

'''
# 獲取TOKEN並模擬使用者操作
user_id = "user123"
user_token = "your_user_token_here"

# 假設使用者執行了一些操作
operations = ["Viewed profile", "Updated settings", "Created post", "Logged out"]

# 將操作記錄寫入日誌文件
for operation in operations:
    log_operation(user_id, operation)

print("操作日誌已記錄並保存在user_logs.txt文件中。")
'''