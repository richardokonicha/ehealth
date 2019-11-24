from django.urls import path
from ehealthApp.api.views import ( api_profile_view,
                                   api_update_profile_view,
                                   api_delete_profile_view,
                                   api_create_profile_view )

app_name = 'ehealthApp'
urlpatterns = [
    path('<slug>/', api_profile_view, name="api_profile_view"),
    path('<slug>/delete', api_delete_profile_view, name="api_delete_profile"),
    path('<slug>/update', api_update_profile_view, name="api_update_profile"),
    path('create/', api_create_profile_view, name="api_create_profile")

]

