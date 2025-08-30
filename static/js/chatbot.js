/**
 * DulcePOS Chatbot System
 * Sistema de chatbot para preguntas frecuentes
 */

class DulcePOSChatbot {
    constructor() {
        this.isOpen = false;
        this.qaDatabase = {
            // Preguntas sobre el sistema
            'sistema': [
                {
                    keywords: ['que es', 'qué es', 'que hace', 'funciona', 'para que sirve'],
                    question: '¿Qué es DulcePOS?',
                    answer: 'DulcePOS es un sistema punto de venta especializado para dulcerías y tienditas en México. Te ayuda a manejar inventario, ventas, códigos de barras y control de caja de manera fácil y profesional.'
                },
                {
                    keywords: ['precio', 'costo', 'cuanto cuesta', 'planes', 'mensualidad'],
                    question: '¿Cuánto cuesta DulcePOS?',
                    answer: 'Tenemos 3 planes: Básico ($299/mes), Intermedio ($449/mes) y Profesional ($699/mes). Cada plan incluye diferentes características. ¡Puedes probar nuestro demo gratuito!'
                },
                {
                    keywords: ['demo', 'prueba', 'gratis', 'probar'],
                    question: '¿Puedo probar el sistema?',
                    answer: 'Sí, tenemos un demo gratuito disponible en nuestra página principal. Puedes probar funciones básicas como agregar productos, usar el scanner y simular ventas.'
                }
            ],
            // Preguntas técnicas
            'tecnico': [
                {
                    keywords: ['scanner', 'escanear', 'codigo de barras', 'barras', 'camara'],
                    question: '¿Cómo funciona el scanner?',
                    answer: 'El scanner usa la cámara de tu dispositivo para leer códigos de barras. Haz clic en "Scan", permite acceso a la cámara y enfoca el código. También puedes escribir los códigos manualmente.'
                },
                {
                    keywords: ['inventario', 'productos', 'stock', 'agregar producto'],
                    question: '¿Cómo manejo el inventario?',
                    answer: 'Ve a "Inventario" en el menú. Puedes agregar productos manualmente, usar el scanner para códigos, establecer stock mínimo y recibir alertas cuando se agoten productos.'
                },
                {
                    keywords: ['ventas', 'vender', 'cobrar', 'pos', 'punto de venta'],
                    question: '¿Cómo hago una venta?',
                    answer: 'En "POS", busca productos por nombre o escanea códigos. Los productos se agregan al carrito automáticamente. Después haz clic en "Cobrar" para procesar la venta y generar el ticket.'
                },
                {
                    keywords: ['caja', 'efectivo', 'dinero', 'abrir caja', 'cerrar caja'],
                    question: '¿Cómo manejo la caja?',
                    answer: 'En "Caja" puedes abrir/cerrar caja diariamente, registrar el dinero inicial, ver ventas del día y registrar gastos. Al cerrar, el sistema calcula automáticamente diferencias.'
                }
            ],
            // Preguntas de soporte
            'soporte': [
                {
                    keywords: ['ayuda', 'soporte', 'problema', 'error', 'no funciona'],
                    question: '¿Dónde puedo obtener ayuda?',
                    answer: 'Puedes contactarnos por WhatsApp al 56 3809 7287. También tenemos tutoriales integrados en cada sección del sistema (busca el ícono "?" negro).'
                },
                {
                    keywords: ['whatsapp', 'contacto', 'telefono', 'mensaje'],
                    question: '¿Cómo los contacto?',
                    answer: 'Escríbenos por WhatsApp al 56 3809 7287 o haz clic en el botón de WhatsApp que aparece en varias partes del sistema. Respondemos rápido.'
                },
                {
                    keywords: ['suscribir', 'suscripcion', 'pagar', 'activar'],
                    question: '¿Cómo me suscribo?',
                    answer: 'Envía un mensaje por WhatsApp al 56 3809 7287 diciéndonos qué plan quieres. Te explicaremos el proceso de pago y activación de tu cuenta.'
                }
            ],
            // Preguntas generales
            'general': [
                {
                    keywords: ['horario', 'cuando', 'disponible'],
                    question: '¿En qué horarios dan soporte?',
                    answer: 'Nuestro soporte está disponible de lunes a sábado de 9:00 AM a 8:00 PM (hora de México). Los domingos respondemos emergencias.'
                },
                {
                    keywords: ['mexico', 'pesos', 'mexicanos'],
                    question: '¿Solo funciona en México?',
                    answer: 'Sí, DulcePOS está diseñado específicamente para el mercado mexicano, con precios en pesos y productos típicos de dulcerías mexicanas.'
                }
            ]
        };
        
        this.init();
    }

    init() {
        this.createChatbotHTML();
        this.attachEventListeners();
    }

    createChatbotHTML() {
        const chatbotHTML = `
            <!-- Botón flotante del chatbot -->
            <div id="chatbot-button" class="fixed bottom-4 right-4 z-50">
                <button class="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg transition-all duration-300 hover:scale-110" 
                        title="Chatbot de ayuda">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 3.04.97 4.36L2 22l5.64-.97C9.96 21.64 11.46 22 13 22h7c1.1 0 2-.9 2-2V12c0-5.52-4.48-10-10-10zm5 11h-2v2h-2v-2H9v-2h4V9h2v2h2v2z"/>
                    </svg>
                </button>
            </div>

            <!-- Panel del chatbot -->
            <div id="chatbot-panel" class="fixed bottom-20 right-4 w-96 max-w-[90vw] bg-white rounded-lg shadow-2xl z-50 hidden">
                <div class="bg-blue-600 text-white p-4 rounded-t-lg">
                    <div class="flex items-center justify-between">
                        <h3 class="font-bold text-lg">🤖 Asistente DulcePOS</h3>
                        <button id="chatbot-close" class="text-white hover:text-gray-200">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </button>
                    </div>
                    <p class="text-sm mt-1 opacity-90">¡Pregúntame sobre DulcePOS!</p>
                </div>

                <div id="chatbot-messages" class="h-80 overflow-y-auto p-4 bg-gray-50">
                    <div class="mb-4">
                        <div class="bg-blue-100 text-blue-800 p-3 rounded-lg text-sm">
                            ¡Hola! 👋 Soy tu asistente de DulcePOS. Puedes preguntarme sobre:
                            <br>• Cómo usar el sistema
                            <br>• Precios y planes
                            <br>• Problemas técnicos
                            <br>• ¡Cualquier duda!
                        </div>
                    </div>
                </div>

                <div class="p-4 border-t">
                    <div class="flex gap-2">
                        <input type="text" id="chatbot-input" 
                               class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" 
                               placeholder="Escribe tu pregunta aquí...">
                        <button id="chatbot-send" 
                                class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors">
                            Enviar
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
    }

    attachEventListeners() {
        const button = document.getElementById('chatbot-button');
        const panel = document.getElementById('chatbot-panel');
        const closeBtn = document.getElementById('chatbot-close');
        const input = document.getElementById('chatbot-input');
        const sendBtn = document.getElementById('chatbot-send');

        button.addEventListener('click', () => this.toggleChatbot());
        closeBtn.addEventListener('click', () => this.closeChatbot());
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    toggleChatbot() {
        const panel = document.getElementById('chatbot-panel');
        const button = document.getElementById('chatbot-button');
        
        if (this.isOpen) {
            this.closeChatbot();
        } else {
            panel.classList.remove('hidden');
            button.style.transform = 'scale(0.9)';
            this.isOpen = true;
            
            // Focus en el input
            setTimeout(() => {
                document.getElementById('chatbot-input').focus();
            }, 100);
        }
    }

    closeChatbot() {
        const panel = document.getElementById('chatbot-panel');
        const button = document.getElementById('chatbot-button');
        
        panel.classList.add('hidden');
        button.style.transform = 'scale(1)';
        this.isOpen = false;
    }

    sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        
        if (!message) return;

        // Mostrar mensaje del usuario
        this.addMessage(message, 'user');
        
        // Limpiar input
        input.value = '';

        // Simular "escribiendo..."
        setTimeout(() => {
            const response = this.generateResponse(message);
            this.addMessage(response, 'bot');
        }, 1000);
    }

    addMessage(message, sender) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'mb-4';

        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="flex justify-end">
                    <div class="bg-blue-600 text-white p-3 rounded-lg max-w-xs text-sm">
                        ${message}
                    </div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="flex justify-start">
                    <div class="bg-white border p-3 rounded-lg max-w-xs text-sm">
                        <div class="flex items-start gap-2">
                            <div class="text-blue-600 text-lg">🤖</div>
                            <div>${message}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    generateResponse(userMessage) {
        const message = userMessage.toLowerCase();
        
        // Buscar en todas las categorías
        for (const category in this.qaDatabase) {
            const questions = this.qaDatabase[category];
            
            for (const qa of questions) {
                for (const keyword of qa.keywords) {
                    if (message.includes(keyword.toLowerCase())) {
                        return qa.answer;
                    }
                }
            }
        }

        // Si no encuentra respuesta específica
        const fallbackResponses = [
            'Interesante pregunta. Te recomiendo contactarnos por WhatsApp al 56 3809 7287 para ayudarte mejor. 📱',
            'No tengo una respuesta específica para eso, pero nuestro equipo puede ayudarte por WhatsApp: 56 3809 7287 ✨',
            'Esa pregunta requiere atención personalizada. ¡Escríbenos por WhatsApp al 56 3809 7287! 💬',
            'Me encantaría ayudarte más. Para preguntas específicas, contacta por WhatsApp: 56 3809 7287 🚀'
        ];

        return fallbackResponses[Math.floor(Math.random() * fallbackResponses.length)];
    }
}

// Inicializar el chatbot cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Solo inicializar si no estamos en la landing page (que tiene su propio sistema)
    if (!window.location.pathname.includes('landing') && !document.getElementById('content-demo')) {
        new DulcePOSChatbot();
    }
});