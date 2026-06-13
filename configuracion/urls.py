from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views  # 🔒 Vistas nativas de seguridad de Django
from usuarios import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. Ahora la raíz limpia te lleva a la pantalla de bienvenida con cifrado militar
    path('', views.index, name='index'),
    
    # 2. Esta es tu pantalla principal de antes. La movemos a '/panel/' para usarla en la fase 1.3
    path('panel/', views.home, name='home'),
    
    # 3. Tu registro de siempre (mantenemos tu función 'vista_registro')
    path('registro/', views.vista_registro, name='registro'),
    
    # 4. Dejamos declarada la ruta para iniciar sesión (Paso 2)
    path('login/', views.login_usuario, name='login'),
    
    # 5. Cierre de sesión seguro y corregido
    path('logout/', views.cerrar_sesion_usuario, name='logout'),
    
    # Tus rutas de la API, Mensajes y Pagos
    path('api/guardar-mensaje/', views.guardar_mensaje_cifrado, name='guardar_mensaje'),
    path('api/crear-pago/<int:mensaje_id>/', views.crear_preferencia_pago, name='crear_pago'),
    path('leer/', views.leer_mensaje_pantalla, name='leer_mensaje'),
    path('api/desencriptar/', views.api_desencriptar_mensaje, name='api_desencriptar'),
    path('pago/exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('api/editar-mensaje/', views.api_editar_mensaje, name='api_editar_mensaje'),
    
    # --- RUTA PARA CONFIRMAR LA FE DE VIDA DESDE EL CORREO ---
    path('usuarios/reiniciar-fe-vida/<int:mensaje_id>/', views.reiniciar_fe_vida, name='reiniciar_fe_vida'),
    
    # --- RUTA DE PRUEBA CORREGIDA (Acepta el código de letras ej: FMSSV03PKR) ---
    path('probar-fe-vida/<str:codigo_mensaje>/', views.forzar_prueba_fe_vida, name='forzar_prueba_fe_vida'),

    # ==========================================================================
    # 🛡️ FLUJO TOTALMENTE NATIVO Y SEGURO DE RECUPERACIÓN DE CONTRASEÑA
    # ==========================================================================
    
    # Paso 1: Cambiamos el name a 'recuperar_password' para que coincida con tu HTML
    path('recuperar-password/', 
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), 
         name='recuperar_password'),
         
    # Paso 2: Mensaje en pantalla avisando que el correo fue despachado
    path('recuperar-password/enviado/', 
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), 
         name='password_reset_done'),
         
    # Paso 3: El enlace único con token secreto que le llega al usuario por mail
    path('recuperar-password/confirmar/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), 
         name='password_reset_confirm'),
         
    # Paso 4: Pantalla final confirmando el cambio exitoso de la clave
    path('recuperar-password/completo/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), 
         name='password_reset_complete'),
]