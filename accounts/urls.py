from django.urls import path
from . import views

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
]