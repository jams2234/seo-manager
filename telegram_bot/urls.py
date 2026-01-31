from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from CoinGryComm import views

admin.site.site_header = 'Telegram Bot 관리자'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('seo_analyzer.urls')),  # SEO Analyzer API
    path('CoinGryComm', views.CoinGryComm, name="CoinGryComm"),
    path('game1callback', views.game1callback, name="game1callback"),
    path('tradinggamecallback', views.tradinggamecallback, name="tradinggamecallback"),
    path('kimp/<str:key>/', views.kimp, name="kimp"),
    # Serve React App (catch-all route - must be last)
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]
