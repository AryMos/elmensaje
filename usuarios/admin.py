from django.contrib import admin
from .models import Usuario, Mensaje, Pago

# Registramos los nuevos modelos
admin.site.register(Usuario)
admin.site.register(Mensaje)
admin.site.register(Pago)
