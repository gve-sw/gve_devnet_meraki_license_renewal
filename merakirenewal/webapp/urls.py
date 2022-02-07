from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('settings', views.settings, name='settings'),
    path('overview', views.overview, name='overview'),
    path('home', views.index, name='home'),
    path('logs', views.logs, name='logs'),
    path('download-logs', views.download_logs, name='download-logs'),
    path('download-overview', views.download_overview, name='download-overview'),
    path('download-overview-pdf', views.download_overview_pdf, name='download-overview-pdf'),
    path('download-logs-pdf', views.download_logs_pdf, name='download-logs-pdf'),
    path('extract-api-keys', views.upload_api_csv, name='extract-api-keys'),
    path('logsauth/', auth_views.LoginView.as_view(template_name="webapp/logsauth.html", extra_context={"hiddenLinks":True}), name="logsauth"),
]