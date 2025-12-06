"""
Middleware para restricción de acceso por IP al admin
"""
from django.core.exceptions import PermissionDenied
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AdminIPRestrictionMiddleware:
    """
    Middleware para restringir acceso al admin solo desde IPs autorizadas
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # IPs autorizadas para acceder al admin
        self.allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [
            '127.0.0.1',
            'localhost',
            '::1',  # IPv6 localhost
        ])

    def __call__(self, request):
        # Verificar si es una petición al admin
        if request.path.startswith('/admin/'):
            client_ip = self.get_client_ip(request)

            # En desarrollo permitir todas las IPs
            if settings.DEBUG:
                logger.info(f"Admin access from {client_ip} (DEBUG mode - allowed)")
                return self.get_response(request)

            # En producción verificar IP
            if client_ip not in self.allowed_ips:
                logger.warning(f"Blocked admin access from unauthorized IP: {client_ip}")
                raise PermissionDenied("Acceso al admin no autorizado desde esta IP")

            logger.info(f"Admin access allowed from authorized IP: {client_ip}")

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """
        Obtiene la IP real del cliente, considerando proxies
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Tomar la primera IP en caso de múltiples proxies
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip


class AdminSecurityHeadersMiddleware:
    """
    Middleware para agregar headers de seguridad específicos al admin
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Aplicar headers de seguridad solo al admin
        if request.path.startswith('/admin/'):
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'same-origin'
            response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:;"

        return response