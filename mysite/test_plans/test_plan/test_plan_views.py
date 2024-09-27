from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt

# Create View for Test Item
@csrf_exempt
def create_plan(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO comm_test_plan_list (reviewer_id, added_time, version, category)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                ''',
                [ data['reviewer_id'], data['added_time'], data['version'], json.dumps(data['category'])]
            )
            plan_id = cursor.fetchone()[0]
        return JsonResponse({'id': plan_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

# # Helper function to convert query result to a list of dictionaries
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Get View for Test Plan
def get_plan(request, plan_id):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT * FROM comm_test_plan_list
                WHERE id = %s;
                ''',
                [plan_id]
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

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