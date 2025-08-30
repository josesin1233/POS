"""
Comando para crear las tablas de caja que faltan en producción
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = 'Crea las tablas de caja que faltan en la base de datos'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creación de tablas de caja...')
        
        try:
            # Primero, eliminar las tablas existentes si tienen el esquema incorrecto
            with connection.cursor() as cursor:
                self.stdout.write('Eliminando tablas incorrectas...')
                cursor.execute("DROP TABLE IF EXISTS pos_gastocaja CASCADE;")
                cursor.execute("DROP TABLE IF EXISTS pos_caja CASCADE;")
                self.stdout.write('✅ Tablas eliminadas')
            
            # Verificar si las tablas existen
            with connection.cursor() as cursor:
                # Verificar tabla pos_caja
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'pos_caja'
                    );
                """)
                caja_exists = cursor.fetchone()[0]
                
                # Verificar tabla pos_gastocaja
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'pos_gastocaja'
                    );
                """)
                gastocaja_exists = cursor.fetchone()[0]
                
                if not caja_exists:
                    self.stdout.write('Creando tabla pos_caja...')
                    cursor.execute("""
                        CREATE TABLE pos_caja (
                            id SERIAL PRIMARY KEY,
                            business_id INTEGER NOT NULL REFERENCES accounts_business(id) ON DELETE CASCADE,
                            sucursal_id INTEGER NOT NULL REFERENCES pos_sucursal(id) ON DELETE CASCADE,
                            usuario_apertura_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE RESTRICT,
                            usuario_cierre_id INTEGER NULL REFERENCES accounts_user(id) ON DELETE RESTRICT,
                            monto_inicial DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            monto_final DECIMAL(10,2) NULL,
                            total_ventas DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            total_efectivo DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            total_tarjetas DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            diferencia DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            estado VARCHAR(20) NOT NULL DEFAULT 'abierta',
                            fecha_apertura TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                            fecha_cierre TIMESTAMP WITH TIME ZONE NULL,
                            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
                            monto_actual DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            efectivo_real DECIMAL(10,2) NULL,
                            hora_cierre TIMESTAMP WITH TIME ZONE NULL,
                            notas_apertura TEXT NULL,
                            notas_cierre TEXT NULL
                        );
                    """)
                    
                    cursor.execute("CREATE INDEX pos_caja_business_id_idx ON pos_caja(business_id);")
                    cursor.execute("CREATE INDEX pos_caja_fecha_apertura_idx ON pos_caja(fecha_apertura);")
                    cursor.execute("CREATE INDEX pos_caja_estado_idx ON pos_caja(estado);")
                    
                    self.stdout.write(self.style.SUCCESS('✅ Tabla pos_caja creada exitosamente'))
                else:
                    self.stdout.write('ℹ️  Tabla pos_caja ya existe')
                
                if not gastocaja_exists:
                    self.stdout.write('Creando tabla pos_gastocaja...')
                    cursor.execute("""
                        CREATE TABLE pos_gastocaja (
                            id SERIAL PRIMARY KEY,
                            business_id INTEGER NOT NULL REFERENCES accounts_business(id) ON DELETE CASCADE,
                            concepto VARCHAR(200) NOT NULL,
                            monto DECIMAL(10,2) NOT NULL,
                            tipo VARCHAR(20) NOT NULL DEFAULT 'otro',
                            fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                            usuario_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE RESTRICT
                        );
                    """)
                    
                    cursor.execute("CREATE INDEX pos_gastocaja_business_id_idx ON pos_gastocaja(business_id);")
                    cursor.execute("CREATE INDEX pos_gastocaja_fecha_idx ON pos_gastocaja(fecha);")
                    cursor.execute("CREATE INDEX pos_gastocaja_tipo_idx ON pos_gastocaja(tipo);")
                    
                    self.stdout.write(self.style.SUCCESS('✅ Tabla pos_gastocaja creada exitosamente'))
                else:
                    self.stdout.write('ℹ️  Tabla pos_gastocaja ya existe')
                
                self.stdout.write(self.style.SUCCESS('🎉 Configuración de caja completada'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creando tablas: {str(e)}')
            )
            raise