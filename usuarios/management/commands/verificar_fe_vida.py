from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from usuarios.models import Mensaje

class Command(BaseCommand):
    help = 'Revisa los plazos de fe de vida y gestiona los periodos de gracia'

    def handle(self, *args, **options):
        ahora = timezone.now()
        self.stdout.write(self.style.SUCCESS(f"Iniciando verificación de fe de vida: {ahora}"))

        # --- PARTE A: BUSCAR PLAZOS VENCIDOS (Avisar y dar 10 días de gracia) ---
        mensajes_activos = Mensaje.objects.filter(modalidad='TESTAMENTO', estado='ACTIVO')
        
        for mensaje in mensajes_activos:
            # Calculamos cuándo se le vence el plazo original
            fecha_vencimiento = mensaje.fecha_ultima_fe_vida + timedelta(days=mensaje.frecuencia_fe_vida)
            
            if ahora >= fecha_vencimiento:
                # Se venció el plazo. Activamos los 10 días de gracia de corrido.
                mensaje.estado = 'EN_ESPERA'
                mensaje.en_periodo_gracia = True
                mensaje.fecha_limite_gracia = ahora + timedelta(days=10)
                mensaje.save()

                # Generamos el enlace para el botón de reinicio (temporalmente en localhost)
                url_reinicio = f"http://127.0.0.1:8000/usuarios/reiniciar-fe-vida/{mensaje.id}/"

                # Le mandamos el mail al dueño del mensaje
                asunto = "⚠️ ACCIÓN REQUERIDA: Confirmación de Fe de Vida - El Mensaje"
                cuerpo = (
                    f"Hola {mensaje.usuario.nombre_completo},\n\n"
                    f"Te informamos que se ha cumplido el plazo establecido para tu fe de vida.\n"
                    f"A partir de este momento, disponés de 10 días de corrido para confirmar que te encontrás bien.\n\n"
                    f"Para reiniciar el contador por otros {mensaje.frecuencia_fe_vida} días, por favor hacé clic en el siguiente enlace:\n"
                    f"{url_reinicio}\n\n"
                    f"IMPORTANTE: De lo contrario, una vez vencido el plazo de gracia, tu mensaje guardado quedará liberado automáticamente para su destinatario."
                )

                send_mail(
                    asunto,
                    cuerpo,
                    'notificaciones.elmensaje@gmail.com',
                    [mensaje.usuario.email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.WARNING(f"Mail de gracia enviado a: {mensaje.usuario.email} para mensaje {mensaje.codigo_mensaje}"))


        # --- PARTE B: BUSCAR VENCIDOS EN PERIODO DE GRACIA (Liberar el mensaje) ---
        mensajes_en_gracia = Mensaje.objects.filter(modalidad='TESTAMENTO', estado='EN_ESPERA', en_periodo_gracia=True)

        for mensaje in mensajes_en_gracia:
            if ahora >= mensaje.fecha_limite_gracia:
                # Pasaron los 10 días y no tocó el botón -> Se libera el mensaje
                mensaje.estado = 'LIBERADO'
                mensaje.en_periodo_gracia = False
                mensaje.save()
                
                self.stdout.write(self.style.ERROR(f"¡Plazo de gracia AGOTADO! Mensaje {mensaje.codigo_mensaje} liberado."))
                
        self.stdout.write(self.style.SUCCESS("Proceso de verificación terminado."))