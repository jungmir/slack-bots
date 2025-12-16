"""URL configuration for announcements app."""
from django.urls import path
from . import views

app_name = 'announcements'

urlpatterns = [
    path('slack/events', views.slack_events, name='slack_events'),
]
