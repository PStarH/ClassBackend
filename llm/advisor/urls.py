from django.urls import path 
from llm.advisor import views 
 
urlpatterns = [ 
    path('plan/create', views.create_plan, name='create_plan'),
    path('plan/update', views.update_plan, name='update_plan'),
    path('plan/chat', views.chat_agent, name='chat_agent'),
    path('session/plan', views.get_plan_from_session, name='get_plan_from_session'),
    path('session/clear', views.clear_session, name='clear_session'),
]
