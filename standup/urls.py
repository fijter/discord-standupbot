from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('form/<token>/', views.StandupFormView.as_view(), name='standup_form'),
    path('private/<token>/', views.PrivateStandupView.as_view(), name='private_standup'),
    path('<server>/<channel>/<standup_type>/<date>/', views.PublicStandupView.as_view(), name='public_standup'),
    path('overview/<token>/', views.PrivateHomeView.as_view(), name='private_home'),
    path('', views.HomeView.as_view(), name='home'),
]
