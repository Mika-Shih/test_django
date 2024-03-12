import psycopg2
import json
from datetime import datetime

host = "localhost"
dbname = "postgress"
user = "postgres"
password = "123456789"
sslmode = "allow"

# 資料庫連接設定
conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)

conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

# 執行查詢
query = '''
    SELECT ul.platform_id, ul.phase, pi.target, pi.product_group, pi.cycle, ul.sku, ul.serial_number,
            CASE WHEN subquery.status = 'Keep On' THEN -1 ELSE subquery.borrower_id END AS borrower_id,
             subquery.status, ul.position_in_site,
            subquery.remark, subquery.last_update_time
    FROM (
        SELECT DISTINCT ON (ur.uut_id) ur.record_id, ur.uut_id, ur.status, ur.last_update_time, ur.borrower_id, ur.remark
        FROM unit_record AS ur
        ORDER BY ur.uut_id, ur.last_update_time DESC
    ) subquery
    JOIN unit_list AS ul ON subquery.uut_id = ul.id
    JOIN platform_info AS pi ON ul.platform_id = pi.id
    LEFT JOIN user_info AS ui ON subquery.borrower_id = ui.user_id
    ORDER BY subquery.last_update_time DESC
    LIMIT 30;
'''
cursor.execute(query)

# 取得查詢結果
rows = cursor.fetchall()
users=[]
for row in rows:
    user_data = {
        'platform' : row[0],
        'phase' : row[1],
        'target' : row[2],
        'group' : row[3],
        'cycle' : row[4],
        'sku' : row[5],
        'sn' : row[6],
        'borrower_id' : row[7],
        'status' : row[8],
        'position' : row[9],
        'remark' : row[10],
        'last_update_time' : row[11],
    }
    users.append(user_data)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

json_data = json.dumps(users, cls=DateTimeEncoder)

# 輸出結果
print(json_data)

# 關閉資料庫連接
conn.commit()
cursor.close()
conn.close()
