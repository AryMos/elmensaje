import json
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from .models import Usuario, Mensaje, Pago
from django.contrib import messages
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings

@login_required
def home(request):
    try:
        perfil_militar = Usuario.objects.get(user=request.user)
        nombre_pantalla = perfil_militar.nombre_completo
    except Usuario.DoesNotExist:
        nombre_pantalla = request.user.get_full_name() or request.user.username

    # Calculamos el saludo según la hora actual
    hora_actual = datetime.now().hour
    if 5 <= hora_actual < 12:
        saludo = "Buenos días"
    elif 12 <= hora_actual < 20:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    # Intentamos traer los mensajes asociados al usuario de forma segura
    try:
        perfil = Usuario.objects.get(user=request.user)
        mensajes = Mensaje.objects.filter(usuario=perfil)
    except Usuario.DoesNotExist:
        mensajes = Mensaje.objects.none()

    context = {
        'mensajes': mensajes,
        'dni_usuario_activo': request.user.username,
        'saludo_personalizado': f"¡Hola, {saludo}, {nombre_pantalla}!"
    }
    return render(request, 'usuarios/crear_mensaje.html', context)


@csrf_exempt
def guardar_mensaje_cifrado(request):
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'No autorizado'}, status=401)
            
            data = json.loads(request.body)
            contenido_cifrado = data.get('contenido_cifrado')
            modalidad = data.get('modalidad') 
            fecha_liberacion = data.get('fecha_liberacion')
            frecuencia_meses = data.get('frecuencia_fe_vida') 
            
            perfil_usuario, created = Usuario.objects.get_or_create(
                user=request.user,
                defaults={
                    'nombre_completo': request.user.username,
                    'dni': request.user.username,
                    'email': request.user.email
                }
            )

            # CONVERSIÓN: Pasamos los meses del formulario a días reales para la base de datos
            dias_calculados = None
            if modalidad == 'TESTAMENTO' and frecuencia_meses:
                meses = int(frecuencia_meses)
                if meses == 12:
                    dias_calculados = 365
                else:
                    dias_calculados = meses * 30

            mensaje = Mensaje.objects.create(
                usuario=perfil_usuario,
                contenido_cifrado=contenido_cifrado,
                modalidad=modalidad,
                fecha_liberacion=fecha_liberacion if modalidad == 'FECHA' else None,
                frecuencia_fe_vida=dias_calculados,
                estado='PENDIENTE_PAGO'
            )
            pago = Pago.objects.create(
                usuario=perfil_usuario,
                mensaje=mensaje,
                monto=5000.00,
                estado='PENDIENTE'
            )
            return JsonResponse({'status': 'success', 'mensaje_id': mensaje.id, 'pago_id': pago.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


def crear_preferencia_pago(request, mensaje_id):
    try:
        mensaje = Mensaje.objects.get(id=mensaje_id)
        pago_interno = Pago.objects.get(mensaje=mensaje)
        
        # 🔍 IMPRESIÓN DE DIAGNÓSTICO: Verificamos en la consola qué está leyendo exactamente Django
        print("\n🔎 ====== VERIFICANDO CONFIGURACIÓN ======")
        print(f"TOKEN EN MEMORIA: {settings.MERCADOPAGO_ACCESS_TOKEN}")
        print("==========================================\n")
        
        # Conectamos con el Token oficial seteado en settings
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        # OBTENEMOS EL EMAIL: Si el usuario no tiene mail cargado, usamos uno de respaldo para evitar fallas
        email_comprador = request.user.email if request.user.email else "comprador_anonimo@elmensaje.com"
        
        preference_data = {
            "items": [
                {
                    "title": f"Custodia Segura - Código {mensaje.codigo_mensaje}", 
                    "quantity": 1, 
                    "unit_price": round(float(pago_interno.monto), 2), 
                    "currency_id": "ARS"
                }
            ],
            "payer": {
                "email": email_comprador,
                "name": request.user.username
            },
            "back_urls": {
                "success": "https://pager-delta-repeated.ngrok-free.dev/pago/exitoso/",
                "failure": "https://pager-delta-repeated.ngrok-free.dev/pago/fallido/",
                "pending": "https://pager-delta-repeated.ngrok-free.dev/pago/pendiente/"
            },
            "auto_return": "approved",
            "external_reference": str(pago_interno.id),
        }
        
        preference_response = sdk.preference().create(preference_data)
        
        print("====== RESPUESTA MERCADO PAGO ======")
        print(json.dumps(preference_response, indent=2))
        print("====================================")
        
        link_de_pago = preference_response["response"]["init_point"]
        return JsonResponse({'status': 'success', 'init_point': link_de_pago})
        
    except Exception as e:
        print("💥 ====== FALLA EN PREFERENCIA ======")
        print(str(e))
        print("====================================")
        
        link_fallback = f"https://pager-delta-repeated.ngrok-free.dev/pago/exitoso/?external_reference={pago_interno.id}"
        return JsonResponse({'status': 'success', 'init_point': link_fallback, 'fallback': True, 'error_log': str(e)})

def pago_exitoso(request):
    pago_id = request.GET.get('external_reference')
    codigo_generado = ""
    if pago_id:
        try:
            pago_interno = Pago.objects.get(id=pago_id)
            mensaje = pago_interno.mensaje
            pago_interno.estado = 'APROBADO'
            pago_interno.save()
            mensaje.estado = 'ACTIVO'
            mensaje.save()  
            codigo_generado = mensaje.codigo_mensaje
        except Exception as e:
            print(f"Error al procesar pago: {e}")
    return render(request, 'usuarios/pago_exitoso.html', {'codigo': codigo_generado})


def vista_registro(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        dni = request.POST.get('dni', '').strip()
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=dni).exists():
            return render(request, 'usuarios/registro.html', {'error': 'Este DNI ya se encuentra registrado.'})
        try:
            user_sistema = User.objects.create_user(username=dni, email=email, password=password)
            Usuario.objects.create(user=user_sistema, nombre_completo=nombre, dni=dni, email=email)
            
            user_autenticado = authenticate(username=dni, password=password)
            if user_autenticado:
                auth_login(request, user_autenticado)
            return redirect('home')
        except Exception as e:
            return render(request, 'usuarios/registro.html', {'error': f'Error en base de datos: {str(e)}'})
    return render(request, 'usuarios/registro.html')


def leer_mensaje_pantalla(request):
    return render(request, 'usuarios/leer_mensaje.html')


@csrf_exempt
def api_desencriptar_mensaje(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            codigo = data.get('codigo', '').strip().upper()
            nombre_familiar = data.get('nombre_destinatario', '').strip()
            
            try:
                mensaje = Mensaje.objects.get(codigo_mensaje=codigo, estado__in=['ACTIVO', 'LEIDO', 'LIBERADO'])
            except Mensaje.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Código incorrecto, mensaje inexistente o aún retenido por fe de vida.'}, status=404)
            
            if mensaje.modalidad == 'FECHA' and mensaje.fecha_liberacion:
                if timezone.now() < mensaje.fecha_liberacion:
                    fecha_local = timezone.localtime(mensaje.fecha_liberacion)
                    fecha_legible = fecha_local.strftime("%d/%m/%Y a las %H:%M hs")
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Cápsula Bloqueada. Este mensaje estará disponible el día {fecha_legible}.'
                    }, status=403)

            if mensaje.modalidad == 'TESTAMENTO' and mensaje.estado == 'EN_ESPERA':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Cápsula Bloqueada. El creador se encuentra en periodo de gracia para responder la fe de vida.'
                }, status=403)

            mensaje.registrar_primera_lectura(nombre_familiar)
            
            return JsonResponse({
                'status': 'success', 
                'contenido_cifrado': mensaje.contenido_cifrado, 
                'dias_restantes': mensaje.dias_restantes,
                'dni_creador': mensaje.usuario.dni
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


def index(request):
    return render(request, 'usuarios/index.html')


def login_usuario(request):
    if request.method == 'POST':
        dni_ingresado = request.POST.get('dni')
        password_ingresado = request.POST.get('password')
        
        usuario = authenticate(request, username=dni_ingresado, password=password_ingresado)
        
        if usuario is not None:
            auth_login(request, usuario)
            messages.success(request, "¡Bienvenido de nuevo!")
            return redirect('home')
        else:
            messages.error(request, "El DNI o la contraseña son incorrectos.")
            
    return render(request, 'usuarios/login.html')


def recuperar_password(request):
    if request.method == 'POST':
        messages.info(request, "Si el DNI existe, se enviarán las instrucciones de recuperación.")
        return redirect('login')
    return render(request, 'usuarios/recuperar_password.html')


@csrf_exempt
def api_editar_mensaje(request):
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'No autorizado'}, status=401)
                
            data = json.loads(request.body)
            mensaje_id = data.get('mensaje_id')
            contenido_cifrado = data.get('contenido_cifrado')
            modalidad = data.get('modalidad')
            fecha_liberacion = data.get('fecha_liberacion')
            frecuencia_meses = data.get('frecuencia_fe_vida')

            perfil_militar = Usuario.objects.get(user=request.user)
            mensaje = Mensaje.objects.get(id=mensaje_id, usuario=perfil_militar)

            mensaje.contenido_cifrado = contenido_cifrado
            mensaje.modalidad = modalidad
            
            if modalidad == 'FECHA':
                mensaje.fecha_liberacion = fecha_liberacion if fecha_liberacion else None
                mensaje.frecuencia_fe_vida = None
            else:
                mensaje.fecha_liberacion = None
                if frecuencia_meses:
                    meses = int(frecuencia_meses)
                    mensaje.frecuencia_fe_vida = 365 if meses == 12 else meses * 30

            mensaje.save()
            return JsonResponse({'status': 'success', 'message': 'Mensaje modificado correctamente'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


def cerrar_sesion_usuario(request):
    auth_logout(request)
    return redirect('index')


def reiniciar_fe_vida(request, mensaje_id):
    mensaje = get_object_or_404(Mensaje, id=mensaje_id)
    
    if mensaje.estado in ['ACTIVO', 'EN_ESPERA']:
        mensaje.fecha_ultima_fe_vida = timezone.now()
        mensaje.en_periodo_gracia = False
        mensaje.fecha_limite_gracia = None
        mensaje.estado = 'ACTIVO'
        mensaje.save()
        
        dias_totales = mensaje.frecuencia_fe_vida if mensaje.frecuencia_fe_vida else 60
        
        return render(request, 'usuarios/fe_vida_exitosa.html', {
            'mensaje': mensaje,
            'dias_totales': dias_totales
        })
    else:
        return render(request, 'usuarios/fe_vida_error.html', {'mensaje': mensaje})
    

def forzar_prueba_fe_vida(request, codigo_mensaje):
    mensaje = get_object_or_404(Mensaje, codigo_mensaje=codigo_mensaje.strip().upper())
    email_destinatario = "arielsantiagomosciaro@gmail.com" 
    link_confirmacion = f"https://pager-delta-repeated.ngrok-free.dev/usuarios/reiniciar-fe-vida/{mensaje.id}/"
    
    asunto = "⚠️ CONTROL DE FE DE VIDA - ACCIÓN REQUERIDA"
    cuerpo_mensaje = (
        f"Hola {mensaje.usuario.nombre_completo},\n\n"
        f"Este es un correo de prueba para verificar tu Fe de Vida en el sistema.\n"
        f"Si no confirmás tu estado, tu cápsula con código [{mensaje.codigo_mensaje}] se liberará.\n\n"
        f"Para confirmar que estás bien y resetear el tiempo, hacé clic en el siguiente enlace:\n"
        f"{link_confirmacion}\n\n"
        f"¡Saludos de la Bóveda!\n"
        f"Propiedad Intelectual y Desarrollo de Ariel Santiago Mosciaro."
    )
                     
    try:
        send_mail(
            asunto,
            cuerpo_mensaje,
            'El Mensaje <notificaciones.elmensaje@gmail.com>',
            [email_destinatario],
            fail_silently=False,
        )
        return JsonResponse({
            'status': 'success', 
            'message': f'Simulación exitosa. Mail enviado a {email_destinatario} para el código {codigo_mensaje}.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error al enviar el mail: {str(e)}'}, status=500)