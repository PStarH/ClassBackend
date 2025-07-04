from django.urls import path
from . import views

urlpatterns = [
    # 练习题生成端点
    path('generate/', views.generate_exercises, name='generate_exercises'),
    path('generate-by-content/', views.generate_exercises_by_content, name='generate_exercises_by_content'),
    path('status/', views.exercise_service_status, name='exercise_service_status'),
]
