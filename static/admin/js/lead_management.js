/**
 * Gestión de leads - Comportamiento interactivo
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. COPIAR TELÉFONO Y MARCAR COMO MENSAJE_ENVIADO AL HACER CLICK
    document.querySelectorAll('.phone-copy').forEach(phone => {
        phone.addEventListener('click', async function() {
            const phoneNumber = this.getAttribute('data-phone');
            const leadId = this.getAttribute('data-lead-id');
            
            // Copiar al portapapeles
            try {
                await navigator.clipboard.writeText(phoneNumber);
                
                // Feedback visual
                const originalText = this.textContent;
                this.textContent = '✅ Copiado!';
                this.style.color = '#48bb78';
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.style.color = '#667eea';
                }, 2000);
                
                // Marcar como mensaje_enviado automáticamente
                updateLeadStatus(leadId, 'mensaje_enviado');
                
            } catch (err) {
                alert('📱 Número: ' + phoneNumber);
            }
        });
    });

    // 2. CAMBIAR ESTADO DESDE EL SELECT
    document.querySelectorAll('.status-selector').forEach(selector => {
        selector.addEventListener('change', async function() {
            const leadId = this.getAttribute('data-lead-id');
            const newStatus = this.value;
            
            await updateLeadStatus(leadId, newStatus);
        });
    });

    // 3. ABRIR WHATSAPP Y MARCAR COMO MENSAJE_ENVIADO
    document.querySelectorAll('.whatsapp-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const leadId = this.getAttribute('data-lead-id');
            
            // Marcar como mensaje_enviado cuando se abre WhatsApp
            setTimeout(() => {
                updateLeadStatus(leadId, 'mensaje_enviado');
            }, 1000);
        });
    });

    // 4. COPIAR LINK DE REGISTRO
    document.querySelectorAll('.copy-link-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            
            try {
                await navigator.clipboard.writeText(url);
                
                const originalText = this.textContent;
                this.textContent = '✅ Copiado!';
                this.style.background = '#48bb78';
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.style.background = '#48bb78';
                }, 2000);
                
            } catch (err) {
                prompt('Copia este link:', url);
            }
        });
    });
});

/**
 * Actualizar estado del lead vía AJAX
 */
async function updateLeadStatus(leadId, newStatus) {
    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        const response = await fetch(`/admin/pos/userregistration/${leadId}/update-status/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Recargar la página para mostrar cambios
            location.reload();
        } else {
            console.error('Error al actualizar estado');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}
