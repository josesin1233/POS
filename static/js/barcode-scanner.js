/**
 * BarCodeScanner - Lector de códigos de barras MEJORADO
 * Compatible con múltiples cámaras + optimizado para códigos difíciles
 */
class BarCodeScanner {
  constructor() {
    this.isScanning = false;
    this.stream = null;
    this.codeReader = null;
    this.cameras = [];
    this.currentCameraId = null;
    this.onScanCallback = null;
    this.onErrorCallback = null;
    this.scanAttempts = 0;
    this.maxAttempts = 5; // Más intentos
    this.lastScannedCode = null;
    this.scanTimeout = null;
    this.targetField = null; // Add target field property
  }

  /**
   * Inicializar el scanner
   */
  static init(options = {}) {
    if (!window.barcodeScanner) {
      window.barcodeScanner = new BarCodeScanner();
    }
    
    window.barcodeScanner.onScanCallback = options.onScan || function(code) {
      console.log('Código escaneado:', code);
    };
    
    window.barcodeScanner.onErrorCallback = options.onError || function(error) {
      console.error('Error del scanner:', error);
    };

    window.barcodeScanner.createModal();
    return window.barcodeScanner;
  }

  /**
   * Crear el modal del scanner - RESPONSIVE MEJORADO
   */
  createModal() {
    if (document.getElementById('barcode-modal')) return;

    const modalHTML = `
      <div id="barcode-modal" class="hidden">
        <div>
          <div class="flex-between mb-4">
            <h3>Escanear Código de Barras</h3>
            <button onclick="BarCodeScanner.close()" type="button">&times;</button>
          </div>
          
          <!-- Selector de cámara mejorado -->
          <div class="mb-4">
            <label>Seleccionar cámara:</label>
            <select id="camera-select">
              <option value="">Cargando cámaras disponibles...</option>
            </select>
          </div>

          <!-- Video preview MEJORADO -->
          <div class="video-container">
            <video id="barcode-video" style="width: 100%; height: 18rem; background-color: black; object-fit: cover;" autoplay playsinline muted></video>
            
            <!-- Overlay con guía visual -->
            <div id="scanner-overlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; pointer-events: none;">
              <div style="border: 3px dashed #ef4444; width: 16rem; height: 5rem; border-radius: 0.5rem; background: rgba(239, 68, 68, 0.1); display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-size: 0.875rem; font-weight: 500; background: rgba(239, 68, 68, 0.7); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">
                  Posiciona el código aquí
                </span>
              </div>
            </div>
            
            <!-- Indicador de escaneo activo -->
            <div id="scan-indicator" style="position: absolute; top: 0.75rem; right: 0.75rem; display: none;">
              <div style="background-color: #22c55e; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 500; animation: pulse 2s infinite;">
                Escaneando...
              </div>
            </div>
          </div>

          <!-- Status mejorado -->
          <div id="scanner-status" style="text-align: center; font-size: 0.875rem; color: #6b7280; margin-bottom: 1rem; min-height: 2rem; padding: 0.5rem; border-radius: 0.25rem; background-color: #f9fafb;">
            Preparando escáner de códigos...
          </div>

          <!-- Controles mejorados -->
          <div class="flex-row gap-3" style="flex-wrap: wrap;">
            <button onclick="BarCodeScanner.startScanning()" type="button">
              Iniciar Escaneo
            </button>
            <button onclick="BarCodeScanner.toggleTorch()" type="button">
              Flash
            </button>
            <button onclick="BarCodeScanner.close()" type="button" style="background-color: #6b7280; color: white;">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
  }

  /**
   * Cargar cámaras disponibles - MEJORADO
   */
  async loadCameras() {
    try {
      this.updateStatus('🔐 Solicitando permisos de cámara...', 'text-blue-600', 'bg-blue-50');
      
      // Solicitar permisos explícitamente
      try {
        const tempStream = await navigator.mediaDevices.getUserMedia({ 
          video: { 
            width: { ideal: 1920 }, 
            height: { ideal: 1080 } 
          }, 
          audio: false 
        });
        
        tempStream.getTracks().forEach(track => track.stop());
        this.updateStatus('✅ Permisos concedidos, detectando cámaras...', 'text-green-600', 'bg-green-50');
      } catch (permissionError) {
        this.updateStatus('❌ Permisos de cámara denegados - Permite el acceso', 'text-red-600', 'bg-red-50');
        console.error('Permisos denegados:', permissionError);
        return;
      }

      // Enumerar dispositivos
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      
      const select = document.getElementById('camera-select');
      select.innerHTML = '';

      if (videoDevices.length === 0) {
        select.innerHTML = '<option value="">No se encontraron cámaras</option>';
        this.updateStatus('No hay cámaras disponibles en este dispositivo', 'text-red-600', 'bg-red-50');
        return;
      }

      // Llenar selector con nombres inteligentes
      videoDevices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        
        let label = device.label || `Cámara ${index + 1}`;
        
        // Categorizar cámaras sin iconos
        if (label.toLowerCase().includes('usb') || label.toLowerCase().includes('external')) {
          label = `${label} (Lector USB)`;
        } else if (label.toLowerCase().includes('front') || label.toLowerCase().includes('user')) {
          label = `Cámara Frontal`;
        } else if (label.toLowerCase().includes('back') || label.toLowerCase().includes('environment')) {
          label = `Cámara Trasera (Recomendada)`;
        } else if (label.toLowerCase().includes('webcam')) {
          label = `${label}`;
        } else {
          label = `${label}`;
        }
        
        option.textContent = label;
        select.appendChild(option);
      });

      // Event listener para cambio de cámara
      select.addEventListener('change', () => {
        this.currentCameraId = select.value;
        if (this.isScanning) {
          this.stopScanning();
          setTimeout(() => this.startScanning(), 800);
        }
      });

      // Seleccionar cámara trasera por defecto si existe
      let defaultCamera = videoDevices.find(device => 
        device.label.toLowerCase().includes('back') || 
        device.label.toLowerCase().includes('environment')
      );
      
      if (!defaultCamera) {
        defaultCamera = videoDevices[0];
      }

      this.currentCameraId = defaultCamera.deviceId;
      select.value = this.currentCameraId;
      this.cameras = videoDevices;

      this.updateStatus(`${videoDevices.length} cámara(s) detectada(s) - Lista para escanear`, 'text-green-600', 'bg-green-50');

    } catch (error) {
      console.error('Error cargando cámaras:', error);
      this.updateStatus('Error accediendo a las cámaras - Verifica permisos', 'text-red-600', 'bg-red-50');
      document.getElementById('camera-select').innerHTML = 
        '<option value="">Error: Verifica permisos de cámara en configuración</option>';
    }
  }

  /**
   * Abrir modal - AUTO-START MEJORADO
   */
  static open(targetFieldId = null) {
    console.log(`🎯 SCANNER DEBUG: Opening scanner with targetFieldId: ${targetFieldId}`);
    const modal = document.getElementById('barcode-modal');
    if (modal) {
      // Set target field if provided
      if (window.barcodeScanner) {
        window.barcodeScanner.targetField = targetFieldId;
        console.log(`🎯 SCANNER DEBUG: Set targetField to: ${window.barcodeScanner.targetField}`);
      }
      
      modal.classList.remove('hidden');
      
      // Reset scanner overlay and status to initial state
      const overlay = document.getElementById('scanner-overlay');
      if (overlay) {
        overlay.innerHTML = `
          <div style="border: 3px dashed #ef4444; width: 16rem; height: 5rem; border-radius: 0.5rem; background: rgba(239, 68, 68, 0.1); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-size: 0.875rem; font-weight: 500; background: rgba(239, 68, 68, 0.7); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">
              Posiciona el código aquí
            </span>
          </div>
        `;
      }
      
      // Reset status message
      if (window.barcodeScanner) {
        window.barcodeScanner.updateStatus('Preparando escáner de códigos...', 'text-gray-600', 'bg-gray-50');
      }
      
      setTimeout(async () => {
        await window.barcodeScanner.loadCameras();
        
        if (window.barcodeScanner.cameras.length > 0) {
          // Auto-iniciar más rápido
          setTimeout(() => {
            window.barcodeScanner.startScanning();
          }, 500);
        }
      }, 200);
    }
  }

  /**
   * Cerrar modal
   */
  static close() {
    window.barcodeScanner.stopScanning();
    
    // Clear target field
    if (window.barcodeScanner) {
      window.barcodeScanner.targetField = null;
    }
    
    const modal = document.getElementById('barcode-modal');
    if (modal) {
      modal.classList.add('hidden');
    }
  }

  /**
   * Iniciar escaneo - SÚPER MEJORADO
   */
  async startScanning() {
    if (this.isScanning) {
      this.stopScanning();
      await new Promise(resolve => setTimeout(resolve, 300));
    }

    try {
      const select = document.getElementById('camera-select');
      this.currentCameraId = select.value;

      if (!this.currentCameraId) {
        this.updateStatus('❌ Selecciona una cámara válida primero', 'text-red-600', 'bg-red-50');
        return;
      }

      this.updateStatus('🔄 Iniciando cámara de alta resolución...', 'text-blue-600', 'bg-blue-50');
      this.scanAttempts = 0;
      this.lastScannedCode = null;

      // Configuración OPTIMIZADA para códigos difíciles
      const constraints = {
        video: {
          deviceId: { exact: this.currentCameraId },
          width: { ideal: 1920, min: 1280 }, // Resolución más alta
          height: { ideal: 1080, min: 720 },
          facingMode: this.isMobile() ? 'environment' : undefined,
          focusMode: 'continuous',
          exposureMode: 'continuous', // Mejor exposición
          whiteBalanceMode: 'continuous',
          torch: false
        },
        audio: false
      };

      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
      }

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      const videoElement = document.getElementById('barcode-video');
      videoElement.srcObject = this.stream;

      await new Promise((resolve) => {
        videoElement.onloadedmetadata = resolve;
      });

      // Mostrar indicadores visuales
      document.getElementById('scan-indicator').classList.remove('hidden');
      const overlay = document.getElementById('scanner-overlay');
      if (overlay) {
        overlay.classList.add('active');
      }
      if (videoElement) {
        videoElement.classList.add('scanning');
      }
      this.updateStatus('📱 Cámara activa - Posiciona el código DESPACIO y CENTRADO', 'text-green-600 loading', 'bg-green-50');
      this.isScanning = true;

      // Cargar ZXing y comenzar
      await this.loadZXing();
      this.startZXingScanner();

      // Timeout de seguridad
      this.scanTimeout = setTimeout(() => {
        if (this.isScanning) {
          this.updateStatus('⏰ Escaneo activo - Intenta diferentes ángulos', 'text-yellow-600', 'bg-yellow-50');
        }
      }, 10000);

    } catch (error) {
      console.error('Error iniciando scanner:', error);
      
      let errorMsg = '❌ Error accediendo a la cámara';
      let bgClass = 'bg-red-50';
      
      if (error.name === 'NotAllowedError') {
        errorMsg = '❌ Permisos denegados - Permite acceso a la cámara';
      } else if (error.name === 'NotFoundError') {
        errorMsg = '❌ Cámara no encontrada - Verifica conexión';
      } else if (error.name === 'OverconstrainedError') {
        errorMsg = '❌ Cámara no compatible - Prueba otra cámara';
      }
      
      this.updateStatus(errorMsg, 'text-red-600', bgClass);
      this.onErrorCallback?.(error);
    }
  }

  /**
   * Detectar dispositivo móvil
   */
  isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
   * Cargar ZXing - Updated to latest version
   */
  async loadZXing() {
    if (window.ZXing) return;

    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/@zxing/library@latest/umd/index.min.js';
      script.onload = () => {
        this.updateStatus('📚 Librería ZXing cargada - Escáner listo', 'text-blue-600', 'bg-blue-50');
        resolve();
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  /**
   * Iniciar ZXing - Modern API Implementation
   */
  async startZXingScanner() {
    try {
      this.codeReader = new ZXing.BrowserMultiFormatReader();
      
      // Start continuous decode from video device using modern API
      const videoElement = document.getElementById('barcode-video');
      
      // Use decodeFromConstraints which is the modern approach
      const constraints = {
        video: {
          deviceId: this.currentCameraId ? { exact: this.currentCameraId } : undefined,
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
          facingMode: this.isMobile() ? 'environment' : undefined
        }
      };
      
      // Start decoding from video stream
      const result = await this.codeReader.decodeFromConstraints(constraints, videoElement, (result, error) => {
        if (result) {
          const code = result.getText();
          
          // Evitar códigos duplicados rápidos
          if (this.lastScannedCode !== code) {
            console.log('¡Código detectado!', code);
            this.lastScannedCode = code;
            this.onCodeScanned(code);
          }
        }
        
        if (error && !(error instanceof ZXing.NotFoundException)) {
          this.scanAttempts++;
          if (this.scanAttempts < this.maxAttempts) {
            console.log(`Intento de escaneo ${this.scanAttempts}/${this.maxAttempts}`);
            
            // Feedback progresivo
            if (this.scanAttempts === 2) {
              this.updateStatus('🔍 Analizando código - Mantén estable', 'text-yellow-600', 'bg-yellow-50');
            } else if (this.scanAttempts === 4) {
              this.updateStatus('🎯 Casi listo - Acerca más el código', 'text-orange-600', 'bg-orange-50');
            }
          }
        }
      });

      this.updateStatus('🎯 Escaneador activo - Posiciona el código lentamente', 'text-green-600 animate-pulse', 'bg-green-50');

    } catch (error) {
      console.error('Error ZXing:', error);
      this.updateStatus('❌ Error del escáner - Intenta reiniciar', 'text-red-600', 'bg-red-50');
      
      // Fallback to older API if new one fails
      this.fallbackZXingScanner();
    }
  }
  
  /**
   * Fallback ZXing implementation for older browsers
   */
  fallbackZXingScanner() {
    try {
      if (!this.codeReader) {
        this.codeReader = new ZXing.BrowserMultiFormatReader();
      }
      
      // Use older decodeFromVideoDevice if available
      if (typeof this.codeReader.decodeFromVideoDevice === 'function') {
        this.codeReader.decodeFromVideoDevice(
          this.currentCameraId,
          'barcode-video',
          (result, err) => {
            if (result) {
              const code = result.getText();
              if (this.lastScannedCode !== code) {
                console.log('¡Código detectado (fallback)!', code);
                this.lastScannedCode = code;
                this.onCodeScanned(code);
              }
            }
          }
        );
        this.updateStatus('📱 Escáner en modo compatibilidad', 'text-blue-600', 'bg-blue-50');
      } else {
        throw new Error('No compatible ZXing API found');
      }
    } catch (error) {
      console.error('Fallback ZXing también falló:', error);
      this.updateStatus('❌ Error crítico del escáner', 'text-red-600', 'bg-red-50');
    }
  }

  /**
   * Código escaneado exitosamente - MEJORADO
   */
  onCodeScanned(code) {
    // Limpiar timeout
    if (this.scanTimeout) {
      clearTimeout(this.scanTimeout);
    }
    
    // Efectos de éxito
    this.playSuccessBeep();
    document.getElementById('scan-indicator').classList.add('hidden');
    
    // Mostrar éxito
    this.updateStatus(`¡CÓDIGO ESCANEADO! ${code}`, 'text-green-700 font-bold text-lg', 'bg-green-100');
    
    // Feedback visual en el overlay
    const overlay = document.getElementById('scanner-overlay');
    if (overlay) {
      overlay.classList.remove('active');
      overlay.classList.add('success');
      overlay.innerHTML = `
        <div style="border: 3px solid #00ff88; width: 16rem; height: 5rem; border-radius: 0.75rem; background: rgba(0, 255, 136, 0.2); display: flex; align-items: center; justify-content: center; animation: successPulse 0.6s ease-out;">
          <span style="color: #000000; font-size: 0.875rem; font-weight: 700; background: rgba(0, 255, 136, 0.9); padding: 0.5rem 1rem; border-radius: 0.5rem; text-shadow: none;">
            ¡Código capturado!
          </span>
        </div>
      `;
    }
    
    // GLOBAL EVENT DISPATCH - Fire custom event for any page to listen
    console.log(`🎯 SCANNER DEBUG: Dispatching barcode event with targetField: ${this.targetField}`);
    const barcodeEvent = new CustomEvent('barcodeScanned', {
      detail: {
        code: code,
        source: 'camera',
        timestamp: Date.now(),
        targetField: this.targetField || null // Add target field information
      },
      bubbles: true
    });
    document.dispatchEvent(barcodeEvent);
    
    // Ejecutar callback (legacy support)
    this.onScanCallback?.(code);
    
    // Cerrar modal después de mostrar éxito
    setTimeout(() => {
      BarCodeScanner.close();
    }, 1500);
  }

  /**
   * Toggle flash/torch (para móviles)
   */
  static toggleTorch() {
    if (window.barcodeScanner && window.barcodeScanner.stream) {
      const track = window.barcodeScanner.stream.getVideoTracks()[0];
      if (track && track.getCapabilities && track.getCapabilities().torch) {
        const settings = track.getSettings();
        track.applyConstraints({
          advanced: [{torch: !settings.torch}]
        });
      }
    }
  }

  /**
   * Detener escaneo
   */
  stopScanning() {
    this.isScanning = false;
    this.scanAttempts = 0;
    this.lastScannedCode = null;
    
    if (this.scanTimeout) {
      clearTimeout(this.scanTimeout);
    }
    
    if (this.codeReader) {
      this.codeReader.reset();
      this.codeReader = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    const video = document.getElementById('barcode-video');
    if (video) {
      video.srcObject = null;
    }

    // Limpiar indicadores
    const indicator = document.getElementById('scan-indicator');
    if (indicator) {
      indicator.classList.add('hidden');
    }
    
    // Remove scanning classes
    const overlay = document.getElementById('scanner-overlay');
    if (overlay) {
      overlay.classList.remove('active');
    }
    const video = document.getElementById('barcode-video');
    if (video) {
      video.classList.remove('scanning');
    }
  }

  /**
   * Actualizar mensaje de status - MEJORADO
   */
  updateStatus(message, className = 'text-gray-600', bgClass = 'bg-gray-50') {
    const status = document.getElementById('scanner-status');
    if (status) {
      status.textContent = message;
      status.className = `text-center text-sm mb-4 min-h-8 p-2 rounded ${className} ${bgClass}`;
    }
  }

  /**
   * Sonido de éxito mejorado
   */
  playSuccessBeep() {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      // Doble beep de éxito
      [0, 0.3].forEach((delay, i) => {
        setTimeout(() => {
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          oscillator.frequency.value = i === 0 ? 800 : 1000; // Doble tono
          gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
          
          oscillator.start();
          oscillator.stop(audioContext.currentTime + 0.15);
        }, delay * 1000);
      });
    } catch (error) {
      console.log('No se pudo reproducir sonido:', error);
    }
  }

  /**
   * Métodos estáticos
   */
  static startScanning() {
    window.barcodeScanner?.startScanning();
  }

  static stopScanning() {
    window.barcodeScanner?.stopScanning();
  }
}

// ========================
// USB/KEYBOARD SCANNER SUPPORT
// ========================

class USBBarcodeScanner {
  constructor() {
    this.buffer = '';
    this.lastInputTime = 0;
    this.scanThreshold = 100; // milliseconds between characters to consider it a barcode scan
    this.minBarcodeLength = 4;
    this.maxBarcodeLength = 20;
    this.isListening = false;
  }

  startListening() {
    if (this.isListening) return;
    
    this.isListening = true;
    this.createHiddenInput();
    this.attachGlobalListener();
    console.log('USB/Keyboard barcode scanner listening...');
  }

  stopListening() {
    this.isListening = false;
    this.removeHiddenInput();
    console.log('USB/Keyboard barcode scanner stopped');
  }

  createHiddenInput() {
    // Remove existing hidden input if any
    this.removeHiddenInput();
    
    // Create hidden input to capture USB scanner input
    const hiddenInput = document.createElement('input');
    hiddenInput.id = 'usb-barcode-input';
    hiddenInput.style.position = 'fixed';
    hiddenInput.style.top = '0px';
    hiddenInput.style.left = '0px';
    hiddenInput.style.width = '1px';
    hiddenInput.style.height = '1px';
    hiddenInput.style.opacity = '0';
    hiddenInput.style.pointerEvents = 'none';
    hiddenInput.style.zIndex = '-1000';
    hiddenInput.setAttribute('tabindex', '-1');
    hiddenInput.setAttribute('aria-hidden', 'true');
    document.body.appendChild(hiddenInput);
    
    // Keep focus on hidden input ONLY when no other input is focused - PREVENT SCROLL
    const maintainFocus = () => {
      if (document.activeElement !== hiddenInput && document.hasFocus()) {
        // Don't steal focus from form inputs, textareas, or contenteditable elements
        const activeElement = document.activeElement;
        const isFormField = activeElement && (
          activeElement.tagName === 'INPUT' ||
          activeElement.tagName === 'TEXTAREA' ||
          activeElement.tagName === 'SELECT' ||
          activeElement.isContentEditable ||
          activeElement.hasAttribute('contenteditable')
        );
        
        // Only take focus if no form field is currently focused
        if (!isFormField) {
          try {
            hiddenInput.focus({ preventScroll: true });
          } catch (e) {
            // Fallback for older browsers - use a different approach
            const scrollX = window.scrollX;
            const scrollY = window.scrollY;
            hiddenInput.focus();
            window.scrollTo(scrollX, scrollY);
          }
        }
      }
    };
    
    // Check less frequently and only when needed
    this.focusInterval = setInterval(maintainFocus, 3000); // Every 3 seconds
    
    // Initial focus with scroll prevention
    try {
      hiddenInput.focus({ preventScroll: true });
    } catch (e) {
      // Fallback for older browsers
      const scrollX = window.scrollX;
      const scrollY = window.scrollY;
      hiddenInput.focus();
      window.scrollTo(scrollX, scrollY);
    }
  }

  removeHiddenInput() {
    const existingInput = document.getElementById('usb-barcode-input');
    if (existingInput) {
      existingInput.remove();
    }
    if (this.focusInterval) {
      clearInterval(this.focusInterval);
    }
  }

  attachGlobalListener() {
    this.keydownHandler = (e) => {
      const now = Date.now();
      
      // Reset buffer if too much time has passed (not a barcode scan)
      if (now - this.lastInputTime > this.scanThreshold) {
        this.buffer = '';
      }
      
      this.lastInputTime = now;
      
      if (e.key === 'Enter') {
        // End of barcode scan
        this.processBarcodeBuffer();
      } else if (e.key.length === 1) {
        // Add character to buffer (printable characters only)
        this.buffer += e.key;
        
        // Auto-trigger if buffer gets too long (some scanners don't send Enter)
        if (this.buffer.length >= this.maxBarcodeLength) {
          setTimeout(() => this.processBarcodeBuffer(), 50);
        }
      }
    };
    
    document.addEventListener('keydown', this.keydownHandler, true);
  }

  processBarcodeBuffer() {
    const code = this.buffer.trim();
    this.buffer = '';
    
    // Validate barcode
    if (code.length >= this.minBarcodeLength && code.length <= this.maxBarcodeLength) {
      // Check if it looks like a barcode (mostly numbers or alphanumeric)
      const barcodePattern = /^[0-9A-Za-z\-_\.]+$/;
      if (barcodePattern.test(code)) {
        console.log('USB Scanner detected barcode:', code);
        
        // Fire global event
        const barcodeEvent = new CustomEvent('barcodeScanned', {
          detail: {
            code: code,
            source: 'usb',
            timestamp: Date.now(),
            targetField: null // USB scanner doesn't have specific target
          },
          bubbles: true
        });
        document.dispatchEvent(barcodeEvent);
      }
    }
  }
}

// Auto-inicialización global
if (typeof window !== 'undefined') {
  window.BarCodeScanner = BarCodeScanner;
  window.USBBarcodeScanner = USBBarcodeScanner;
  
  // Auto-start USB scanner when page loads
  window.addEventListener('DOMContentLoaded', () => {
    if (!window.usbBarcodeScanner) {
      window.usbBarcodeScanner = new USBBarcodeScanner();
      window.usbBarcodeScanner.startListening();
    }
  });
}