/*
JavaScript para funcionalidad interactiva del admin de gestión de usuarios
*/

document.addEventListener('DOMContentLoaded', function() {

    // Funcionalidad de copiar link
    function setupCopyLinkButtons() {
        const copyButtons = document.querySelectorAll('a[href*="/copy-link/"]');

        copyButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();

                fetch(this.href)
                    .then(response => response.json())
                    .then(data => {
                        if (data.url) {
                            // Copiar al portapapeles
                            navigator.clipboard.writeText(data.url).then(() => {
                                showNotification('✅ Link copiado al portapapeles', 'success');

                                // Cambiar texto del botón temporalmente
                                const originalText = this.innerHTML;
                                this.innerHTML = '✅ Copiado';
                                this.style.background = 'linear-gradient(135deg, #4CAF50, #45a049)';

                                setTimeout(() => {
                                    this.innerHTML = originalText;
                                    this.style.background = '';
                                }, 2000);
                            }).catch(() => {
                                // Fallback para navegadores que no soporten clipboard
                                showNotification('Link: ' + data.url, 'info');
                            });
                        } else {
                            showNotification('❌ ' + data.error, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showNotification('❌ Error al obtener el link', 'error');
                    });
            });
        });
    }

    // Sistema de notificaciones
    function showNotification(message, type = 'info') {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `admin-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span>${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;

        // Estilos inline para la notificación
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            transform: translateX(100%);
            transition: transform 0.3s ease;
            font-family: inherit;
        `;

        // Estilos según el tipo
        const typeStyles = {
            success: 'background: linear-gradient(135deg, #4CAF50, #45a049); color: white;',
            error: 'background: linear-gradient(135deg, #f44336, #d32f2f); color: white;',
            info: 'background: linear-gradient(135deg, #2196F3, #1976D2); color: white;',
            warning: 'background: linear-gradient(135deg, #ff9800, #f57c00); color: white;'
        };

        notification.style.cssText += typeStyles[type] || typeStyles.info;

        // Estilos para el contenido
        const content = notification.querySelector('.notification-content');
        content.style.cssText = `
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        `;

        // Estilos para el botón de cerrar
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: inherit;
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            line-height: 1;
            opacity: 0.7;
        `;

        // Agregar al DOM
        document.body.appendChild(notification);

        // Mostrar animación
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Funcionalidad de cerrar
        const closeNotification = () => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        };

        closeBtn.addEventListener('click', closeNotification);

        // Auto-cerrar después de 5 segundos
        setTimeout(closeNotification, 5000);
    }

    // Confirmación para acciones importantes
    function setupAdvanceButtons() {
        const advanceButtons = document.querySelectorAll('a[href*="/advance/"]');

        advanceButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                const action = this.textContent.trim();

                if (action.includes('Confirmar pago')) {
                    if (!confirm('¿Confirmar que el pago fue recibido? Se generará automáticamente un link de registro.')) {
                        e.preventDefault();
                    }
                } else if (action.includes('Activar usuario')) {
                    if (!confirm('¿Activar el usuario en el sistema POS? Esta acción creará la cuenta final.')) {
                        e.preventDefault();
                    }
                }
            });
        });
    }

    // Tooltips mejorados para la línea de tiempo
    function setupTimelineTooltips() {
        const timelineSteps = document.querySelectorAll('.timeline-step');

        timelineSteps.forEach(step => {
            step.addEventListener('mouseenter', function() {
                const tooltip = this.getAttribute('title');
                if (tooltip) {
                    // Crear tooltip personalizado
                    const tooltipElement = document.createElement('div');
                    tooltipElement.className = 'custom-tooltip';
                    tooltipElement.textContent = tooltip;
                    tooltipElement.style.cssText = `
                        position: absolute;
                        background: #333;
                        color: white;
                        padding: 8px 12px;
                        border-radius: 6px;
                        font-size: 12px;
                        z-index: 1000;
                        pointer-events: none;
                        opacity: 0;
                        transition: opacity 0.2s ease;
                    `;

                    document.body.appendChild(tooltipElement);

                    // Posicionar tooltip
                    const rect = this.getBoundingClientRect();
                    tooltipElement.style.left = rect.left + (rect.width / 2) - (tooltipElement.offsetWidth / 2) + 'px';
                    tooltipElement.style.top = rect.top - tooltipElement.offsetHeight - 8 + 'px';

                    // Mostrar
                    setTimeout(() => {
                        tooltipElement.style.opacity = '1';
                    }, 50);

                    // Remover al salir
                    this.addEventListener('mouseleave', function() {
                        if (document.body.contains(tooltipElement)) {
                            tooltipElement.style.opacity = '0';
                            setTimeout(() => {
                                if (document.body.contains(tooltipElement)) {
                                    document.body.removeChild(tooltipElement);
                                }
                            }, 200);
                        }
                    }, { once: true });
                }
            });
        });
    }

    // Filtros inteligentes
    function setupIntelligentFilters() {
        // Auto-refresh cada 30 segundos si hay usuarios en estados activos
        const hasActiveUsers = document.querySelector('.timeline-step.current');
        if (hasActiveUsers) {
            setTimeout(() => {
                if (document.querySelector('#changelist-search input').value === '') {
                    // Solo auto-refresh si no hay búsqueda activa
                    window.location.reload();
                }
            }, 30000);
        }
    }

    // Resaltado de filas según estado
    function setupRowHighlighting() {
        const rows = document.querySelectorAll('#result_list tbody tr');

        rows.forEach(row => {
            const statusCell = row.querySelector('.field-status_timeline');
            if (statusCell) {
                // Determinar estado según contenido
                if (statusCell.textContent.includes('💰')) {
                    row.style.background = 'linear-gradient(90deg, rgba(76, 175, 80, 0.1), transparent)';
                } else if (statusCell.textContent.includes('🚀')) {
                    row.style.background = 'linear-gradient(90deg, rgba(33, 150, 243, 0.1), transparent)';
                } else if (statusCell.textContent.includes('⏳')) {
                    row.style.background = 'linear-gradient(90deg, rgba(255, 152, 0, 0.1), transparent)';
                }
            }
        });
    }

    // Inicializar todas las funcionalidades
    setupCopyLinkButtons();
    setupAdvanceButtons();
    setupTimelineTooltips();
    setupIntelligentFilters();
    setupRowHighlighting();

    // Mejoras de UX
    console.log('🚀 Sistema de gestión de usuarios inicializado');
});

// Función global para actualizar estado (puede ser llamada desde otros scripts)
window.updateUserStatus = function(userId, newStatus) {
    fetch(`/admin/pos/userregistration/${userId}/advance/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        }
    });
};