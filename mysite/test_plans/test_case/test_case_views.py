from django.http import JsonResponse, HttpResponseNotFound
from django.db import connection
import json
from datetime import datetime
import pytz # time zone
import re
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from user.token import LoginRequiredMiddleware #request.uesr_id
from user import user_views as user_views 
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
        cursor.execute(
            f'''
            SELECT id, case_details, editor, case_status, update_time
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
                    'case_id': row[0],
                    'case_name': json.loads(row[1])['name'],
                    'description': json.loads(row[1])['description'],
                    'comment': json.loads(row[1])['comment'],
                    'editor_name': userid_to_mail(row[2])[0],
                    'case_status': row[3],
                    'update_time': row[4],
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
    if not tag or not re.match(r"^[A-Z][0-9]{2}$", tag):
        return JsonResponse({'error': 'tag is required and must be in the format of "A00".'})
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
    if approve_case(category, case_info):
        return JsonResponse({'error': 'name already exists.'})
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
        (category, user_views.mail_to_userid(user_id), user_views.mail_to_userid(user_id))
    )
    if not cursor.fetchone():
        return JsonResponse({'error': 'Insufficient permissions'})
    if not name or not description:
        return JsonResponse({'error': 'name or description is required.'})
    case_info = {
        "name": name,
        "description": description,
        "comment": comment,
    }
    if approve_case(category, case_info, id):
        return JsonResponse({'error': 'name or version already exists.'})
    cursor.execute(
        '''
        INSERT INTO test_case_record (case_details, editor, case_status, update_time)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        ''',
        (json.dumps(case_info), user_views.mail_to_userid(user_id), "approve", timenow())
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

#Modify select main case
@api_view(["post"])
@csrf_exempt
@with_db_connection
def select_case(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    id = request.data.get('id')
    select = request.data.get('select')
    print(category, id, select)
    cursor.execute(
        '''
        SELECT * FROM test_case_permission
        WHERE category = %s AND ((case_permission ->> 'admin') ::jsonb @> to_jsonb(ARRAY[%s])  OR (case_permission ->> 'editor') ::jsonb @> to_jsonb(ARRAY[%s]));
        ''',
        (category, mail_to_userid(user_id), mail_to_userid(user_id))
    )
    if not cursor.fetchone():
        return JsonResponse({'error': 'Insufficient permissions'})
    cursor.execute(
        '''
        UPDATE test_case
        SET case_details = jsonb_set(case_details, '{select}', %s::jsonb)
        WHERE id = %s;
        ''',
        (json.dumps(select), id)
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
    category = category.upper()
    cursor.execute(
        '''
        SELECT *
        FROM test_case_permission
        WHERE category = %s;
        ''',
        (category,)
    )
    if cursor.fetchone():
        return JsonResponse({'error': 'category already exists.'})
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

#View category
@with_db_connection
def view_category(cursor, request):
    cursor.execute(
        '''
        SELECT category
        FROM test_case_permission;
        '''
    )
    rows = cursor.fetchall()
    all_data = [row[0] for row in rows]
    return JsonResponse({'finaldata': all_data})

#Test case permission
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

#Test case permission
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


#Test case delete
@api_view(["post"])
@csrf_exempt
@with_db_connection
def delete_case(cursor, request):
    user_id = request.user_id
    id = request.data.get('id')
    case_id = request.data.get('case_id')
    cursor.execute(
        '''
        UPDATE test_case_record
        SET case_status = %s, update_time = %s
        WHERE id = %s
        ''',
        ("delete", timenow(), case_id))
    return JsonResponse({'finaldata': 'Successful'})

#Test case restore
@api_view(["post"])
@csrf_exempt
@with_db_connection
def restore_case(cursor, request):
    user_id = request.user_id
    id = request.data.get('id')
    case_id = request.data.get('case_id')
    cursor.execute(
        '''
        UPDATE test_case_record
        SET case_status = %s, update_time = %s
        WHERE id = %s
        ''',
        ("approve", timenow(), case_id))
    return JsonResponse({'finaldata': 'Successful'})

@with_db_connection
def approve_case(cursor, category, detail, case_list_id=None):
    if not isinstance(detail, dict) or not all(key in detail for key in ["name", "description", "comment"]):
        return True
    case_name = detail["name"]
    case_description = detail["description"]
    case_comment = detail["comment"]
    if case_list_id:
        cursor.execute(
            '''
            SELECT * 
            FROM test_case AS tc
            WHERE tc.id = %s
            AND EXISTS (
                SELECT 1
                FROM test_case_record AS tcr
                WHERE tcr.case_details ->> 'name' = %s AND tcr.case_details ->> 'description' = %s AND tcr.case_details ->> 'comment' = %s
                AND tcr.id IN (
                    SELECT jsonb_array_elements_text(tc.case_details->'item_order')::int
                )
            );
            ''',
            (case_list_id, case_name, case_description, case_comment)
        )
        if cursor.fetchone():
            return True
        cursor.execute(
            '''
            SELECT * 
            FROM test_case AS tc
            WHERE tc.id != %s AND tc.category = %s
            AND EXISTS (
                SELECT 1
                FROM test_case_record AS tcr
                WHERE tcr.case_details ->> 'name' = %s
                AND tcr.id IN (
                    SELECT jsonb_array_elements_text(tc.case_details->'item_order')::int
                )
            );
            ''',
            (case_list_id, category, case_name)
        )
        if cursor.fetchone():
            return True
    else:
        cursor.execute(
            '''
            SELECT * 
            FROM test_case AS tc
            WHERE tc.category = %s
            AND EXISTS (
                SELECT 1
                FROM test_case_record AS tcr
                WHERE tcr.case_details ->> 'name' = %s
                AND tcr.id IN (
                    SELECT jsonb_array_elements_text(tc.case_details->'item_order')::int
                )
            );
            ''',
            (category, case_name)
        )
        if cursor.fetchone():
            return True
    return False 
    





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