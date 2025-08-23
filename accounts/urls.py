from django.urls import path
from . import views
from . import admin_views

app_name = 'accounts'

urlpatterns = [
    # Autenticación
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterBusinessView.as_view(), name='register'),

    # Dashboard y configuración
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('configuracion/', views.ConfiguracionView.as_view(), name='configuracion'),

    # APIs
    path('api/usuarios-activos/', views.UsuariosActivosView.as_view(), name='usuarios_activos'),
    path('api/cerrar-sesion-usuario/', views.CerrarSesionUsuarioView.as_view(), name='cerrar_sesion_usuario'),
    
    # Admin interface - User management
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.user_management, name='user_management'),
    path('admin/edit-permissions/<int:user_id>/', admin_views.edit_user_permissions, name='edit_user_permissions'),
    path('admin/create-user/', admin_views.create_user, name='create_user'),
    path('admin/toggle-user-active/<int:user_id>/', admin_views.toggle_user_active, name='toggle_user_active'),
    path('admin/delete-user/<int:user_id>/', admin_views.delete_user, name='delete_user'),
    path('admin/business-settings/', admin_views.business_settings, name='business_settings'),
    
    # Permission check API
    path('api/check-permission/<str:permission_name>/', admin_views.check_permission, name='check_permission'),
]