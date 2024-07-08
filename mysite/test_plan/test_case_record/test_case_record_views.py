from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json

# Create View for Test item   
@csrf_exempt
def create_case_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO comm_test_item_changed_record (item_id, item_status, editor_id, reviewer_id, reviewer_comment, version, updated_time, item_details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                ''',
                [data['item_id'], data['item_status'], data['editor_id'], data['reviewer_id'], data['reviewer_comment'], data['version'], data['updated_time'], json.dumps(data['item_details'])]
            )
            item_record_id = cursor.fetchone()[0]
        return JsonResponse({'id': item_record_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
# Helper function to convert query result to a list of dictionaries
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@csrf_exempt
def get_personal_case_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        plan_id = data.get('plan_id')
        editor_id = data.get('editor_id')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT sub.*
                FROM (
                    SELECT DISTINCT ON (cticr.item_id)
                        cticr.*,
                        cticr.item_details->>'test_item_name' AS item_name,
                        cticr.item_details->>'description' AS description,
                        (
                            SELECT array_position(
                                ARRAY(
                                    SELECT jsonb_array_elements_text(ctp.plan_details->'item_order')::int
                                    FROM (
                                        SELECT *
                                        FROM comm_test_plan_changed_record
                                        WHERE plan_id =  %(plan_id)s AND editor_id = %(editor_id)s
                                        ORDER BY updated_time DESC
                                        LIMIT 1
                                    ) ctp
                                )::integer[],
                                cticr.item_id
                            )
                        ) AS item_order_position
                    FROM comm_test_item_changed_record cticr
                    WHERE cticr.item_id = ANY(
                        SELECT jsonb_array_elements_text(ctp.plan_details->'item_order')::int
                        FROM (
                            SELECT *
                            FROM comm_test_plan_changed_record
                            WHERE plan_id = %(plan_id)s AND editor_id = %(editor_id)s
                            ORDER BY updated_time DESC
                            LIMIT 1
                        ) ctp
                    )
                    ORDER BY cticr.item_id, cticr.updated_time DESC
                ) sub
                ORDER BY sub.item_order_position, sub.item_id, sub.updated_time DESC;
                ''',
                {'editor_id': editor_id, 'plan_id': plan_id}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

@csrf_exempt
def get_personal_plan_cases(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        item_order = data.get('item_order')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT DISTINCT ON (item_id)
                    item_id,
                    item_details->>'test_item_name' AS test_item_name
                FROM comm_test_item_changed_record
                WHERE item_id = ANY(%(item_order)s)
                ORDER BY item_id, updated_time DESC;
                ''',
                {'item_order': item_order}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def get_personal_case_specific_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        item_id = data.get('item_id')
        editor_id = data.get('editor_id')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT cr.*, il.category
                FROM comm_test_item_changed_record cr
                JOIN comm_test_item_list il ON cr.item_id = il.id
                WHERE cr.item_id = %(item_id)s AND cr.editor_id = %(editor_id)s
                ORDER BY cr.updated_time DESC
                LIMIT 1;
                ''',
                {'item_id': item_id, 'editor_id': editor_id}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

@csrf_exempt
def get_version_specific_record(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        ids = data.get('ids', [])
        all_data = []

        with connection.cursor() as cursor:
            for id in ids:
                cursor.execute(
                    '''
                    SELECT id, item_id, version, item_details->>'note' AS note, item_details->>'description' AS description, updated_time AS timestamp
                    FROM comm_test_item_changed_record
                    WHERE id = %s
                    ''',
                    [id]
                )
                data = dictfetchall(cursor)
                if data:
                    all_data.extend(data)

        return JsonResponse(all_data, safe=False)
    
@csrf_exempt
def get_category_all_case(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        category_name = data.get('category_name')
        print(category_name)
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT *
                FROM (
                    SELECT DISTINCT ON (ti.id) ti.id, tir.item_details->>'test_item_name' AS item_name,  tir.item_details->>'description' AS description, tir.item_status
                    FROM comm_test_item_list ti
                    JOIN comm_test_item_changed_record tir ON ti.id = tir.item_id
                    WHERE ti.category->> %(category_name)s = 'true'
                    ORDER BY ti.id, tir.updated_time DESC
                )AS subquery
                WHERE item_status != 'delete';
                ''',
                {'category_name': category_name}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

# Get View for Test item
@csrf_exempt
def get_case_record(request, item_id):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT * FROM comm_test_item_changed_record
                WHERE id = %s;
                ''',
                [item_id]
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)
    
# Get View for Test item
@csrf_exempt
def get_all_case_record(request):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT * FROM comm_test_item_changed_record
                WHERE item_status = 'approved';
                ''',
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)

@csrf_exempt
def get_all_version_record(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT id, version, item_details->>'note' AS note, updated_time AS timestamp
                FROM comm_test_item_changed_record
                WHERE item_id = %(item_id)s
                ORDER BY updated_time DESC;
                ''',
                {'item_id': item_id}
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
# Update View for Test item
@csrf_exempt
def update_case_record_status(request, item_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        data['updated_time'] = timezone.now() #optional: frontend
        data['item_id'] = item_id
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_item_changed_record
                SET item_status = %(item_status)s,
                    reviewer_comment = %(reviewer_comment)s,
                    updated_time = %(updated_time)s
                WHERE id = %(item_id)s
                RETURNING id;
                ''',
                data
            )
            item_id = cursor.fetchone()[0]
        return JsonResponse({'id': item_id})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def update_case_record_ai_suggestion(request):
    if request.method == 'PATCH':
        data = json.loads(request.body)
        print(data)
        item_id = data.get('item_id')
        description = data.get('description')
        data['updated_time'] = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                WITH LatestRecord AS (
                    SELECT item_id
                    FROM comm_test_item_changed_record
                    WHERE item_id =  %(item_id)s
                    ORDER BY updated_time DESC
                    LIMIT 1
                )
                UPDATE comm_test_item_changed_record
                SET item_details = item_details || jsonb_build_object('description', %(description)s)
                WHERE item_id IN (SELECT item_id FROM LatestRecord);
                ''',
                {'item_id': item_id, 'description': description}
            )
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
@csrf_exempt
def delete_case_from_plan(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        plan_id = data.get('plan_id')
        editor_id = data.get('editor_id')
        print(item_id, plan_id, editor_id)
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                WITH latest_record AS ( -- get the latest record of the plan
                    SELECT *
                    FROM comm_test_plan_changed_record
                    WHERE plan_id = %(plan_id)s and editor_id = %(editor_id)s
                    ORDER BY updated_time DESC
                    LIMIT 1
                )
                INSERT INTO comm_test_plan_changed_record (plan_id, plan_status, editor_id, reviewer_id, reviewer_comment, version, updated_time, plan_details) -- insert a new record with the latest record
                SELECT %(plan_id)s, latest_record.plan_status, latest_record.editor_id, latest_record.reviewer_id, latest_record.reviewer_comment, latest_record.version, NOW() AT TIME ZONE 'Asia/Taipei', jsonb_set(latest_record.plan_details, '{item_order}', (
                    SELECT jsonb_agg(value)
                    FROM jsonb_array_elements(latest_record.plan_details->'item_order') AS value
                    WHERE value::text <> %(item_id)s
                ))  -- delete the item from the item_order array
                FROM latest_record;
                ''',
                {'editor_id': editor_id, 'plan_id': plan_id, 'item_id': str(item_id)}
            )
            rows_affected = cursor.rowcount
        if rows_affected > 0:
            return JsonResponse({'message': 'Item deleted successfully.'})
        else:
            return HttpResponseNotFound("Item not found.")
    else:
        return HttpResponse(status=405)

@csrf_exempt
def delete_case_record(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        print(item_id)
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                WITH latest_record AS (
                    SELECT *
                    FROM comm_test_item_changed_record
                    WHERE item_id = %(item_id)s
                    ORDER BY updated_time DESC
                    LIMIT 1
                )
                INSERT INTO comm_test_item_changed_record (item_id, item_status, editor_id, reviewer_id, reviewer_comment, version, updated_time, item_details)
                SELECT %(item_id)s, 'delete', latest_record.editor_id, latest_record.reviewer_id, latest_record.reviewer_comment, latest_record.version, NOW() AT TIME ZONE 'Asia/Taipei', latest_record.item_details
                FROM latest_record;
                ''',
                 {'item_id': item_id}
            )
            rows_affected = cursor.rowcount
        if rows_affected > 0:
            return JsonResponse({'message': 'Item deleted successfully.'})
        else:
            return HttpResponseNotFound("Item not found.")
    else:
        return HttpResponse(status=405)  # Return 405 Method Not Allowed for non-DELETE requestsf