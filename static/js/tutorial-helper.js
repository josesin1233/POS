/**
 * TutorialHelper - Sistema de tutoriales interactivos
 * Botón flotante con tutoriales paso a paso para guiar a los usuarios
 * Incluye: sistema de pestañas, tutoriales cross-page, auto-inicio
 */

class TutorialHelper {
  constructor() {
    this.isMinimized = false;
    this.isActive = false;
    this.currentTutorial = null;
    this.currentStep = 0;
    this.buttonElement = null;
    this.overlayElement = null;
    this.instructionModal = null;

    // Posición del botón (se guarda en localStorage)
    this.position = this.loadPosition() || { x: 20, y: 20 };

    // Mapeo de páginas a URLs y labels
    this.pageConfig = {
      'pos': { label: 'Punto de Venta', url: '/punto_de_venta/', icon: '🛒' },
      'inventario': { label: 'Inventario', url: '/inventario/', icon: '📦' },
      'caja': { label: 'Caja', url: '/caja/', icon: '💰' },
      'registro': { label: 'Registro', url: '/registro/', icon: '📋' }
    };

    // Tutoriales definidos por página
    this.tutorials = {
      'pos': [
        {
          id: 'realizar-venta',
          title: '¿Cómo realizar una venta?',
          description: 'Aprende el flujo completo: buscar producto, agregar al carrito y cobrar',
          page: 'pos',
          steps: [
            {
              target: '#nombre',
              message: 'Busca el producto escribiendo su nombre aquí. Aparecerán sugerencias conforme escribas.',
              position: 'bottom'
            },
            {
              target: '#codigo',
              message: 'También puedes buscar por código de barras. Escríbelo o usa el botón SCAN para escanear con la cámara.',
              position: 'bottom'
            },
            {
              target: '#cantidad',
              message: 'Ajusta la cantidad que el cliente quiere comprar.',
              position: 'bottom'
            },
            {
              target: '#formulario-producto button[type="submit"]',
              message: 'Haz clic en "Agregar al Carrito" para añadir el producto. También puedes presionar Enter en el campo de código.',
              position: 'top'
            },
            {
              target: '#total',
              message: 'Aquí se muestra el total acumulado de todos los productos en el carrito.',
              position: 'top'
            },
            {
              target: '#tabla-productos',
              message: 'En esta tabla verás los productos agregados. Puedes ajustar cantidades con los botones + y -, o eliminar productos.',
              position: 'top',
              fallback: '#carrito-vacio'
            },
            {
              target: 'button[onclick="cobrar()"]',
              message: 'Cuando el cliente esté listo para pagar, presiona "Cobrar". Se abrirá un modal para elegir el método de pago: Efectivo, Transferencia o Tarjeta.',
              position: 'top',
              isLast: true
            }
          ]
        },
        {
          id: 'buscar-productos',
          title: '¿Cómo buscar productos?',
          description: 'Diferentes formas de encontrar productos rápidamente',
          page: 'pos',
          steps: [
            {
              target: '#nombre',
              message: 'Escribe al menos 2 letras del nombre del producto. Aparecerá un menú desplegable con sugerencias que coincidan.',
              position: 'bottom'
            },
            {
              target: '#search-suggestions',
              message: 'Las sugerencias aparecerán aquí mostrando nombre, código, stock y precio. Haz clic en una para seleccionarla.',
              position: 'bottom',
              fallback: '#nombre'
            },
            {
              target: '#codigo',
              message: 'Si conoces el código exacto, escríbelo aquí. El producto se autocompletará automáticamente.',
              position: 'bottom'
            },
            {
              target: '#precio',
              message: 'Una vez encontrado el producto, el precio se muestra aquí automáticamente (solo lectura).',
              position: 'bottom'
            },
            {
              target: '#stock',
              message: 'El stock disponible se muestra aquí para que sepas cuántas unidades hay antes de vender.',
              position: 'bottom',
              isLast: true
            }
          ]
        }
      ],
      'inventario': [
        {
          id: 'agregar-producto',
          title: '¿Cómo agregar productos?',
          description: 'Aprende a agregar nuevos productos paso a paso',
          page: 'inventario',
          steps: [
            {
              target: '#nuevo-codigo',
              message: 'Primero, ingresa el código del producto. Puedes escribirlo manualmente, usar el botón SCAN para escanearlo, o AUTO para asignar uno automático.',
              position: 'bottom'
            },
            {
              target: '#nuevo-nombre',
              message: 'Ahora, escribe el nombre del producto. Sé descriptivo para identificarlo fácilmente.',
              position: 'bottom'
            },
            {
              target: '#nuevo-precio',
              message: 'Ingresa el precio del producto. Usa punto decimal para centavos (ejemplo: 15.50)',
              position: 'bottom'
            },
            {
              target: '#nuevo-stock',
              message: 'Define el stock inicial. Esta es la cantidad de unidades que tienes disponibles.',
              position: 'bottom'
            },
            {
              target: '#nuevo-stock-minimo',
              message: 'Opcional: Establece el stock mínimo. Recibirás alertas cuando el stock baje de este número.',
              position: 'bottom'
            },
            {
              target: '#form-agregar-producto button[type="submit"]',
              message: '¡Perfecto! Ahora haz clic en "Agregar Producto" para guardar el producto en tu inventario.',
              position: 'top',
              isLast: true
            }
          ]
        },
        {
          id: 'actualizar-stock',
          title: '¿Cómo actualizar stock?',
          description: 'Aprende a modificar el stock y precio de productos existentes',
          page: 'inventario',
          steps: [
            {
              target: '#stock-codigo',
              message: 'Ingresa el código del producto que deseas actualizar. Puedes escribirlo o usar SCAN para escanearlo.',
              position: 'bottom'
            },
            {
              target: '#producto-info',
              message: 'Aquí se mostrará la información del producto encontrado: nombre, stock actual y precio.',
              position: 'bottom'
            },
            {
              target: '#stock-agregar',
              message: 'Escribe la cantidad a agregar o restar del stock. Usa números negativos para restar (ejemplo: -5 para quitar 5 unidades).',
              position: 'bottom'
            },
            {
              target: '#nuevo-precio-update',
              message: 'Opcional: Si necesitas cambiar el precio, escribe el nuevo precio aquí. Déjalo vacío para mantener el precio actual.',
              position: 'bottom'
            },
            {
              target: '#stock-minimo-update',
              message: 'Opcional: Actualiza el stock mínimo para las alertas de poco stock.',
              position: 'bottom'
            },
            {
              target: '#form-actualizar-producto button[type="submit"]',
              message: 'Haz clic en "Actualizar" para guardar los cambios.',
              position: 'top',
              isLast: true
            }
          ]
        },
        {
          id: 'buscar-editar-productos',
          title: '¿Cómo buscar y editar productos?',
          description: 'Busca productos en tu inventario y edítalos directamente',
          page: 'inventario',
          steps: [
            {
              target: '#buscar-inventario',
              message: 'Usa este campo para buscar productos por nombre o código. La tabla se filtra en tiempo real conforme escribes.',
              position: 'bottom'
            },
            {
              target: '#productos-table',
              message: 'Aquí se muestra toda tu lista de productos con código, nombre, precio, stock y stock mínimo.',
              position: 'top'
            },
            {
              target: '#productos-poco-stock',
              message: 'En esta sección aparecen los productos con poco stock. Puedes hacer clic en "Reabastecer" para ir directamente al formulario de actualización.',
              position: 'top',
              fallback: '#poco-stock-container',
              isLast: true
            }
          ]
        }
      ],
      'caja': [
        {
          id: 'abrir-caja',
          title: '¿Cómo abrir la caja?',
          description: 'Aprende a iniciar tu turno abriendo la caja con el monto inicial',
          page: 'caja',
          steps: [
            {
              target: '#estado-caja',
              message: 'Aquí puedes ver el estado actual de la caja: "Abierta" o "Cerrada". Haz clic para navegar a la sección correspondiente.',
              position: 'bottom'
            },
            {
              target: '#monto-inicial-billetes',
              message: 'Ingresa la cantidad de billetes con la que inicias el día. Esto es tu fondo de caja.',
              position: 'bottom'
            },
            {
              target: '#monto-inicial-monedas',
              message: 'Ingresa la cantidad de monedas. El total se calculará automáticamente.',
              position: 'bottom'
            },
            {
              target: '#monto-inicial-total',
              message: 'Aquí se muestra el total calculado (billetes + monedas). Este campo es de solo lectura.',
              position: 'bottom'
            },
            {
              target: '#form-apertura button[type="submit"]',
              message: 'Haz clic en "Abrir Caja" para comenzar tu turno. La caja quedará abierta hasta que la cierres.',
              position: 'top',
              isLast: true
            }
          ]
        },
        {
          id: 'registrar-gastos',
          title: '¿Cómo registrar gastos?',
          description: 'Registra gastos, compras y retiros durante el día',
          page: 'caja',
          steps: [
            {
              target: '#btn-nuevo-gasto',
              message: 'Haz clic en "+ Nuevo Gasto" para abrir el formulario de registro de gastos.',
              position: 'bottom'
            },
            {
              target: '#form-gasto-container',
              message: 'Aquí aparecerá el formulario con los campos: Concepto (descripción del gasto), Monto, y Tipo (Compra, Gasto Operativo, Retiro u Otro).',
              position: 'top',
              fallback: '#btn-nuevo-gasto'
            },
            {
              target: '#tabla-gastos',
              message: 'Los gastos registrados aparecen en esta tabla con la hora, concepto, tipo y monto de cada uno.',
              position: 'top'
            },
            {
              target: '#total-gastos',
              message: 'Aquí se muestra el total acumulado de gastos del día. Este monto se descuenta del efectivo esperado al cerrar la caja.',
              position: 'top',
              isLast: true
            }
          ]
        },
        {
          id: 'cerrar-caja',
          title: '¿Cómo cerrar la caja?',
          description: 'Cierra tu turno contando el efectivo y cuadrando la caja',
          page: 'caja',
          steps: [
            {
              target: '#efectivo-esperado',
              message: 'Este es el efectivo que debería haber en caja: monto inicial + ventas en efectivo - gastos.',
              position: 'bottom'
            },
            {
              target: '#efectivo-real',
              message: 'Cuenta el dinero en tu caja y escribe la cantidad real aquí. La diferencia se calculará automáticamente.',
              position: 'bottom'
            },
            {
              target: '#diferencia',
              message: 'Aquí se muestra la diferencia. Verde si hay sobrante, rojo si falta dinero.',
              position: 'bottom'
            },
            {
              target: '#form-cierre button[type="submit"]',
              message: 'Haz clic en "Cerrar Caja" para finalizar tu turno. Se guardará el registro del cierre con todos los detalles.',
              position: 'top',
              isLast: true
            }
          ]
        }
      ],
      'registro': [
        {
          id: 'ver-historial',
          title: '¿Cómo ver el historial de ventas?',
          description: 'Explora el registro completo de ventas y movimientos',
          page: 'registro',
          steps: [
            {
              target: '#total-dia',
              message: 'Aquí se muestra el total de ventas del día actual. Se actualiza automáticamente.',
              position: 'bottom'
            },
            {
              target: '#tabla-ventas',
              message: 'Esta es la tabla principal de actividades. Muestra ventas y movimientos de inventario organizados jerárquicamente por año, mes, semana y día.',
              position: 'top'
            },
            {
              target: '#tabla-ventas-body',
              message: 'Haz clic en cualquier fila de grupo (año, mes, semana, día) para expandir o contraer su contenido. Las ventas de hoy se muestran expandidas por defecto.',
              position: 'top'
            },
            {
              target: '#tabla-ventas-body',
              message: 'Al expandir una venta individual, verás los productos vendidos, cantidades, precios y el cambio de stock que generó cada venta.',
              position: 'top',
              isLast: true
            }
          ]
        },
        {
          id: 'filtrar-ventas',
          title: '¿Cómo filtrar por fecha?',
          description: 'Filtra ventas por día, mes o año específico',
          page: 'registro',
          steps: [
            {
              target: '#filtro-dia',
              message: 'Selecciona un día específico para ver solo las ventas de esa fecha.',
              position: 'bottom'
            },
            {
              target: '#filtro-mes',
              message: 'O selecciona un mes completo para ver todas las ventas de ese período.',
              position: 'bottom'
            },
            {
              target: '#filtro-anio',
              message: 'También puedes filtrar por año. Escribe el año (ejemplo: 2025).',
              position: 'bottom'
            },
            {
              target: '#filtro-form button[type="submit"]',
              message: 'Haz clic en "Filtrar" para aplicar los filtros seleccionados.',
              position: 'right',
              fallback: '#filtro-form'
            },
            {
              target: '#filtro-form',
              message: 'Usa el botón "Limpiar" para quitar todos los filtros y ver el historial completo nuevamente.',
              position: 'bottom',
              isLast: true
            }
          ]
        }
      ]
    };

    this.init();
  }

  init() {
    this.createFloatingButton();
    this.setupDragAndDrop();
    this.restorePosition();
    this.checkPendingTutorial();
  }

  // Verificar si hay un tutorial pendiente por auto-iniciar (cross-page)
  checkPendingTutorial() {
    const pending = localStorage.getItem('tutorial-pending');
    if (!pending) return;

    try {
      const { tutorialId, page } = JSON.parse(pending);
      const currentPage = this.getCurrentPage();

      if (currentPage === page) {
        localStorage.removeItem('tutorial-pending');
        // Esperar a que la página cargue completamente
        setTimeout(() => {
          const tutorials = this.tutorials[page] || [];
          const tutorial = tutorials.find(t => t.id === tutorialId);
          if (tutorial && tutorial.steps.length > 0) {
            this.startTutorial(tutorial);
          }
        }, 800);
      }
    } catch (e) {
      localStorage.removeItem('tutorial-pending');
    }
  }

  // Cargar posición desde localStorage
  loadPosition() {
    const saved = localStorage.getItem('tutorial-helper-position');
    return saved ? JSON.parse(saved) : null;
  }

  // Guardar posición en localStorage
  savePosition() {
    localStorage.setItem('tutorial-helper-position', JSON.stringify(this.position));
  }

  // Crear botón flotante
  createFloatingButton() {
    const button = document.createElement('div');
    button.id = 'tutorial-helper-button';
    button.className = 'tutorial-helper-button';
    button.innerHTML = `
      <div class="tutorial-helper-content">
        <svg class="tutorial-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <span class="tutorial-text">Tutoriales</span>
      </div>
    `;

    button.addEventListener('click', (e) => {
      if (!this.isDragging) {
        this.toggleMinimize();
      }
    });

    document.body.appendChild(button);
    this.buttonElement = button;

    // Agregar estilos
    this.injectStyles();
  }

  // Inyectar estilos CSS
  injectStyles() {
    if (document.getElementById('tutorial-helper-styles')) return;

    const styles = document.createElement('style');
    styles.id = 'tutorial-helper-styles';
    styles.textContent = `
      .tutorial-helper-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 12px 20px;
        cursor: move;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        z-index: 9998;
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 600;
        transition: all 0.3s ease;
        user-select: none;
      }

      .tutorial-helper-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
      }

      .tutorial-helper-button.minimized {
        padding: 12px;
        border-radius: 50%;
      }

      .tutorial-helper-button.minimized .tutorial-text {
        display: none;
      }

      .tutorial-helper-button.dragging {
        cursor: grabbing;
        opacity: 0.8;
      }

      .tutorial-icon {
        flex-shrink: 0;
      }

      .tutorial-text {
        white-space: nowrap;
      }

      /* Modal de selección de tutoriales */
      .tutorial-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.75);
        backdrop-filter: blur(4px);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.2s ease;
      }

      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }

      .tutorial-modal {
        background: white;
        border-radius: 16px;
        max-width: 560px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        animation: slideUp 0.3s ease;
      }

      @keyframes slideUp {
        from {
          opacity: 0;
          transform: translateY(20px) scale(0.95);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      .tutorial-modal-header {
        padding: 24px;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .tutorial-modal-title {
        font-size: 20px;
        font-weight: 700;
        color: #111827;
        margin: 0;
      }

      .tutorial-modal-close {
        background: none;
        border: none;
        font-size: 24px;
        color: #6b7280;
        cursor: pointer;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        transition: all 0.2s;
      }

      .tutorial-modal-close:hover {
        background: #f3f4f6;
        color: #111827;
      }

      /* Tabs */
      .tutorial-tabs {
        display: flex;
        gap: 4px;
        padding: 16px 24px 0;
        border-bottom: 1px solid #e5e7eb;
        overflow-x: auto;
      }

      .tutorial-tab {
        padding: 10px 16px;
        border: none;
        background: none;
        font-size: 13px;
        font-weight: 500;
        color: #6b7280;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        transition: all 0.2s;
        white-space: nowrap;
        border-radius: 0;
      }

      .tutorial-tab:hover {
        color: #111827;
        background: #f9fafb;
      }

      .tutorial-tab.active {
        color: #6366f1;
        border-bottom-color: #6366f1;
        font-weight: 600;
      }

      .tutorial-tab-current {
        position: relative;
      }

      .tutorial-tab-current::after {
        content: '';
        position: absolute;
        top: 6px;
        right: 6px;
        width: 6px;
        height: 6px;
        background: #6366f1;
        border-radius: 50%;
      }

      .tutorial-modal-body {
        padding: 24px;
      }

      .tutorial-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .tutorial-item {
        padding: 16px;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.2s;
        background: white;
      }

      .tutorial-item:hover {
        border-color: #6366f1;
        background: #f9fafb;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
      }

      .tutorial-item.disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .tutorial-item.disabled:hover {
        border-color: #e5e7eb;
        background: white;
        transform: none;
        box-shadow: none;
      }

      .tutorial-item-title {
        font-size: 16px;
        font-weight: 600;
        color: #111827;
        margin: 0 0 4px 0;
      }

      .tutorial-item-desc {
        font-size: 14px;
        color: #6b7280;
        margin: 0;
      }

      .tutorial-item-badge {
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        margin-left: 8px;
        background: #dbeafe;
        color: #2563eb;
      }

      .tutorial-item-badge.cross-page {
        background: #fef3c7;
        color: #92400e;
      }

      .tutorial-no-items {
        text-align: center;
        padding: 40px 20px;
        color: #6b7280;
      }

      .tutorial-no-items-icon {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }

      .tutorial-no-items-text {
        font-size: 16px;
        font-weight: 600;
        margin: 0 0 8px 0;
      }

      .tutorial-no-items-hint {
        font-size: 14px;
        margin: 0;
        opacity: 0.8;
      }

      /* Overlay para resaltar elementos */
      .tutorial-highlight-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 9997;
        pointer-events: none;
      }

      .tutorial-highlight {
        position: absolute;
        border: 3px solid #6366f1;
        border-radius: 8px;
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2),
                    0 0 20px rgba(99, 102, 241, 0.4);
        z-index: 9998;
        pointer-events: none;
        transition: all 0.3s ease;
      }

      /* Modal de instrucciones */
      .tutorial-instruction-modal {
        position: fixed;
        background: white;
        border-radius: 12px;
        padding: 20px;
        max-width: 400px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        z-index: 9999;
        animation: slideUp 0.3s ease;
      }

      .tutorial-instruction-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
      }

      .tutorial-instruction-title {
        font-size: 14px;
        font-weight: 600;
        color: #6366f1;
        margin: 0;
      }

      .tutorial-instruction-close {
        background: none;
        border: none;
        font-size: 20px;
        color: #6b7280;
        cursor: pointer;
        padding: 0;
        line-height: 1;
      }

      .tutorial-instruction-message {
        font-size: 15px;
        color: #111827;
        line-height: 1.6;
        margin: 0 0 16px 0;
      }

      .tutorial-instruction-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .tutorial-instruction-progress {
        font-size: 12px;
        color: #6b7280;
        font-weight: 500;
      }

      .tutorial-instruction-actions {
        display: flex;
        gap: 8px;
      }

      .tutorial-btn {
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }

      .tutorial-btn-primary {
        background: #6366f1;
        color: white;
      }

      .tutorial-btn-primary:hover {
        background: #4f46e5;
      }

      .tutorial-btn-secondary {
        background: #f3f4f6;
        color: #374151;
      }

      .tutorial-btn-secondary:hover {
        background: #e5e7eb;
      }

      /* Modal de redirección cross-page */
      .tutorial-redirect-modal {
        background: white;
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: scaleIn 0.3s ease;
        max-width: 420px;
        width: 90%;
      }

      .tutorial-redirect-icon {
        font-size: 48px;
        margin-bottom: 16px;
      }

      .tutorial-redirect-title {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        margin: 0 0 8px 0;
      }

      .tutorial-redirect-message {
        font-size: 15px;
        color: #6b7280;
        margin: 0 0 24px 0;
        line-height: 1.5;
      }

      .tutorial-redirect-actions {
        display: flex;
        gap: 12px;
        justify-content: center;
      }

      /* Mensaje de éxito */
      .tutorial-success-modal {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: scaleIn 0.3s ease;
        min-width: 320px;
      }

      @keyframes scaleIn {
        from {
          opacity: 0;
          transform: translate(-50%, -50%) scale(0.8);
        }
        to {
          opacity: 1;
          transform: translate(-50%, -50%) scale(1);
        }
      }

      .tutorial-success-icon {
        font-size: 64px;
        margin-bottom: 16px;
      }

      .tutorial-success-title {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
        margin: 0 0 8px 0;
      }

      .tutorial-success-message {
        font-size: 16px;
        color: #6b7280;
        margin: 0 0 24px 0;
      }
    `;

    document.head.appendChild(styles);
  }

  // Setup drag and drop
  setupDragAndDrop() {
    let isDragging = false;
    let startX, startY;

    this.buttonElement.addEventListener('mousedown', (e) => {
      isDragging = true;
      this.isDragging = false;
      startX = e.clientX;
      startY = e.clientY;
      this.buttonElement.classList.add('dragging');
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;

      if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
        this.isDragging = true;
      }

      if (this.isDragging) {
        this.position.x = window.innerWidth - e.clientX;
        this.position.y = window.innerHeight - e.clientY;

        this.position.x = Math.max(10, Math.min(window.innerWidth - 60, this.position.x));
        this.position.y = Math.max(10, Math.min(window.innerHeight - 60, this.position.y));

        this.updateButtonPosition();
      }
    });

    document.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        this.buttonElement.classList.remove('dragging');

        if (this.isDragging) {
          this.savePosition();
          setTimeout(() => {
            this.isDragging = false;
          }, 100);
        }
      }
    });
  }

  updateButtonPosition() {
    this.buttonElement.style.right = `${this.position.x}px`;
    this.buttonElement.style.bottom = `${this.position.y}px`;
  }

  restorePosition() {
    this.updateButtonPosition();
  }

  toggleMinimize() {
    if (!this.isActive) {
      this.showTutorialModal();
    }
  }

  getCurrentPage() {
    const path = window.location.pathname;

    if (path.includes('/inventario')) return 'inventario';
    if (path.includes('/punto_de_venta') || path === '/') return 'pos';
    if (path.includes('/caja')) return 'caja';
    if (path.includes('/registro')) return 'registro';

    return 'unknown';
  }

  // Mostrar modal con pestañas de todos los tutoriales
  showTutorialModal() {
    const currentPage = this.getCurrentPage();
    const pages = Object.keys(this.tutorials);

    const overlay = document.createElement('div');
    overlay.className = 'tutorial-modal-overlay';

    // Construir tabs HTML
    const tabsHtml = pages.map(page => {
      const config = this.pageConfig[page];
      const isActive = page === currentPage;
      const isCurrent = page === currentPage;
      return `<button class="tutorial-tab ${isActive ? 'active' : ''} ${isCurrent ? 'tutorial-tab-current' : ''}" data-page="${page}">
        ${config.icon} ${config.label}
      </button>`;
    }).join('');

    // Construir contenido para cada tab
    const renderTutorialList = (page) => {
      const tutorials = this.tutorials[page] || [];
      const isCurrentPage = page === currentPage;

      if (tutorials.length === 0) {
        return `
          <div class="tutorial-no-items">
            <div class="tutorial-no-items-icon">📚</div>
            <p class="tutorial-no-items-text">No hay tutoriales disponibles</p>
          </div>
        `;
      }

      return `
        <div class="tutorial-list">
          ${tutorials.map(tutorial => {
            const hasSteps = tutorial.steps.length > 0;
            const badge = !isCurrentPage && hasSteps
              ? `<span class="tutorial-item-badge cross-page">Ir a ${this.pageConfig[page].label}</span>`
              : '';
            return `
              <div class="tutorial-item ${!hasSteps ? 'disabled' : ''}" data-tutorial-id="${tutorial.id}" data-tutorial-page="${page}">
                <h3 class="tutorial-item-title">${tutorial.title}${badge}</h3>
                <p class="tutorial-item-desc">${tutorial.description}</p>
              </div>
            `;
          }).join('')}
        </div>
      `;
    };

    overlay.innerHTML = `
      <div class="tutorial-modal">
        <div class="tutorial-modal-header">
          <h2 class="tutorial-modal-title">Tutoriales Interactivos</h2>
          <button class="tutorial-modal-close">&times;</button>
        </div>
        <div class="tutorial-tabs">${tabsHtml}</div>
        <div class="tutorial-modal-body" id="tutorial-tab-content">
          ${renderTutorialList(currentPage)}
        </div>
      </div>
    `;

    // Event: cerrar modal
    const closeBtn = overlay.querySelector('.tutorial-modal-close');
    closeBtn.addEventListener('click', () => document.body.removeChild(overlay));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) document.body.removeChild(overlay);
    });

    // Event: cambiar tab
    const tabs = overlay.querySelectorAll('.tutorial-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const page = tab.dataset.page;
        const content = overlay.querySelector('#tutorial-tab-content');
        content.innerHTML = renderTutorialList(page);
        this._bindTutorialItems(overlay, currentPage);
      });
    });

    // Bind tutorial item clicks
    this._bindTutorialItems(overlay, currentPage);

    document.body.appendChild(overlay);
  }

  // Bind click events a los items de tutorial
  _bindTutorialItems(overlay, currentPage) {
    const items = overlay.querySelectorAll('.tutorial-item:not(.disabled)');
    items.forEach(item => {
      item.addEventListener('click', () => {
        const tutorialId = item.dataset.tutorialId;
        const tutorialPage = item.dataset.tutorialPage;
        const tutorials = this.tutorials[tutorialPage] || [];
        const tutorial = tutorials.find(t => t.id === tutorialId);

        if (!tutorial) return;

        if (tutorialPage !== currentPage) {
          // Cross-page: mostrar modal de redirección
          document.body.removeChild(overlay);
          this.showRedirectModal(tutorial, tutorialPage);
        } else {
          // Misma página: iniciar directamente
          document.body.removeChild(overlay);
          this.startTutorial(tutorial);
        }
      });
    });
  }

  // Mostrar modal de redirección para tutoriales cross-page
  showRedirectModal(tutorial, targetPage) {
    const config = this.pageConfig[targetPage];

    const overlay = document.createElement('div');
    overlay.className = 'tutorial-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'tutorial-redirect-modal';
    modal.innerHTML = `
      <div class="tutorial-redirect-icon">${config.icon}</div>
      <h2 class="tutorial-redirect-title">Ir a ${config.label}</h2>
      <p class="tutorial-redirect-message">
        Para seguir el tutorial <strong>"${tutorial.title}"</strong> necesitas estar en la página de <strong>${config.label}</strong>.
        <br><br>
        Al hacer clic en "Ir", se abrirá la página y el tutorial iniciará automáticamente.
      </p>
      <div class="tutorial-redirect-actions">
        <button class="tutorial-btn tutorial-btn-secondary tutorial-redirect-cancel">Cancelar</button>
        <button class="tutorial-btn tutorial-btn-primary tutorial-redirect-go">Ir a ${config.label}</button>
      </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Events
    const cancelBtn = modal.querySelector('.tutorial-redirect-cancel');
    const goBtn = modal.querySelector('.tutorial-redirect-go');

    cancelBtn.addEventListener('click', () => document.body.removeChild(overlay));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) document.body.removeChild(overlay);
    });

    goBtn.addEventListener('click', () => {
      // Guardar tutorial pendiente en localStorage
      localStorage.setItem('tutorial-pending', JSON.stringify({
        tutorialId: tutorial.id,
        page: targetPage
      }));
      // Redirigir
      window.location.href = config.url;
    });
  }

  // Iniciar tutorial
  startTutorial(tutorial) {
    this.isActive = true;
    this.currentTutorial = tutorial;
    this.currentStep = 0;

    this.createOverlay();
    this.showStep();
  }

  createOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'tutorial-highlight-overlay';
    document.body.appendChild(overlay);
    this.overlayElement = overlay;
  }

  showStep() {
    const step = this.currentTutorial.steps[this.currentStep];
    if (!step) return;

    // Encontrar elemento target (con fallback)
    let targetElement = document.querySelector(step.target);
    if (!targetElement && step.fallback) {
      targetElement = document.querySelector(step.fallback);
    }
    if (!targetElement) {
      // Saltar al siguiente paso si el elemento no existe
      console.warn('Tutorial: elemento no encontrado:', step.target);
      if (this.currentStep < this.currentTutorial.steps.length - 1) {
        this.currentStep++;
        this.showStep();
      } else {
        this.completeTutorial();
      }
      return;
    }

    targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

    setTimeout(() => {
      this.highlightElement(targetElement);
      this.showInstructionModal(step, targetElement);
    }, 300);
  }

  highlightElement(element) {
    const oldHighlight = document.querySelector('.tutorial-highlight');
    if (oldHighlight) {
      oldHighlight.remove();
    }

    const rect = element.getBoundingClientRect();
    const highlight = document.createElement('div');
    highlight.className = 'tutorial-highlight';
    highlight.style.top = `${rect.top - 4}px`;
    highlight.style.left = `${rect.left - 4}px`;
    highlight.style.width = `${rect.width + 8}px`;
    highlight.style.height = `${rect.height + 8}px`;

    document.body.appendChild(highlight);

    const updatePosition = () => {
      const newRect = element.getBoundingClientRect();
      highlight.style.top = `${newRect.top - 4}px`;
      highlight.style.left = `${newRect.left - 4}px`;
    };

    window.addEventListener('scroll', updatePosition);
    window.addEventListener('resize', updatePosition);

    this.currentHighlight = { element: highlight, updatePosition };
  }

  showInstructionModal(step, targetElement) {
    if (this.instructionModal) {
      this.instructionModal.remove();
    }

    const modal = document.createElement('div');
    modal.className = 'tutorial-instruction-modal';

    const totalSteps = this.currentTutorial.steps.length;
    const currentStepNum = this.currentStep + 1;

    modal.innerHTML = `
      <div class="tutorial-instruction-header">
        <span class="tutorial-instruction-title">Paso ${currentStepNum} de ${totalSteps}</span>
        <button class="tutorial-instruction-close">&times;</button>
      </div>
      <div class="tutorial-instruction-message">${step.message}</div>
      <div class="tutorial-instruction-footer">
        <div class="tutorial-instruction-progress">${currentStepNum}/${totalSteps}</div>
        <div class="tutorial-instruction-actions">
          <button class="tutorial-btn tutorial-btn-secondary tutorial-cancel">Cancelar</button>
          <button class="tutorial-btn tutorial-btn-primary tutorial-next">
            ${step.isLast ? 'Finalizar' : 'Siguiente'}
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    this.positionInstructionModal(modal, targetElement, step.position);

    const closeBtn = modal.querySelector('.tutorial-instruction-close');
    const cancelBtn = modal.querySelector('.tutorial-cancel');
    const nextBtn = modal.querySelector('.tutorial-next');

    closeBtn.addEventListener('click', () => this.endTutorial());
    cancelBtn.addEventListener('click', () => this.endTutorial());
    nextBtn.addEventListener('click', () => this.nextStep());

    this.instructionModal = modal;
  }

  positionInstructionModal(modal, targetElement, position) {
    const rect = targetElement.getBoundingClientRect();
    const modalRect = modal.getBoundingClientRect();

    let top, left;

    switch (position) {
      case 'top':
        top = rect.top - modalRect.height - 20;
        left = rect.left + (rect.width / 2) - (modalRect.width / 2);
        break;
      case 'bottom':
        top = rect.bottom + 20;
        left = rect.left + (rect.width / 2) - (modalRect.width / 2);
        break;
      case 'left':
        top = rect.top + (rect.height / 2) - (modalRect.height / 2);
        left = rect.left - modalRect.width - 20;
        break;
      case 'right':
        top = rect.top + (rect.height / 2) - (modalRect.height / 2);
        left = rect.right + 20;
        break;
      default:
        top = rect.bottom + 20;
        left = rect.left + (rect.width / 2) - (modalRect.width / 2);
    }

    top = Math.max(20, Math.min(window.innerHeight - modalRect.height - 20, top));
    left = Math.max(20, Math.min(window.innerWidth - modalRect.width - 20, left));

    modal.style.top = `${top}px`;
    modal.style.left = `${left}px`;
  }

  nextStep() {
    const step = this.currentTutorial.steps[this.currentStep];

    if (step.isLast) {
      this.completeTutorial();
      return;
    }

    this.currentStep++;

    if (this.currentStep < this.currentTutorial.steps.length) {
      this.showStep();
    } else {
      this.completeTutorial();
    }
  }

  completeTutorial() {
    this.cleanup();
    this.showSuccessMessage();

    this.isActive = false;
    this.currentTutorial = null;
    this.currentStep = 0;
  }

  endTutorial() {
    this.cleanup();
    this.isActive = false;
    this.currentTutorial = null;
    this.currentStep = 0;
  }

  cleanup() {
    if (this.overlayElement) {
      this.overlayElement.remove();
      this.overlayElement = null;
    }

    if (this.instructionModal) {
      this.instructionModal.remove();
      this.instructionModal = null;
    }

    const highlight = document.querySelector('.tutorial-highlight');
    if (highlight) {
      highlight.remove();
    }

    if (this.currentHighlight) {
      window.removeEventListener('scroll', this.currentHighlight.updatePosition);
      window.removeEventListener('resize', this.currentHighlight.updatePosition);
      this.currentHighlight = null;
    }
  }

  showSuccessMessage() {
    const overlay = document.createElement('div');
    overlay.className = 'tutorial-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'tutorial-success-modal';
    modal.innerHTML = `
      <div class="tutorial-success-icon">🎉</div>
      <h2 class="tutorial-success-title">¡Tutorial completado!</h2>
      <p class="tutorial-success-message">Has completado el tutorial exitosamente.</p>
      <button class="tutorial-btn tutorial-btn-primary">Entendido</button>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    const btn = modal.querySelector('.tutorial-btn');
    btn.addEventListener('click', () => {
      document.body.removeChild(overlay);
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    });
  }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.tutorialHelper = new TutorialHelper();
  });
} else {
  window.tutorialHelper = new TutorialHelper();
}
