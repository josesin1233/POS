/**
 * Sistema de Alertas Deslizantes para Productos con Poco Stock
 * Maneja notificaciones automáticas y interacciones del usuario
 */
class StockAlertSystem {
  constructor() {
    this.alerts = new Map();
    this.container = null;
    this.counter = null;
    this.checkInterval = null;
    this.isInitialized = false;
    this.alertQueue = [];
    this.maxVisibleAlerts = 5;
    this.settings = {
      checkInterval: 0, // Sin chequeos automáticos
      alertDuration: 10000,   // 10 segundos
      criticalThreshold: 0,  // Sin stock = crítico
      warningThreshold: 5,   // Menos de 5 = advertencia
      enabled: false,  // Deshabilitado por defecto
      sound: false  // Desactivar sonido por defecto
    };
  }

  /**
   * Inicializar el sistema de alertas
   */
  init(options = {}) {
    this.settings = { ...this.settings, ...options };
    
    if (this.isInitialized) {
      console.warn('StockAlertSystem ya está inicializado');
      return;
    }

    this.createContainer();
    this.createCounter();
    this.startPeriodicCheck();
    this.isInitialized = true;
    
    console.log('🚨 Sistema de alertas de stock inicializado');
  }

  /**
   * Crear el contenedor de alertas
   */
  createContainer() {
    this.container = document.createElement('div');
    this.container.className = 'alerts-container';
    this.container.id = 'stock-alerts-container';
    document.body.appendChild(this.container);
  }

  /**
   * Crear el contador de alertas
   */
  createCounter() {
    this.counter = document.createElement('div');
    this.counter.className = 'alert-counter hidden';
    this.counter.id = 'stock-alerts-counter';
    this.counter.innerHTML = '0';
    this.counter.addEventListener('click', () => this.toggleAllAlerts());
    document.body.appendChild(this.counter);
  }

  /**
   * Comenzar el chequeo periódico de productos con poco stock
   */
  startPeriodicCheck() {
    if (!this.settings.enabled || this.settings.checkInterval === 0) return;
    
    // NO hacer chequeo automático inicial
    
    // Solo hacer chequeo periódico si está habilitado Y tiene intervalo
    if (this.settings.checkInterval > 0) {
      this.checkInterval = setInterval(() => {
        this.checkLowStock();
      }, this.settings.checkInterval);
    }
  }

  /**
   * Parar el chequeo periódico
   */
  stopPeriodicCheck() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  /**
   * Verificar productos con poco stock desde la API
   */
  async checkLowStock() {
    try {
      const response = await fetch('/inventario/poco-stock/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          console.log('Usuario no autenticado - saltando verificación de stock');
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      this.processLowStockProducts(data.productos_bajo_stock || []);
      
    } catch (error) {
      console.error('Error verificando stock bajo:', error);
    }
  }

  /**
   * Procesar productos con stock bajo y crear alertas
   */
  processLowStockProducts(productos) {
    if (!Array.isArray(productos) || productos.length === 0) {
      this.updateCounter(0);
      return;
    }

    let newAlerts = 0;
    
    productos.forEach(producto => {
      const alertId = `stock-${producto.codigo}`;
      
      // Si la alerta ya existe, no crear duplicado
      if (this.alerts.has(alertId)) return;
      
      const severity = this.determineSeverity(producto.stock, producto.stock_minimo);
      const alert = this.createAlert(producto, severity);
      
      this.alerts.set(alertId, alert);
      this.showAlert(alert);
      newAlerts++;
    });

    this.updateCounter(this.alerts.size);
    
    if (newAlerts > 0) {
      console.log(`🔔 ${newAlerts} nuevas alertas de stock bajo`);
    }
  }

  /**
   * Determinar la severidad de la alerta según el stock
   */
  determineSeverity(stock, stockMinimo) {
    if (stock <= this.settings.criticalThreshold) {
      return 'critical';
    } else if (stock <= this.settings.warningThreshold) {
      return 'warning';
    } else if (stock < stockMinimo) {
      return 'warning';
    }
    return 'info';
  }

  /**
   * Crear elemento de alerta
   */
  createAlert(producto, severity) {
    const alert = document.createElement('div');
    alert.className = `stock-alert ${severity}`;
    alert.dataset.productCode = producto.codigo;
    alert.dataset.severity = severity;

    const icon = this.getAlertIcon(severity);
    const title = this.getAlertTitle(severity, producto);
    const message = this.getAlertMessage(producto);

    alert.innerHTML = `
      <div class="stock-alert-content">
        <div class="stock-alert-icon">${icon}</div>
        <div class="stock-alert-text">
          <div class="stock-alert-title">${title}</div>
          <div class="stock-alert-message">${message}</div>
          <div class="stock-alert-actions">
            <button class="stock-alert-btn primary" onclick="stockAlerts.goToInventory('${producto.codigo}')">
              📦 Reabastecer
            </button>
            <button class="stock-alert-btn" onclick="stockAlerts.dismissAlert('stock-${producto.codigo}')">
              ✓ Entendido
            </button>
          </div>
        </div>
      </div>
      <button class="stock-alert-close" onclick="stockAlerts.dismissAlert('stock-${producto.codigo}')">&times;</button>
      <div class="stock-alert-progress">
        <div class="stock-alert-progress-bar"></div>
      </div>
    `;

    return alert;
  }

  /**
   * Obtener icono según severidad
   */
  getAlertIcon(severity) {
    const icons = {
      critical: '🚨',
      warning: '⚠️', 
      info: '📊'
    };
    return icons[severity] || '📊';
  }

  /**
   * Obtener título según severidad
   */
  getAlertTitle(severity, producto) {
    const titles = {
      critical: `¡SIN STOCK! ${producto.nombre}`,
      warning: `Stock Bajo - ${producto.nombre}`,
      info: `Revisar Stock - ${producto.nombre}`
    };
    return titles[severity] || `Producto: ${producto.nombre}`;
  }

  /**
   * Obtener mensaje de la alerta
   */
  getAlertMessage(producto) {
    const stock = producto.stock;
    const minimo = producto.stock_minimo;
    const diferencia = minimo - stock;

    if (stock <= 0) {
      return `Sin unidades disponibles. Necesitas ${minimo} unidades.`;
    } else if (stock < minimo) {
      return `Solo quedan ${stock} unidades. Faltan ${diferencia} para el mínimo (${minimo}).`;
    } else {
      return `Stock actual: ${stock} unidades (Mínimo: ${minimo})`;
    }
  }

  /**
   * Mostrar alerta con animación
   */
  showAlert(alertElement) {
    this.container.appendChild(alertElement);
    
    // Trigger reflow para la animación
    alertElement.offsetHeight;
    
    requestAnimationFrame(() => {
      alertElement.classList.add('show');
    });

    // Auto dismiss después del tiempo configurado
    setTimeout(() => {
      this.dismissAlert(`stock-${alertElement.dataset.productCode}`);
    }, this.settings.alertDuration);

    // Reproducir sonido si está habilitado
    if (this.settings.sound) {
      this.playAlertSound(alertElement.dataset.severity);
    }
  }

  /**
   * Descartar una alerta específica
   */
  dismissAlert(alertId) {
    const alert = this.alerts.get(alertId);
    if (!alert) return;

    alert.classList.add('hide');
    
    setTimeout(() => {
      if (alert.parentNode) {
        alert.parentNode.removeChild(alert);
      }
      this.alerts.delete(alertId);
      this.updateCounter(this.alerts.size);
    }, 500);
  }

  /**
   * Alternar visibilidad de todas las alertas
   */
  toggleAllAlerts() {
    const allAlerts = this.container.querySelectorAll('.stock-alert');
    const isVisible = allAlerts.length > 0 && !allAlerts[0].classList.contains('hide');
    
    if (isVisible) {
      this.hideAllAlerts();
    } else {
      this.showAllAlerts();
    }
  }

  /**
   * Ocultar todas las alertas
   */
  hideAllAlerts() {
    this.alerts.forEach((alert, alertId) => {
      this.dismissAlert(alertId);
    });
  }

  /**
   * Mostrar todas las alertas
   */
  showAllAlerts() {
    // Re-check stock to show current alerts
    this.checkLowStock();
  }

  /**
   * Actualizar contador de alertas
   */
  updateCounter(count) {
    if (!this.counter) return;
    
    this.counter.textContent = count;
    
    if (count > 0) {
      this.counter.classList.remove('hidden');
    } else {
      this.counter.classList.add('hidden');
    }
  }

  /**
   * Navegar al inventario para reabastecer producto
   */
  goToInventory(productCode) {
    // Si estamos en la página de inventario, enfocar el producto
    if (window.location.pathname.includes('/inventario/')) {
      const codeInput = document.getElementById('stock-codigo');
      if (codeInput) {
        codeInput.value = productCode;
        codeInput.dispatchEvent(new Event('input'));
        codeInput.scrollIntoView({ behavior: 'smooth' });
        codeInput.focus();
      }
    } else {
      // Navegar a inventario con el código
      window.location.href = `/inventario/?code=${productCode}`;
    }
    
    // Dismiss the alert
    this.dismissAlert(`stock-${productCode}`);
  }

  /**
   * Reproducir sonido de alerta
   */
  playAlertSound(severity) {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      let frequency = 800;
      let duration = 0.3;
      
      if (severity === 'critical') {
        frequency = 1000;
        duration = 0.5;
      } else if (severity === 'warning') {
        frequency = 600;
        duration = 0.2;
      }
      
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = frequency;
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      
      oscillator.start();
      oscillator.stop(audioContext.currentTime + duration);
      
    } catch (error) {
      console.log('No se pudo reproducir sonido de alerta:', error);
    }
  }

  /**
   * Configurar settings del sistema
   */
  configure(newSettings) {
    this.settings = { ...this.settings, ...newSettings };
    
    if (newSettings.enabled === false) {
      this.stopPeriodicCheck();
      this.hideAllAlerts();
    } else if (newSettings.enabled === true && !this.checkInterval) {
      this.startPeriodicCheck();
    }
  }

  /**
   * Obtener estadísticas del sistema
   */
  getStats() {
    return {
      activeAlerts: this.alerts.size,
      isEnabled: this.settings.enabled,
      checkInterval: this.settings.checkInterval,
      lastCheck: this.lastCheckTime || null
    };
  }

  /**
   * Limpiar y destruir el sistema
   */
  destroy() {
    this.stopPeriodicCheck();
    this.hideAllAlerts();
    
    if (this.container) {
      this.container.remove();
    }
    if (this.counter) {
      this.counter.remove();
    }
    
    this.isInitialized = false;
  }

  /**
   * Método estático para crear una instancia global
   */
  static createGlobal(options = {}) {
    if (window.stockAlerts) {
      console.warn('StockAlertSystem ya existe globalmente');
      return window.stockAlerts;
    }
    
    window.stockAlerts = new StockAlertSystem();
    window.stockAlerts.init(options);
    
    return window.stockAlerts;
  }

  /**
   * Método estático para trigger manual
   */
  static triggerCheck() {
    if (window.stockAlerts) {
      window.stockAlerts.checkLowStock();
      console.log('🔄 Verificación manual de stock ejecutada');
    }
  }
}

// Auto-inicialización DESHABILITADA - solo manual
// No inicializar automáticamente las alertas

// Exportar para uso modular
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StockAlertSystem;
}