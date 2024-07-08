from django.http import JsonResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt

# Create View for Test Item
@csrf_exempt
def create_case(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO comm_test_item_list (plan_id, test_group, added_time, version, category)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                ''',
                [data['plan_id'], data['test_group'], data['added_time'], data['version'], json.dumps(data['category'])]
            )
            item_id = cursor.fetchone()[0]
            print(item_id)
        return JsonResponse({'id': item_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

# Helper function to convert query result to a list of dictionaries
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Get View for Test Plan
def get_case(request, case_id):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT * FROM comm_test_item_list
                WHERE id = %s;
                ''',
                [case_id]
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
# Update View for Test Item
def update_case(request, item_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        data['added_time'] = timezone.now() #optional: frontend
        data['item_id'] = item_id
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_item_list
                SET test_group = %(test_group)s,
                    creator_id  = %(creator_id)s,
                    added_time = %(added_time)s,
                    version = %(version)s
                WHERE id = %(item_id)s
                RETURNING id;
                ''',
                data
            )
            item_id = cursor.fetchone()[0]
        return JsonResponse({'id': item_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

# Delete View for Test Item
def delete_case(request, case_id):
    if request.method == 'DELETE':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                DELETE FROM comm_test_item_list
                WHERE id = %s;
                ''',
                [case_id]
            )
        return JsonResponse({'id': case_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)