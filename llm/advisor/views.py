from django.shortcuts import render

from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser 
from rest_framework import status
 
from rest_framework.decorators import api_view
from openai import OpenAI
from DjangoRestApisPostgreSQL.Configs.DeepSeek import DeepSeekConfig


@api_view(['POST'])
def create_plan(request):
    if request.method == 'POST':
        client = OpenAI(api_key=DeepSeekConfig['api_key'], base_url=DeepSeekConfig['base_url'])
        response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ],
        stream=False
    )    
    return JsonResponse({'message': response.choices[0].message.content})
    
