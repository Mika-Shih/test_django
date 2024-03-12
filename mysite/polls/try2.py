import psycopg2
import json
host = "localhost"
dbname = "postgress"
user = "postgres"
password = "123456789"
sslmode = "allow"

# 資料庫連接設定
conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)

conn = psycopg2.connect(conn_string)
cursor = conn.cursor()
# 解析請求中的 JSON 數據
targets = {"target":["DOCK","NB","AIO"]}
groups={"group":["COMMERICAL","CONSUMER"]}
platforms={"platform":["Able"]}
targetsearch2 = set(targets["target"])
groupsearch2 = set(groups["group"])
platformsearch2 = set(platforms["platform"])
print(platformsearch2)
# 創建一個佔位符字串，用於動態生成目標條件的部分 """"""""前面參數不能放數字""""""
targetsearch_placeholders = ', '.join(['%s'] * len(targetsearch2))
groupsearch_placeholders = ', '.join(['%s'] * len(groupsearch2))
platformsearch_placeholders = ', '.join(['%s'] * len(platformsearch2))
# 創建一個包含目標條件的元組
targetsearch3 = tuple(targetsearch2)
groupsearch3 = tuple(groupsearch2)
platformsearch3 = tuple(platformsearch2)
query = f'''
        SELECT subquery.cycle, array_agg(subquery.uut_id) AS uut_ids
        FROM (
            SELECT DISTINCT ON (ur.uut_id, pi.cycle) ur.uut_id, pi.cycle
            FROM unit_record AS ur
            JOIN unit_list AS ul ON ur.uut_id = ul.id
            JOIN platform_info AS pi ON ul.platform_id = pi.id
            LEFT JOIN user_info AS ui ON ur.borrower_id = ui.user_id
            WHERE pi.target IN ({targetsearch_placeholders}) AND pi.product_group IN ({groupsearch_placeholders})
            ORDER BY ur.uut_id, pi.cycle
        ) subquery
        GROUP BY subquery.cycle
        ORDER BY subquery.cycle
    '''
cursor.execute(query, targetsearch3+groupsearch3)
rows = cursor.fetchall()
users = []
for row in rows:
    user_data = {
        'cycle': row[0],
        
    }
    users.append(user_data)
    print(user_data)


conn.commit()
cursor.close()
conn.close()