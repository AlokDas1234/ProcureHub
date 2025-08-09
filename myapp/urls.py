# myapp/urls.py

# from django.urls import path
# from django.shortcuts import render
#
# urlpatterns = [
#     path('', lambda request: render(request, 'myapp/index.html')),  # Correct path to your template
#
#
# ]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),             # Dashboard or redirect to login
    path('login/', views.login_view, name='login'),  # Login page
    path('register/', views.register_view, name='register'),  # Registration
    path('logout/', views.logout_view, name='logout'),  # Logout
    path('requirements/', views.create_requirement, name='requirements'),  # Logout
    path('delId/', views.del_requirement, name='delId'),  # Logout
    path('editId/', views.edit_requirement, name='editId'),
    path("bulk-upload/", views.bulk_upload_requirements, name="bulk_upload_requirements"),
# urls.py
    path('download-template/', views.download_template, name='download_template'),

path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

]
