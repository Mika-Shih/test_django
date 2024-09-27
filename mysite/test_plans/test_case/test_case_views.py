from django.http import JsonResponse, HttpResponseNotFound
from django.db import connection
import json
from datetime import datetime
import pytz # time zone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from user.token import LoginRequiredMiddleware #request.uesr_id
from log import log_views as log_views
def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

# List View for Test Case
@api_view(["post"])   
@csrf_exempt
@with_db_connection
def list_case(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    cursor.execute(
        '''
        SELECT id, category, case_details, update_time
        FROM test_case
        WHERE category = %s OR category = 'COMMON';
        ''',
        (category,)
    )
    rows = cursor.fetchall()
    if not rows:
        return JsonResponse({'error': 'No Data'})
    all_data = []
    for row in rows:
        [id, category, case_details, list_update_time] = row
        select = json.loads(case_details)["select"]
        version = json.loads(case_details)["item_order"]
        pending = json.loads(case_details)["pending"]
        print(version)
        cursor.execute(
            f'''
            SELECT case_details, editor, case_status, update_time
            FROM test_case_record
            WHERE id IN ({', '.join(['%s'] * len(set(version)))});
            ''',
            tuple(set(version))
        )
        result = cursor.fetchall()
        data = {
            'id': id,
            'reviewer': mail_to_userid(user_id) == (json.loads(case_details)["reviewer"] if json.loads(case_details)["reviewer"] != "" else json.loads(case_details)["creator"]),
            'editor': mail_to_userid(user_id) in json.loads(case_details)["editor"] or mail_to_userid(user_id) == json.loads(case_details)["creator"],
            'tag': json.loads(case_details)["tag"],
            'category': category,
            'creator_name': userid_to_mail(json.loads(case_details)["creator"])[0],
            'creator_mail': userid_to_mail(json.loads(case_details)["creator"])[1],
            'editor_mail': [userid_to_mail(num)[1] for num in json.loads(case_details)["editor"]],
            'reviewer_mail': userid_to_mail(json.loads(case_details)["reviewer"])[1] if json.loads(case_details)["reviewer"] != "" else "",
            'select': version.index(select),
            'data': [
                {
                    'case_name': json.loads(row[0])['name'],
                    'description': json.loads(row[0])['description'],
                    'comment': json.loads(row[0])['comment'],
                    'editor_name': userid_to_mail(row[1])[0],
                    'case_status': row[2],
                    'update_time': row[3],
                } for row in result
            ],
            'list_update_time': list_update_time,
        }
        all_data.append(data)
    return JsonResponse({'finaldata': all_data})
    
# Create View for Test Item
@api_view(["post"])   
@csrf_exempt
@with_db_connection
def create_case(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    name = request.data.get('name')
    description = request.data.get('description')
    comment = request.data.get('comment')
    tag = request.data.get('tag')
    reviewer = request.data.get('reviewer')
    print(reviewer)
    editor = request.data.get('editor')
    if not name or not description:
        return JsonResponse({'error': 'name or description is required.'})
    cursor.execute(
        '''
        SELECT * FROM test_case_record
        WHERE case_details ->> 'name' = %s;
        ''',
        (name,)
    )
    if cursor.fetchone():
        return JsonResponse({'error': 'name already exists.'})
    case_info = {
        "name": name,
        "description": description,
        "comment": comment,
    }
    cursor.execute(
        '''
        INSERT INTO test_case_record (case_details, editor, case_status, update_time)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        ''',
        (json.dumps(case_info), mail_to_userid(user_id), "approve", timenow())
    )
    case_id = cursor.fetchone()[0]

    case_list_info = {
        "creator": mail_to_userid(user_id),
        "editor": [mail_to_userid(num) for num in editor],
        "reviewer": mail_to_userid(reviewer) if reviewer else "",
        "select": case_id,
        "item_order":[case_id],
        "pending": [],
        "tag": tag,
    }
    cursor.execute(
        '''
        INSERT INTO test_case (category, case_details, update_time)
        VALUES (%s, %s, %s)
        ''',
        (category, json.dumps(case_list_info), timenow())
    )
    return JsonResponse({'finaldata': 'Successful'})

# Create View for Test Item
@api_view(["post"])   
@csrf_exempt
@with_db_connection
def edit_case(cursor, request):
    user_id = request.user_id
    id = request.data.get('id')
    name = request.data.get('name')
    description = request.data.get('description')
    comment = request.data.get('comment')
    reviewer = request.data.get('reviewer')
    print(reviewer)
    editor = request.data.get('editor')
    cursor.execute(
        '''
        SELECT case_details FROM test_case
        WHERE  id = %s;
        ''',
        (id,)
    )
    result = cursor.fetchone()
    if mail_to_userid(user_id) != json.loads(result[0])["creator"] and mail_to_userid(user_id) not in json.loads(result[0])["editor"]:
        return JsonResponse({'error': 'Insufficient permissions'})
    if not name or not description:
        return JsonResponse({'error': 'name or description is required.'})
    # cursor.execute(
    #     '''
    #     SELECT * FROM test_case_record
    #     WHERE case_details ->> 'name' = %s;
    #     ''',
    #     (name,)
    # )
    # if cursor.fetchone():
    #     return JsonResponse({'error': 'name already exists.'})
    case_info = {
        "name": name,
        "description": description,
        "comment": comment,
    }
    cursor.execute(
        '''
        INSERT INTO test_case_record (case_details, editor, case_status, update_time)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        ''',
        (json.dumps(case_info), mail_to_userid(user_id), "approve", timenow())
    )
    case_id = cursor.fetchone()[0]
    item_order = json.loads(result[0])["item_order"]
    print("Before appending:", item_order)
    print("case_id:", case_id)
    item_order.append(case_id)
    print("After appending:", item_order)
    case_list_info = {
        "creator": json.loads(result[0])["creator"],
        "editor": [mail_to_userid(num) for num in editor],
        "reviewer": mail_to_userid(reviewer) if reviewer else "",
        "select": case_id,
        "item_order":item_order,
        "pending": [],
        "tag": json.loads(result[0])["tag"],
    }
    cursor.execute(
        '''
        UPDATE test_case
        SET case_details = %s, update_time = %s
        WHERE id = %s;
        ''',
        (json.dumps(case_list_info), timenow(), id)
    )
    return JsonResponse({'finaldata': 'Successful'})

def timenow():
    current_time = datetime.now()
    timezone = pytz.timezone('Asia/Taipei')
    last_update_time = current_time.astimezone(timezone)
    return last_update_time

@with_db_connection
def mail_to_userid(cursor, user_email):
    cursor.execute(
        '''
        SELECT * FROM user_info
        WHERE user_info ->> 'user_email' = %s;
        ''',           
    (user_email,))
    return cursor.fetchone()[0]

@with_db_connection
def userid_to_mail(cursor, user_id):
    cursor.execute(
        '''
        SELECT user_name, user_info ->> 'user_email' FROM user_info
        WHERE user_id = %s;
        ''',           
    (user_id,))
    return cursor.fetchone()