import random
import string
from django.db import models
from django.contrib.auth.models import User

class Usuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre_completo = models.CharField(max_length=150)
    dni = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.nombre_completo} ({self.dni})"


class Mensaje(models.Model):
    ESTADOS = (
        ('PENDIENTE_PAGO', 'Pendiente de Pago'),
        ('ACTIVO', 'Activo / Custodiado'),
        ('EN_ESPERA', 'Esperando Fe de Vida (Gracia)'), 
        ('LIBERADO', 'Habilitado para Descifrar'),      
        ('LEIDO', 'Leído por Destinatario'),
        ('AUTODESTRUIDO', 'Eliminado Permanentemente'),
    )
    MODALIDADES = (
        ('TESTAMENTO', 'Modalidad Testamento (Fe de Vida)'),
        ('FECHA', 'Fecha Fija Futura'),
    )

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    contenido_cifrado = models.TextField()
    modalidad = models.CharField(max_length=20, choices=MODALIDADES, default='TESTAMENTO')
    fecha_liberacion = models.DateTimeField(null=True, blank=True)
    frecuencia_fe_vida = models.IntegerField(null=True, blank=True) # Días: 60, 90, 180, 365
    
    # --- NUEVOS CAMPOS PARA CONTROLAR LA FE DE VIDA ---
    fecha_ultima_fe_vida = models.DateTimeField(null=True, blank=True)
    en_periodo_gracia = models.BooleanField(default=False)
    fecha_limite_gracia = models.DateTimeField(null=True, blank=True)
    # --------------------------------------------------

    codigo_mensaje = models.CharField(max_length=10, unique=True, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE_PAGO')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_primera_lectura = models.DateTimeField(null=True, blank=True)
    leido_por = models.CharField(max_length=100, null=True, blank=True)

    def _str_(self): 
        return f"Mensaje {self.codigo_mensaje} - {self.usuario.nombre_completo}"

    def save(self, *args, **kwargs):
        # Si pasa a ACTIVO y no tiene fecha de última fe de vida, arranca el contador hoy
        if self.estado == 'ACTIVO' and not self.fecha_ultima_fe_vida:
            from django.utils import timezone
            self.fecha_ultima_fe_vida = timezone.now()

        if self.estado == 'ACTIVO' and not self.codigo_mensaje:
            while True:
                nuevo_codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                if not Mensaje.objects.filter(codigo_mensaje=nuevo_codigo).exists():
                    self.codigo_mensaje = nuevo_codigo
                    break
        super().save(*args, **kwargs)

    @property
    def dias_restantes(self):
        if self.fecha_primera_lectura:
            from django.utils import timezone
            pasado = timezone.now() - self.fecha_primera_lectura
            restante = 60 - pasado.days
            return max(0, restante)
        return 60

    def registrar_primera_lectura(self, nombre):
        if not self.fecha_primera_lectura:
            from django.utils import timezone
            self.fecha_primera_lectura = timezone.now()
            self.leido_por = nombre
            self.estado = 'LEIDO'
            self.save()


class Pago(models.Model):
    ESTADOS_PAGO = (
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    mensaje = models.OneToOneField(Mensaje, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')
    fecha_pago = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"Pago {self.id} - {self.estado} (${self.monto})"