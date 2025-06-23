from django.contrib import admin
from django.urls import path, include 
 
urlpatterns = [ 
    path('admin/', admin.site.urls),
    path('api/tutorials', include('tutorials.urls')),
    path('api/advisor', include('llm.advisor.urls')),
]
