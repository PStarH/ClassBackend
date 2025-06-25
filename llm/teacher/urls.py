from django.urls import path
from . import views

urlpatterns = [
    path('create-outline/', views.create_outline, name='create_outline'),
    path('generate-section-detail/', views.generate_section_detail, name='generate_section_detail'),
]