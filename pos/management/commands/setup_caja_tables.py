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
                            sucursal_id INTEGER REFERENCES pos_sucursal(id) ON DELETE SET NULL,
                            fecha_apertura TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                            fecha_cierre TIMESTAMP WITH TIME ZONE NULL,
                            usuario_apertura_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE PROTECT,
                            usuario_cierre_id INTEGER NULL REFERENCES accounts_user(id) ON DELETE PROTECT,
                            monto_inicial DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                            monto_final DECIMAL(10,2) NULL,
                            diferencia DECIMAL(10,2) NULL,
                            estado VARCHAR(20) NOT NULL DEFAULT 'abierta',
                            notas TEXT NULL
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
                            concepto VARCHAR(255) NOT NULL,
                            monto DECIMAL(10,2) NOT NULL,
                            tipo VARCHAR(50) NOT NULL DEFAULT 'gasto_operativo',
                            fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                            usuario_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE PROTECT,
                            caja_id INTEGER NULL REFERENCES pos_caja(id) ON DELETE SET NULL,
                            notas TEXT NULL
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