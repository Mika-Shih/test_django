from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import ollama

@csrf_exempt
def get_case_suggestion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        response = ollama.chat(model='llama3', messages=[
            {
                'role': 'user',
                'content': data['user_content'],
            },
            ])
        return JsonResponse({'ai_suggestion': response['message']['content']})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
