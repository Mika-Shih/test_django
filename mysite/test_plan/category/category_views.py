from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import connection
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
# Helper function to convert query result to a list of dictionaries
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Get View for Test Plan
def get_categories(request):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT DISTINCT jsonb_object_keys(category) as category_name
                FROM comm_test_item_list
                WHERE category IS NOT NULL;
                ''',
            )
            data = dictfetchall(cursor)
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
# update View for Test Item
@csrf_exempt
def update_item_category(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        category_name = data.get('category_name')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_item_list
                SET category = jsonb_set(category, %s, 'false')
                WHERE category IS NOT NULL;
                ''',
               ['{"' + category_name + '"}']
            )
        return JsonResponse({'success': 'Category added successfully.'})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
@csrf_exempt
def update_plan_category(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        category_name = data.get('category_name')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_plan_list
                SET category = jsonb_set(category, %s, 'false')
                WHERE category IS NOT NULL;
                ''',
               ['{"' + category_name + '"}']
            )
        return JsonResponse({'success': 'Category added successfully.'})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def delete_item_category(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        category_name = data.get('category_name')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_item_list
                SET category = category - %(category_name)s
                WHERE category ? %(category_name)s;
                ''',
               {'category_name': category_name}
            )
        return JsonResponse({'success': 'Category deleted successfully.'})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
@csrf_exempt
def delete_plan_category(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        category_name = data.get('category_name')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE comm_test_plan_list
                SET category = category - %(category_name)s
                WHERE category ? %(category_name)s;
                ''',
               {'category_name': category_name}
            )
        return JsonResponse({'success': 'Category deleted successfully.'})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)