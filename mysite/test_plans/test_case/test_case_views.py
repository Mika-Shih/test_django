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
        SELECT case_permission 
        FROM test_case_permission
        WHERE category = %s; 
        ''',
        (category,)
    )
    result = cursor.fetchone()
    [case_permission] = result
    permission_data = {
        "admin_permission": mail_to_userid(user_id) in json.loads(case_permission)["admin"],
        "editor_permission": mail_to_userid(user_id) in json.loads(case_permission)["editor"],
        "admin": [userid_to_mail(num)[1] for num in json.loads(case_permission)["admin"]],
        "editor": [userid_to_mail(num)[1] for num in json.loads(case_permission)["editor"]],
    }
    cursor.execute(
        '''
        SELECT id, category, case_details, update_time
        FROM test_case
        WHERE category = %s;
        ''',
        (category,)
    )
    rows = cursor.fetchall()
    all_data = []
    if not rows:
        return JsonResponse({'finaldata': all_data, 'permission': permission_data})
    for row in rows:
        [id, category, case_details, list_update_time] = row
        select = json.loads(case_details)["select"]
        version = json.loads(case_details)["item_order"]
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
            'tag': json.loads(case_details)["tag"],
            'category': category,
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
    all_data = sorted(all_data, key=lambda x: x['id'])
    return JsonResponse({'finaldata': all_data, 'permission': permission_data})
    
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
    cursor.execute(
        '''
        SELECT * FROM test_case_permission
        WHERE category = %s AND ((case_permission ->> 'admin') ::jsonb @> to_jsonb(ARRAY[%s])  OR (case_permission ->> 'editor') ::jsonb @> to_jsonb(ARRAY[%s]));
        ''',
        (category, mail_to_userid(user_id), mail_to_userid(user_id))
    )
    if not cursor.fetchone():
        return JsonResponse({'error': 'Insufficient permissions'})
    if not name or not description:
        return JsonResponse({'error': 'name or description is required.'})
    cursor.execute(
        '''
        SELECT * FROM test_case_record tcr
        JOIN test_case tc ON tcr.id = ANY(SELECT jsonb_array_elements_text(tc.case_details -> 'item_order')::int)
        WHERE tc.category = %s AND tcr.case_details ->> 'name' = %s;
        ''',
        (category, name)
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
        "select": case_id,
        "item_order":[case_id],
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
    tag = request.data.get('tag')
    category = request.data.get('category')
    cursor.execute(
        '''
        SELECT * FROM test_case_permission
        WHERE category = %s AND ((case_permission ->> 'admin') ::jsonb @> to_jsonb(ARRAY[%s])  OR (case_permission ->> 'editor') ::jsonb @> to_jsonb(ARRAY[%s]));
        ''',
        (category, mail_to_userid(user_id), mail_to_userid(user_id))
    )
    if not cursor.fetchone():
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
    cursor.execute(
        '''
        SELECT case_details FROM test_case
        WHERE id = %s;
        ''',
        (id,)
    )
    result = cursor.fetchone()
    item_order = json.loads(result[0])["item_order"]
    tag = json.loads(result[0])["tag"]
    item_order.append(case_id)
    case_list_info = {
        "select": case_id,
        "item_order":item_order,
        "tag": tag,
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

#Add category
@api_view(["post"])
@csrf_exempt
@with_db_connection
def add_category(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    if not category:
        return JsonResponse({'error': 'category is required.'})
    case_permission_info = {
        "admin": [mail_to_userid(user_id)],
        "editor": [],
    }
    cursor.execute(
        '''
        INSERT INTO test_case_permission (category, case_permission)
        VALUES (%s, %s);
        ''',
        (category, json.dumps(case_permission_info))
    )
    return JsonResponse({'finaldata': 'Successful'})

#test_case_permission
@api_view(["post"])
@csrf_exempt
@with_db_connection
def edit_permission(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    admin = request.data.get('admin')
    editor = request.data.get('editor')
    cursor.execute(
        '''
        SELECT * FROM test_case_permission
        WHERE category = %s AND ((case_permission ->> 'admin') ::jsonb @> to_jsonb(ARRAY[%s]))
        ''',
        (category, mail_to_userid(user_id))
    )
    if not cursor.fetchone():
        return JsonResponse({'error': 'Insufficient permissions'})
    else:
        case_permission_info = {
            "admin": [mail_to_userid(num) for num in admin],
            "editor": [mail_to_userid(num) for num in editor],
        }    
        cursor.execute(
            '''
            UPDATE test_case_permission
            SET case_permission = %s
            WHERE category = %s;
            ''',
            (json.dumps(case_permission_info), category)
        )
        operation = f"modify admin: {' '.join(admin)}, modify editor: {' '.join(editor)}"
        log_views.test_plan_log(user_id, operation)
        return JsonResponse({'finaldata': 'Successful'})

# time function 
def timenow():
    current_time = datetime.now()
    timezone = pytz.timezone('Asia/Taipei')
    last_update_time = current_time.astimezone(timezone)
    return last_update_time

# return user_id number
@with_db_connection
def mail_to_userid(cursor, user_email):
    cursor.execute(
        '''
        SELECT * FROM user_info
        WHERE user_info ->> 'user_email' = %s;
        ''',           
    (user_email,))
    return cursor.fetchone()[0]

#[0]: user_name, [1]: user_email
@with_db_connection
def userid_to_mail(cursor, user_id):
    cursor.execute(
        '''
        SELECT user_name, user_info ->> 'user_email' FROM user_info
        WHERE user_id = %s;
        ''',           
    (user_id,))
    return cursor.fetchone()