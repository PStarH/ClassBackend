from django.urls import path 
from backend import views 
 
urlpatterns = [ 
    path('api/tutorials/', views.tutorial_list, name='tutorial_list'),
    path('api/tutorials/<int:pk>/', views.tutorial_detail, name='tutorial_detail'),
    path('api/tutorials/published/', views.tutorial_list_published, name='tutorial_list_published')
]
