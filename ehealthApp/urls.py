
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls import url
from .views import get_data, Ehealth_register, Ehealth_registerMed


urlpatterns = [
    path('', views.ehealth_home, name='ehealth_home'),
    path('about/', views.ehealth_about, name='ehealth_about'),
    path('tables/', views.ehealth_tables, name='ehealth_tables'),
    
    path('register/', views.Ehealth_register.as_view(template_name='ehealthApp/register.html'), name='ehealth_register'),
    #path('register/', views.ehealth_register, name='ehealth_register'),
    path('registerMed/', views.Ehealth_registerMed.as_view(template_name='ehealthApp/registerMed.html'), name='ehealthMed_register'),


    path('login/', auth_views.LoginView.as_view(template_name='ehealthApp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='ehealthApp/logout.html'), name='logout'),
    path('profile/', views.ehealth_profile, name='ehealth_profile'),
    url(r'^api/data/$', get_data, name='api-data'),
    url(r'^search/$', views.search, name='search'),

]


#for debug mode only 
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
