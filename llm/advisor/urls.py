from django.urls import path 
from llm.advisor import views 
 
urlpatterns = [ 
    path('/plan/create', views.create_plan, name='create_plan'),
]
