from django.urls import path, include
from . import views
from . import auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/analyze/', views.analyze_interview, name='analyze_interview'),
    path('api/test/', views.test_connection, name='test_connection'),
    path('accounts/signup/', auth_views.signup, name='signup'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('community/<slug:slug>/', views.community_detail, name='community_detail'),
]
