from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from datetime import datetime
import pytz
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
        "re_permission": mail_to_userid(user_id) in json.loads(case_permission)["admin"],
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
def create_plan(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    name = request.data.get('name')
    details = request.data.get('details')
    editor = request.data.get('editor')
    reviewer = request.data.get('reviewer')
    type = request.data.get('type')
    print(details)
    cursor.execute(
        '''
        SELECT * FROM test_plan
        WHERE plan_details ->> 'name' = %s 
        ''',
        (name,)
    )
    if cursor.fetchone():
        return JsonResponse({'error': 'name already exists.'})
    if not name :
        return JsonResponse({'error': 'name is required.'})
    plan_details_info = details


    cursor.execute(
        '''
        INSERT INTO test_plan_record (plan_details, editor, plan_status, update_time)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        ''',
        (json.dumps(plan_details_info), mail_to_userid(user_id), "approve", timenow())
    )
    plan_id = cursor.fetchone()[0]

    plan_info = {
        "name": name,
        "creator": mail_to_userid(user_id),
        "editor": [mail_to_userid(num) for num in editor],
        "reviewer": [mail_to_userid(num) for num in reviewer],
        "select": plan_id,
        "item_order":[plan_id],
        "pending": [],
    }
    cursor.execute(
        '''
        INSERT INTO test_plan (category, type, plan_details)
        VALUES (%s, %s, %s)
        ''',
        (category, type, json.dumps(plan_info))
    )
    return JsonResponse({'finaldata': 'Successful'})

# Update View for Test Plan
def update_plan(request, plan_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        data['added_time'] = timezone.now() #optional: frontend
        data['plan_id'] = plan_id
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_plan_list
                SET creator_id = %(creator_id)s,
                    reviewer_id = %(reviewer_id)s,
                    added_time = %(added_time)s,
                    version = %(version)s
                WHERE id = %(plan_id)s
                RETURNING id;
                ''',
                data
            )
            plan_id = cursor.fetchone()[0]
        return JsonResponse({'id': plan_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

# Delete View for Test Plan
def delete_plan(request, plan_id):
    if request.method == 'DELETE':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                DELETE FROM comm_test_plan_list
                WHERE id = %s;
                ''',
                [plan_id]
            )
            rows_affected = cursor.rowcount
        if rows_affected > 0:
            return JsonResponse({'message': 'Plan deleted successfully.'})
        else:
            return HttpResponseNotFound("Plan not found.")
    else:
        return HttpResponse(status=405)  # Return 405 Method Not Allowed for non-DELETE requests
    
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