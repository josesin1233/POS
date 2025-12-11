/**
 * TutorialHelper - Sistema de tutoriales interactivos
 * Botón flotante con tutoriales paso a paso para guiar a los usuarios
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
    this.position = this.loadPosition() || { x: 20, y: 20 }; // 20px desde esquina inferior derecha

    // Tutoriales definidos por página
    this.tutorials = {
      'inventario': [
        {
          id: 'agregar-producto',
          title: '¿Cómo agregar productos a inventario?',
          description: 'Aprende a agregar nuevos productos paso a paso',
          steps: [
            {
              target: '#nuevo-codigo',
              message: 'Primero, ingresa el código del producto. Puedes escribirlo manualmente, usar el botón SCAN para escanearlo, o AUTO para asignar uno automático.',
              position: 'bottom',
              waitForInput: false
            },
            {
              target: '#nuevo-nombre',
              message: 'Ahora, escribe el nombre del producto. Sé descriptivo para identificarlo fácilmente.',
              position: 'bottom',
              waitForInput: false
            },
            {
              target: '#nuevo-precio',
              message: 'Ingresa el precio del producto. Usa punto decimal para centavos (ejemplo: 15.50)',
              position: 'bottom',
              waitForInput: false
            },
            {
              target: '#nuevo-stock',
              message: 'Define el stock inicial. Esta es la cantidad de unidades que tienes disponibles.',
              position: 'bottom',
              waitForInput: false
            },
            {
              target: '#nuevo-stock-minimo',
              message: 'Opcional: Establece el stock mínimo. Recibirás alertas cuando el stock baje de este número.',
              position: 'bottom',
              waitForInput: false
            },
            {
              target: 'button[type="submit"]',
              message: '¡Perfecto! Ahora haz clic en "Agregar Producto" para guardar el producto en tu inventario.',
              position: 'top',
              waitForInput: false,
              isLast: true
            }
          ]
        }
      ],
      'pos': [
        {
          id: 'realizar-venta',
          title: '¿Cómo realizar una venta?',
          description: 'Tutorial próximamente...',
          steps: []
        }
      ],
      'caja': [
        {
          id: 'control-caja',
          title: '¿Cómo usar el control de caja?',
          description: 'Tutorial próximamente...',
          steps: []
        }
      ],
      'registro': [
        {
          id: 'ver-ventas',
          title: '¿Cómo ver el registro de ventas?',
          description: 'Tutorial próximamente...',
          steps: []
        }
      ]
    };

    this.init();
  }

  init() {
    this.createFloatingButton();
    this.setupDragAndDrop();
    this.restorePosition();
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
        max-width: 500px;
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
    let initialX, initialY;

    this.buttonElement.addEventListener('mousedown', (e) => {
      isDragging = true;
      this.isDragging = false;
      startX = e.clientX;
      startY = e.clientY;

      const rect = this.buttonElement.getBoundingClientRect();
      initialX = rect.right;
      initialY = rect.bottom;

      this.buttonElement.classList.add('dragging');
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;

      // Si se movió más de 5px, consideramos que está arrastrando
      if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
        this.isDragging = true;
      }

      if (this.isDragging) {
        // Calcular nueva posición desde esquina inferior derecha
        this.position.x = window.innerWidth - e.clientX;
        this.position.y = window.innerHeight - e.clientY;

        // Limitar a los bordes de la ventana
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
          // Pequeño delay para no activar el click después del drag
          setTimeout(() => {
            this.isDragging = false;
          }, 100);
        }
      }
    });
  }

  // Actualizar posición del botón
  updateButtonPosition() {
    this.buttonElement.style.right = `${this.position.x}px`;
    this.buttonElement.style.bottom = `${this.position.y}px`;
  }

  // Restaurar posición guardada
  restorePosition() {
    this.updateButtonPosition();
  }

  // Minimizar/expandir botón
  toggleMinimize() {
    if (!this.isActive) {
      // Si no hay tutorial activo, mostrar modal de selección
      this.showTutorialModal();
    }
  }

  // Detectar página actual
  getCurrentPage() {
    const path = window.location.pathname;

    if (path.includes('/inventario')) return 'inventario';
    if (path.includes('/punto_de_venta') || path === '/') return 'pos';
    if (path.includes('/caja')) return 'caja';
    if (path.includes('/registro')) return 'registro';

    return 'unknown';
  }

  // Obtener tutoriales de la página actual
  getPageTutorials() {
    const page = this.getCurrentPage();
    return this.tutorials[page] || [];
  }

  // Mostrar modal de selección de tutoriales
  showTutorialModal() {
    const tutorials = this.getPageTutorials();

    const overlay = document.createElement('div');
    overlay.className = 'tutorial-modal-overlay';
    overlay.innerHTML = `
      <div class="tutorial-modal">
        <div class="tutorial-modal-header">
          <h2 class="tutorial-modal-title">Tutoriales Interactivos</h2>
          <button class="tutorial-modal-close">&times;</button>
        </div>
        <div class="tutorial-modal-body">
          ${tutorials.length > 0 ? `
            <div class="tutorial-list">
              ${tutorials.map(tutorial => `
                <div class="tutorial-item ${tutorial.steps.length === 0 ? 'disabled' : ''}" data-tutorial-id="${tutorial.id}">
                  <h3 class="tutorial-item-title">${tutorial.title}</h3>
                  <p class="tutorial-item-desc">${tutorial.description}</p>
                </div>
              `).join('')}
            </div>
          ` : `
            <div class="tutorial-no-items">
              <div class="tutorial-no-items-icon">📚</div>
              <p class="tutorial-no-items-text">No hay tutoriales disponibles aquí</p>
              <p class="tutorial-no-items-hint">Navega a otras secciones como Inventario, POS, o Caja para ver tutoriales específicos.</p>
            </div>
          `}
        </div>
      </div>
    `;

    // Event listeners
    const closeBtn = overlay.querySelector('.tutorial-modal-close');
    closeBtn.addEventListener('click', () => {
      document.body.removeChild(overlay);
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    });

    // Tutorial item clicks
    const items = overlay.querySelectorAll('.tutorial-item:not(.disabled)');
    items.forEach(item => {
      item.addEventListener('click', () => {
        const tutorialId = item.dataset.tutorialId;
        const tutorial = tutorials.find(t => t.id === tutorialId);
        if (tutorial) {
          document.body.removeChild(overlay);
          this.startTutorial(tutorial);
        }
      });
    });

    document.body.appendChild(overlay);
  }

  // Iniciar tutorial
  startTutorial(tutorial) {
    this.isActive = true;
    this.currentTutorial = tutorial;
    this.currentStep = 0;

    // Crear overlay
    this.createOverlay();

    // Mostrar primer paso
    this.showStep();
  }

  // Crear overlay de highlight
  createOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'tutorial-highlight-overlay';
    document.body.appendChild(overlay);
    this.overlayElement = overlay;
  }

  // Mostrar paso actual
  showStep() {
    const step = this.currentTutorial.steps[this.currentStep];
    if (!step) return;

    // Encontrar elemento target
    const targetElement = document.querySelector(step.target);
    if (!targetElement) {
      console.error('Tutorial: elemento no encontrado:', step.target);
      this.endTutorial();
      return;
    }

    // Scroll al elemento
    targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Esperar un poco para que el scroll termine
    setTimeout(() => {
      // Crear highlight
      this.highlightElement(targetElement);

      // Mostrar modal de instrucciones
      this.showInstructionModal(step, targetElement);
    }, 300);
  }

  // Resaltar elemento
  highlightElement(element) {
    // Remover highlight anterior si existe
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

    // Actualizar posición si el usuario hace scroll
    const updatePosition = () => {
      const newRect = element.getBoundingClientRect();
      highlight.style.top = `${newRect.top - 4}px`;
      highlight.style.left = `${newRect.left - 4}px`;
    };

    window.addEventListener('scroll', updatePosition);
    window.addEventListener('resize', updatePosition);

    // Guardar para limpiar después
    this.currentHighlight = { element: highlight, updatePosition };
  }

  // Mostrar modal de instrucciones
  showInstructionModal(step, targetElement) {
    // Remover modal anterior si existe
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

    // Posicionar modal cerca del elemento
    document.body.appendChild(modal);
    this.positionInstructionModal(modal, targetElement, step.position);

    // Event listeners
    const closeBtn = modal.querySelector('.tutorial-instruction-close');
    const cancelBtn = modal.querySelector('.tutorial-cancel');
    const nextBtn = modal.querySelector('.tutorial-next');

    closeBtn.addEventListener('click', () => this.endTutorial());
    cancelBtn.addEventListener('click', () => this.endTutorial());
    nextBtn.addEventListener('click', () => this.nextStep());

    this.instructionModal = modal;
  }

  // Posicionar modal de instrucciones
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

    // Ajustar para que no se salga de la pantalla
    top = Math.max(20, Math.min(window.innerHeight - modalRect.height - 20, top));
    left = Math.max(20, Math.min(window.innerWidth - modalRect.width - 20, left));

    modal.style.top = `${top}px`;
    modal.style.left = `${left}px`;
  }

  // Siguiente paso
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

  // Completar tutorial
  completeTutorial() {
    // Limpiar
    this.cleanup();

    // Mostrar mensaje de éxito
    this.showSuccessMessage();

    this.isActive = false;
    this.currentTutorial = null;
    this.currentStep = 0;
  }

  // Terminar tutorial (cancelado)
  endTutorial() {
    this.cleanup();
    this.isActive = false;
    this.currentTutorial = null;
    this.currentStep = 0;
  }

  // Limpiar elementos del tutorial
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

  // Mostrar mensaje de éxito
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
