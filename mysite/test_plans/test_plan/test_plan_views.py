from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from datetime import datetime
import pytz
from user import user_views as user_views
def with_db_connection(func):
    def wrapper(*args, **kwargs):
        with connection.cursor() as cursor:
            return func(cursor, *args, **kwargs)
    return wrapper

# List View for Test Plan
@api_view(["post"])   
@csrf_exempt
@with_db_connection
def list_plan(cursor, request):
    user_id = request.user_id
    category = request.data.get('category')
    cursor.execute(
        '''
        SELECT id, category, type, plan_details
        FROM test_plan
        WHERE category = %s;
        ''',
        (category,)
    )
    rows = cursor.fetchall()
    all_data = []
    for row in rows:
        [id, category, type, plan_details] = row
        name = json.loads(plan_details)["name"]
        creator = json.loads(plan_details)["creator"]
        editor = json.loads(plan_details)["editor"]
        reviewer = json.loads(plan_details)["reviewer"]
        item_order = json.loads(plan_details)["item_order"]
        select = json.loads(plan_details)["select"]
        permission_data = {
            "reviewer_permission": user_views.mail_to_userid(user_id) in reviewer,
            "editor_permission": user_views.mail_to_userid(user_id) in editor,
            "reviewer": [user_views.userid_to_mail(num)[1] for num in reviewer],
            "editor": [user_views.userid_to_mail(num)[1] for num in editor],
        }
        cursor.execute(
            f'''
            SELECT id, plan_details, editor, plan_status, update_time
            FROM test_plan_record
            WHERE id IN ({', '.join(['%s'] * len(set(item_order)))});
            ''',
            tuple(set(item_order))
        )
        result = cursor.fetchall()
        data = {
            'id': id,
            'name': name,
            'category': category,
            'type': type,
            'select': item_order.index(select),
            'creator': creator,
            'permission': permission_data,
            'data': [
                {
                    'id': row[0],
                    'plan_details': json.loads(row[1]),
                    'editor_name': user_views.userid_to_mail(row[2])[0],
                    'case_status': row[3],
                    'update_time': row[4],
                } for row in result
            ],
        }
        all_data.append(data)
    all_data = sorted(all_data, key=lambda x: x['id'])
    return JsonResponse({'finaldata': all_data})
    
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
        (json.dumps(plan_details_info), user_views.mail_to_userid(user_id), "approve", timenow())
    )
    plan_id = cursor.fetchone()[0]

    plan_info = {
        "name": name,
        "creator": user_views.mail_to_userid(user_id),
        "editor": [user_views.mail_to_userid(num) for num in editor],
        "reviewer": [user_views.mail_to_userid(num) for num in reviewer],
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

# Edit for Test Plan
@api_view(["post"])
@csrf_exempt
@with_db_connection
def edit_plan(cursor, request):
    user_id = request.user_id
    plan_id = request.data.get('plan_id')
    # name = request.data.get('name')
    details = request.data.get('details')
    # editor = request.data.get('editor')
    # reviewer = request.data.get('reviewer')
    cursor.execute(
        '''
        SELECT id, category, type, plan_details
        FROM test_plan
        WHERE id = %s AND ((plan_details ->> 'editor') ::jsonb @> to_jsonb(ARRAY[%s]));
        ''',
        (plan_id, user_views.mail_to_userid(user_id))
    )
    result = cursor.fetchone()
    if not result:
       return JsonResponse({'error': 'Insufficient permissions'}) 
    else:
        [id, category, type, plan_details] = result
        item_order = json.loads(plan_details)["item_order"]
        cursor.execute(
            '''
            INSERT INTO test_plan_record (plan_details, editor, plan_status, update_time)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            ''',
            (json.dumps(details), user_views.mail_to_userid(user_id), "approve", timenow())
        )
        plan_record_id = cursor.fetchone()[0]
        item_order.append(plan_record_id)
        plan_info = {
            "name": json.loads(plan_details)["name"],
            "creator": json.loads(plan_details)["creator"],
            "editor": json.loads(plan_details)["editor"],
            "reviewer": json.loads(plan_details)["reviewer"],
            "select": plan_record_id,
            "item_order":item_order,
            "pending": [],
        }
        cursor.execute(
            '''
            UPDATE test_plan
            SET plan_details = %s
            WHERE id = %s;
            ''',
            (json.dumps(plan_info), plan_id)
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

