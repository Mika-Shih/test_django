from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json

# Create View for Test Item
@csrf_exempt
def create_plan_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO comm_test_plan_changed_record (plan_id, plan_status, editor_id, reviewer_id, reviewer_comment, version, updated_time, plan_details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                ''',
                [data['plan_id'], data['plan_status'], data['editor_id'], data['reviewer_id'], data['reviewer_comment'], data['version'], data['updated_time'], json.dumps(data['plan_details'])]
            )
            plan_record_id = cursor.fetchone()[0]
        return JsonResponse({'id': plan_record_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

# # Helper function to convert query result to a list of dictionaries
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Get View for Test Plan
def get_plan_record(request, plan_id):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT * FROM comm_test_plan_changed_record
                WHERE id = %s;
                ''',
                [plan_id]
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

@csrf_exempt
def get_personal_specific_plan_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        editor_id = data.get('editor_id')
        plan_id = data.get('plan_id')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT *
                FROM (
                    SELECT DISTINCT ON (cplan.plan_id)
                        cplan.plan_id,
                        (cplan.plan_details->>'item_order') AS item_order,
                        (cplan.plan_details->>'test_plan_name') AS plan_name,
                        (cplan.plan_details->>'description') AS description,
                        cplan.editor_id,
                        cplan.plan_status,
                        cplan.reviewer_comment,
                        cplan.updated_time
                    FROM comm_test_plan_changed_record cplan
                    INNER JOIN comm_test_plan_list cplist ON cplan.plan_id = cplist.id
                    WHERE cplan.editor_id = %(editor_id)s
                        AND cplist.id = %(plan_id)s
                    ORDER BY cplan.plan_id, cplan.updated_time DESC
                ) AS subquery
                WHERE plan_status != 'delete';
                ''',
                {'editor_id': editor_id, 'plan_id': plan_id}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

# Get View for Test Plan 
@csrf_exempt
def get_personal_plan_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        editor_id = data.get('editor_id')
        category = data.get('category')
        with connection.cursor() as cursor:
            cursor.execute( 
                '''
                SELECT *
                FROM (
                    SELECT DISTINCT ON (cplan.plan_id)
                        cplan.plan_id,
                        (cplan.plan_details->>'test_plan_name') AS plan_name,
                        cplan.editor_id,
                        cplan.plan_status,
                        cplan.reviewer_comment,
                        cplan.updated_time
                    FROM comm_test_plan_changed_record cplan
                    INNER JOIN comm_test_plan_list cplist ON cplan.plan_id = cplist.id
                    WHERE cplan.editor_id = %(editor_id)s AND cplan.plan_details ->> 'category' = %(category)s
                    ORDER BY cplan.plan_id, cplan.updated_time DESC
                ) AS subquery
                WHERE plan_status != 'delete';
                ''',
                {'editor_id': editor_id, 'category': category}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)
    
# Get All View for Test plan
def get_all_plan_record(request):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT * FROM comm_test_plan_changed_record
                WHERE plan_status = 'approved';
                ''',
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

@csrf_exempt
def update_plan_record_status(request, plan_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        data['plan_id'] = plan_id
        data['updated_time'] = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_plan_changed_record
                SET plan_status = %(plan_status)s,
                    reviewer_comment = %(reviewer_comment)s,
                    updated_time = %(updated_time)s
                WHERE id = %(plan_id)s
                RETURNING id;
                ''',
                data
            )
            plan_id = cursor.fetchone()[0]
        return JsonResponse({'id': plan_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def delete_plan_record(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        print(plan_id)
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                WITH latest_record AS (
                    SELECT *
                    FROM comm_test_plan_changed_record
                    WHERE plan_id = %(plan_id)s
                    ORDER BY updated_time DESC
                    LIMIT 1
                )
                INSERT INTO comm_test_plan_changed_record (plan_id, plan_status, editor_id, reviewer_id, reviewer_comment, version, updated_time, plan_details)
                SELECT %(plan_id)s, 'delete', latest_record.editor_id, latest_record.reviewer_id, latest_record.reviewer_comment, latest_record.version, NOW() AT TIME ZONE 'Asia/Taipei', latest_record.plan_details
                FROM latest_record;
                ''',
                 {'plan_id': plan_id}
            )
            rows_affected = cursor.rowcount
        if rows_affected > 0:
            return JsonResponse({'message': 'Plan deleted successfully.'})
        else:
            return HttpResponseNotFound("Plan not found.")
    else:
        return HttpResponse(status=405)  # Return 405 Method Not Allowed for non-DELETE requests