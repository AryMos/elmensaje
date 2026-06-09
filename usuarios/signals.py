import secrets
import string
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pago, Mensaje

def generar_codigo_unico():
    """Genera un código aleatorio de 10 caracteres (letras mayúsculas y números)"""
    caracteres = string.ascii_uppercase + string.digits
    while True:
        # Genera algo como: 'X7K2M9P4LW'
        codigo = ''.join(secrets.choice(caracteres) for _ in range(10))
        # Nos aseguramos de que no exista ya en la base de datos
        if not Mensaje.objects.filter(codigo_mensaje=codigo).exists():
            return codigo

@receiver(post_save, sender=Pago)
def activar_mensaje_por_pago(sender, instance, created, **kwargs):
    """
    Cada vez que se guarda un Pago, si el estado es APROBADO,
    se le genera el código único al mensaje y se activa.
    """
    if instance.estado == 'APROBADO':
        mensaje = instance.mensaje
        
        # Solo le generamos código si todavía no tiene uno (evita pisarlo si se edita el pago)
        if not mensaje.codigo_mensaje:
            mensaje.codigo_mensaje = generar_codigo_unico()
            mensaje.estado = 'ACTIVO'
            mensaje.save()
            