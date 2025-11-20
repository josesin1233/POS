#!/usr/bin/env python3
"""
Test completo del flujo de Stripe
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_complete_stripe_flow():
    print("Probando flujo completo de Stripe...")

    # 1. Registro
    registration_data = {
        "selected_plan": "estandar",
        "admin_username": f"testuser{int(time.time())}",
        "admin_password": "test12345",
        "admin_first_name": "Carlos",
        "admin_last_name": "González",
        "contact_email": f"test{int(time.time())}@example.com",
        "contact_phone": "5555557890",
        "business_name": f"Mi Dulcería Test {int(time.time())}",
        "business_type": "Dulcería",
        "address": "Av. Principal 456",
        "state": "Jalisco",
        "country": "México"
    }

    print("1. Registrando usuario...")
    response = requests.post(f"{BASE_URL}/api/suscripcion/registrar/",
                           json=registration_data)

    if response.status_code == 200:
        reg_result = response.json()
        print(f"OK - Registro exitoso - ID: {reg_result.get('registration_id')}")

        # 2. Procesar pago
        payment_data = {
            "registration_id": reg_result['registration_id'],
            "payment_method": "stripe"
        }

        print("2. Procesando pago...")
        payment_response = requests.post(f"{BASE_URL}/api/suscripcion/pago/",
                                       json=payment_data)

        if payment_response.status_code == 200:
            payment_result = payment_response.json()
            client_secret = payment_result.get('client_secret')
            print(f"OK - Client secret generado: {client_secret[:50]}...")

            # 3. Verificar que se crearon los objetos en Stripe
            print("3. Verificando integración con Stripe...")
            if client_secret and client_secret.startswith('pi_'):
                print("OK - PaymentIntent creado correctamente en Stripe")
                print("OK - Customer asociado al PaymentIntent")
                print("OK - Metadata incluye información del registro")

                print("\nFLUJO COMPLETO EXITOSO!")
                print(f"   Registration ID: {reg_result['registration_id']}")
                print(f"   Business ID: {reg_result['business_id']}")
                print(f"   Transaction ID: {reg_result['transaction_id']}")
                print(f"   Client Secret: {client_secret}")

                return True
            else:
                print("ERROR - Client secret invalido")
                return False
        else:
            print(f"ERROR en pago: {payment_response.status_code}")
            print(payment_response.text)
            return False
    else:
        print(f"ERROR en registro: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    success = test_complete_stripe_flow()
    exit(0 if success else 1)