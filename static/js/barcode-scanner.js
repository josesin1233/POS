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
    this.lastScanTime = 0;
    this.scanTimeout = null;
    this.targetField = null; // Add target field property
    this.continuousMode = false; // Close modal after scan by default, can be toggled by user
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
            <button onclick="BarCodeScanner.toggleContinuousMode()" type="button" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: white; font-size: 0.75rem; padding: 0.5rem 1rem;">
              🔄 CONTINUO: ON
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
    if (window.barcodeScanner) {
      window.barcodeScanner.stopScanning();
      // Clear target field
      window.barcodeScanner.targetField = null;
    }
    
    const modal = document.getElementById('barcode-modal');
    if (modal) {
      modal.classList.add('hidden');
      // Force hide modal by removing from DOM if needed
      setTimeout(() => {
        if (modal.classList.contains('hidden')) {
          modal.style.display = 'none';
        }
      }, 100);
    }
    
    console.log('📱 Scanner modal closed');
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

      // Configuración OPTIMIZADA pero compatible para códigos difíciles
      const constraints = {
        video: {
          deviceId: { exact: this.currentCameraId },
          // Progressive resolution based on device capability
          width: { 
            ideal: this.isiPhone6SOrOlder() ? 640 : (this.isMobile() ? 1280 : 1920), 
            min: 320 
          },
          height: { 
            ideal: this.isiPhone6SOrOlder() ? 480 : (this.isMobile() ? 720 : 1080), 
            min: 240 
          },
          facingMode: this.isMobile() ? 'environment' : undefined,
          // iOS Safari specific optimizations - conservative only for iPhone 6S
          ...(this.isiPhone6SOrOlder() && {
            frameRate: { ideal: 15, max: 20 }, // Lower frame rate only for iPhone 6S
            aspectRatio: { ideal: 4/3 } // 4:3 is more stable on older iOS
          }),
          // Better settings for modern iOS devices
          ...(this.isiOS() && !this.isiPhone6SOrOlder() && {
            frameRate: { ideal: 30, max: 30 },
            aspectRatio: { ideal: 16/9 }
          })
        },
        audio: false
      };

      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
      }

      try {
        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (error) {
        console.error('❌ getUserMedia failed:', error);
        if (this.isMobile()) {
          this.updateStatus(`❌ Error cámara: ${error.name}`, 'text-red-600', 'bg-red-50');
          
          // Try fallback constraints for iOS
          if (this.isiOS() && error.name === 'OverconstrainedError') {
            this.updateStatus('🔄 Probando configuración alternativa...', 'text-yellow-600', 'bg-yellow-50');
            const fallbackConstraints = {
              video: {
                facingMode: 'environment',
                // Only use ultra-low settings for iPhone 6S, better for newer devices
                width: { ideal: this.isiPhone6SOrOlder() ? 320 : 720, max: this.isiPhone6SOrOlder() ? 640 : 1280 },
                height: { ideal: this.isiPhone6SOrOlder() ? 240 : 540, max: this.isiPhone6SOrOlder() ? 480 : 720 },
                frameRate: { ideal: this.isiPhone6SOrOlder() ? 10 : 25, max: this.isiPhone6SOrOlder() ? 15 : 30 }
              }
            };
            this.stream = await navigator.mediaDevices.getUserMedia(fallbackConstraints);
          } else {
            throw error;
          }
        } else {
          throw error;
        }
      }
      
      const videoElement = document.getElementById('barcode-video');
      
      // Add debug logging
      console.log('📹 Stream obtenido:', this.stream);
      console.log('📹 Video element:', videoElement);
      
      if (this.isMobile()) {
        this.updateStatus(`📹 Stream OK | Pistas: ${this.stream.getTracks().length}`, 'text-green-600', 'bg-green-50');
      }
      
      // Validate stream tracks are active - More lenient for iOS
      const videoTrack = this.stream.getVideoTracks()[0];
      if (!videoTrack) {
        console.error('❌ No video track found');
        this.updateStatus('❌ Error: No hay pista de video', 'text-red-600', 'bg-red-50');
        return;
      }
      
      // iOS Safari may have track readyState other than 'live' initially, so be more lenient
      if (this.isiOS()) {
        console.log('🍎 iOS detected - Lenient track validation');
      } else if (videoTrack.readyState !== 'live') {
        console.error('❌ Video track is not live:', videoTrack?.readyState);
        this.updateStatus('❌ Error: Video track no disponible', 'text-red-600', 'bg-red-50');
        return;
      }
      
      console.log('📹 Video track state:', videoTrack.readyState, 'enabled:', videoTrack.enabled);
      
      // Visual debugging for mobile
      if (this.isMobile()) {
        this.updateStatus(`🔍 iOS: ${this.isiOS()} | Track: ${videoTrack.readyState} | Enabled: ${videoTrack.enabled}`, 'text-blue-600', 'bg-blue-50');
      }
      
      // Set up video element properly with enhanced error handling
      videoElement.srcObject = null; // Clear first to force refresh
      
      // iOS Safari specific setup
      if (this.isiOS()) {
        videoElement.setAttribute('webkit-playsinline', '');
        videoElement.setAttribute('playsinline', '');
        videoElement.style.webkitTransform = 'translateZ(0)';
      }
      
      setTimeout(() => {
        videoElement.srcObject = this.stream;
        videoElement.setAttribute('autoplay', '');
        videoElement.setAttribute('muted', ''); 
        videoElement.setAttribute('playsinline', '');
        
        // Force CSS properties for better rendering
        videoElement.style.display = 'block';
        videoElement.style.visibility = 'visible';
        videoElement.style.opacity = '1';
        
        // Additional iOS fixes - More aggressive for iPhone 6S
        if (this.isiOS()) {
          videoElement.style.objectFit = 'cover';
          videoElement.style.webkitBackfaceVisibility = 'hidden';
          
          // iOS Safari video rendering fix
          videoElement.style.webkitTransform = 'translate3d(0, 0, 0)';
          videoElement.style.transform = 'translate3d(0, 0, 0)';
          
          // Additional iPhone 6S specific fixes
          videoElement.style.willChange = 'transform';
          videoElement.style.webkitPerspective = '1000px';
          videoElement.style.perspective = '1000px';
          
          // Force iOS video to actually render - Multiple attempts for iPhone 6S
          setTimeout(() => {
            if (videoElement.videoWidth > 0 && videoElement.videoHeight > 0) {
              // Force a layout update
              const parent = videoElement.parentElement;
              if (parent) {
                parent.style.transform = 'translateZ(0.1px)';
                setTimeout(() => {
                  parent.style.transform = '';
                }, 10);
              }
            } else {
              // iPhone 6S fallback - recreate video element if dimensions are still 0
              console.warn('🍎 iPhone 6S: Video dimensions still 0, applying fallback...');
              this.applyiPhone6SFallback(videoElement);
            }
          }, 2000); // Longer wait for iPhone 6S
        }
      }, this.isiOS() ? 500 : 100); // Much longer delay for iPhone 6S
      
      // Monitor stream for issues
      this.stream.getTracks().forEach(track => {
        track.addEventListener('ended', () => {
          console.error('⚠️ STREAM TRACK ENDED unexpectedly:', track.kind);
          this.handleStreamInterruption();
        });
      });

      await new Promise((resolve) => {
        let resolved = false;
        
        const checkVideoReady = () => {
          if (resolved) return;
          
          console.log('🔍 Video readyState:', videoElement.readyState, 'networkState:', videoElement.networkState);
          
          if (videoElement.readyState >= 2) { // HAVE_CURRENT_DATA or higher
            console.log('📹 Video metadata loaded, size:', videoElement.videoWidth, 'x', videoElement.videoHeight);
            
            // Additional validation for black screen - More lenient for iOS
            if (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
              console.warn('⚠️ Video has zero dimensions, forcing refresh...');
              if (this.isMobile()) {
                this.updateStatus('⚠️ Video sin dimensiones - Refrescando...', 'text-yellow-600', 'bg-yellow-50');
              }
              
              // On iOS, sometimes dimensions come later, be more patient
              if (this.isiOS()) {
                console.log('🍎 iOS: Waiting longer for video dimensions...');
                setTimeout(checkVideoReady, 1000); // Longer wait for iOS
                return;
              } else {
                videoElement.load(); // Force reload on other platforms
                setTimeout(checkVideoReady, 500);
                return;
              }
            }
            
            // Ensure video plays with multiple attempts
            const attemptPlay = (attempt = 1) => {
              // iOS specific play handling
              if (this.isiOS() && attempt === 1) {
                // Force video load on iOS
                this.updateStatus('🍎 iOS: Forzando carga de video...', 'text-blue-600', 'bg-blue-50');
                videoElement.load();
                setTimeout(() => {
                  videoElement.play()
                    .then(() => {
                      console.log('✅ iOS Video playing successfully on attempt:', attempt);
                      
                      // Additional iOS rendering checks
                      setTimeout(() => {
                        const computedStyle = window.getComputedStyle(videoElement);
                        const videoVisible = videoElement.offsetWidth > 0 && videoElement.offsetHeight > 0;
                        
                        this.updateStatus(`✅ iOS: Video ${videoElement.videoWidth}x${videoElement.videoHeight} | Visible: ${videoVisible} | Display: ${computedStyle.display}`, 'text-green-600', 'bg-green-50');
                        
                        // Force repaint on iOS if video seems invisible
                        if (!videoVisible || videoElement.videoWidth === 0) {
                          this.updateStatus('🔄 iOS: Video no visible, recreando elemento...', 'text-yellow-600', 'bg-yellow-50');
                          
                          // Recreate video element for iOS
                          const parent = videoElement.parentElement;
                          const newVideo = document.createElement('video');
                          newVideo.id = 'barcode-video';
                          newVideo.style.cssText = videoElement.style.cssText;
                          newVideo.autoplay = true;
                          newVideo.muted = true;
                          newVideo.playsInline = true;
                          newVideo.setAttribute('webkit-playsinline', '');
                          
                          parent.replaceChild(newVideo, videoElement);
                          newVideo.srcObject = this.stream;
                          
                          newVideo.play().then(() => {
                            this.updateStatus(`🎯 iOS: Video recreado y reproduciéndose!`, 'text-green-600', 'bg-green-50');
                          }).catch(console.error);
                        }
                      }, 500);
                      
                      resolved = true;
                      resolve();
                    })
                    .catch(e => {
                      this.updateStatus(`❌ iOS: Error reproducción intento ${attempt}: ${e.message}`, 'text-red-600', 'bg-red-50');
                      attemptPlay(2);
                    });
                }, 300);
                return;
              }
              
              videoElement.play()
                .then(() => {
                  console.log('✅ Video playing successfully on attempt:', attempt);
                  resolved = true;
                  resolve();
                })
                .catch(e => {
                  console.error(`❌ Video play error (attempt ${attempt}):`, e);
                  if (attempt < (this.isiOS() ? 5 : 3)) { // More attempts on iOS
                    setTimeout(() => attemptPlay(attempt + 1), this.isiOS() ? 400 : 200);
                  } else {
                    console.warn('⚠️ Max play attempts reached, continuing...');
                    resolved = true;
                    resolve();
                  }
                });
            };
            
            attemptPlay();
          } else {
            setTimeout(checkVideoReady, 200);
          }
        };
        
        videoElement.onloadedmetadata = checkVideoReady;
        videoElement.oncanplay = checkVideoReady;
        
        // Immediate check in case metadata is already loaded
        setTimeout(checkVideoReady, 100);
        
        // Fallback timeout in case metadata never loads
        setTimeout(() => {
          if (!resolved) {
            console.warn('⏰ Video metadata timeout, continuing...');
            resolved = true;
            resolve();
          }
        }, 8000);
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
  
  isiOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  /**
   * Detect specifically iPhone 6S or older devices that need ultra-conservative settings
   */
  isiPhone6SOrOlder() {
    const userAgent = navigator.userAgent;
    
    // Check for iPhone 6S specifically
    if (/iPhone OS (9_|10_|11_)/.test(userAgent)) {
      return true;
    }
    
    // Check for iPhone 6S hardware identifier if available
    if (userAgent.includes('iPhone8,1') || userAgent.includes('iPhone8,2')) {
      return true;
    }
    
    // Fallback: Check for iPhone with iOS 9-11 (likely iPhone 6S era)
    const iosMatch = userAgent.match(/OS (\d+)_/);
    if (iosMatch) {
      const iosVersion = parseInt(iosMatch[1]);
      // iOS 9-11 likely indicates iPhone 6S or similar era device
      if (iosVersion >= 9 && iosVersion <= 11 && /iPhone/.test(userAgent)) {
        return true;
      }
    }
    
    return false;
  }

  /**
   * iPhone 6S specific fallback for video rendering issues
   */
  async applyiPhone6SFallback(videoElement) {
    try {
      console.log('🍎 Applying iPhone 6S fallback...');
      this.updateStatus('🍎 iPhone 6S: Aplicando corrección...', 'text-orange-600', 'bg-orange-50');
      
      // Stop current stream
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
      }
      
      // Create ultra-conservative constraints for iPhone 6S
      const iPhone6SConstraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: 240, max: 320 },
          height: { ideal: 180, max: 240 },
          frameRate: { ideal: 8, max: 12 } // Very low frame rate
        }
      };
      
      // Get new stream with ultra-low specs
      this.stream = await navigator.mediaDevices.getUserMedia(iPhone6SConstraints);
      
      // Clear video element completely
      videoElement.srcObject = null;
      videoElement.removeAttribute('src');
      
      // Wait and apply stream
      setTimeout(() => {
        videoElement.srcObject = this.stream;
        
        // Force play with multiple attempts
        const forcePlay = (attempt = 1) => {
          videoElement.play()
            .then(() => {
              console.log('✅ iPhone 6S fallback video playing');
              this.updateStatus('✅ iPhone 6S: Video funcionando!', 'text-green-600', 'bg-green-50');
            })
            .catch(e => {
              if (attempt < 3) {
                setTimeout(() => forcePlay(attempt + 1), 500);
              } else {
                console.error('❌ iPhone 6S fallback failed:', e);
                this.updateStatus('❌ iPhone 6S: Error de video', 'text-red-600', 'bg-red-50');
              }
            });
        };
        
        setTimeout(() => forcePlay(), 500);
      }, 1000);
      
    } catch (error) {
      console.error('❌ iPhone 6S fallback error:', error);
      this.updateStatus('❌ iPhone 6S: Error crítico', 'text-red-600', 'bg-red-50');
    }
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
      
      // OPTIMIZED BUT COMPATIBLE CONSTRAINTS FOR FASTER BARCODE SCANNING
      const constraints = {
        video: {
          deviceId: this.currentCameraId ? { exact: this.currentCameraId } : undefined,
          // Higher resolution for better code recognition with compatibility fallback
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
          // Frame rate optimization where supported
          frameRate: { ideal: 30, min: 15 },
          facingMode: this.isMobile() ? 'environment' : undefined
          // Removed advanced camera controls for better compatibility
        }
      };
      
      // ENHANCED DETECTION WITH MULTIPLE STRATEGIES
      let scanInterval;
      
      // Strategy 1: Continuous scanning with optimized frequency
      const result = await this.codeReader.decodeFromConstraints(constraints, videoElement, (result, error) => {
        if (result) {
          const code = result.getText();
          
          // Enhanced duplicate prevention with timestamp
          const now = Date.now();
          if (this.lastScannedCode !== code || (now - this.lastScanTime) > 2000) {
            console.log('🎯 ¡Código detectado con algoritmo principal!', code);
            this.lastScannedCode = code;
            this.lastScanTime = now;
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

      // Strategy 2: Additional high-frequency manual scanning for difficult codes
      scanInterval = setInterval(() => {
        if (this.isScanning && videoElement) {
          // Validate stream health every few cycles
          if (this.scanAttempts % 10 === 0) {
            this.validateAndRecoverStream();
          }
          
          if (videoElement.videoWidth > 0) {
            try {
              // Create canvas for image processing
              const canvas = document.createElement('canvas');
              const ctx = canvas.getContext('2d');
              canvas.width = videoElement.videoWidth;
              canvas.height = videoElement.videoHeight;
              
              // Draw current frame
              ctx.drawImage(videoElement, 0, 0);
              
              // Enhanced image processing for better detection
              const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
              this.enhanceImageForBarcode(imageData, ctx, canvas);
              
              // Try to decode the enhanced image
              this.codeReader.decodeFromImageUrl(canvas.toDataURL())
                .then(result => {
                  if (result) {
                    const code = result.getText();
                    const now = Date.now();
                    if (this.lastScannedCode !== code || (now - this.lastScanTime) > 2000) {
                      console.log('🔥 ¡Código detectado con algoritmo de mejora de imagen!', code);
                      this.lastScannedCode = code;
                      this.lastScanTime = now;
                      this.onCodeScanned(code);
                    }
                  }
                })
                .catch(() => {
                  // Silent fail - this is supplementary scanning
                });
            } catch (error) {
              // Silent fail for supplementary strategy
            }
          } else if (this.scanAttempts % 5 === 0) {
            // Video has zero dimensions, might be black screen
            console.warn('⚠️ Video dimensions are zero, attempting recovery...');
            this.validateAndRecoverStream();
          }
        }
      }, 200); // Scan every 200ms for supplementary detection

      this.scanInterval = scanInterval;
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
    
    // Cerrar modal o reiniciar según el modo
    setTimeout(() => {
      if (this.continuousMode) {
        // Restart scanning without closing - keep camera active
        this.restartScanningAfterSuccess();
      } else {
        // Close scanner (original behavior) - faster closing
        BarCodeScanner.close();
      }
    }, 800); // Reduced delay from 1500ms to 800ms for faster UX
  }

  /**
   * Restart scanning after successful code detection without closing camera
   */
  restartScanningAfterSuccess() {
    try {
      console.log('🔄 Restarting scanner in continuous mode...');
      
      // Verify stream is still active
      if (!this.stream || this.stream.getTracks().every(track => track.readyState === 'ended')) {
        console.warn('⚠️ Stream not active, attempting to restart camera...');
        this.startScanning();
        return;
      }
      
      // Verify video element is still playing
      const videoElement = document.getElementById('barcode-video');
      if (videoElement && (videoElement.paused || videoElement.readyState === 0)) {
        console.warn('⚠️ Video paused or not ready, restarting...');
        videoElement.play().catch(e => console.error('Failed to restart video:', e));
      }
      
      // Reset status and overlay to scanning mode
      this.updateStatus('🎯 Escaneador activo - Escanea otro código', 'text-green-600 animate-pulse', 'bg-green-50');
      
      // Reset overlay to scanning state
      const overlay = document.getElementById('scanner-overlay');
      if (overlay) {
        overlay.classList.remove('success');
        overlay.classList.add('active');
        overlay.innerHTML = `
          <div style="border: 3px dashed #00d4ff; width: 16rem; height: 5rem; border-radius: 0.5rem; background: rgba(0, 212, 255, 0.1); display: flex; align-items: center; justify-content: center;">
            <span style="color: #00d4ff; font-size: 0.875rem; font-weight: 700; text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);">
              Posiciona el código aquí
            </span>
          </div>
        `;
      }
      
      // Show scan indicator again
      const indicator = document.getElementById('scan-indicator');
      if (indicator) {
        indicator.classList.remove('hidden');
      }
      
      // Reset video styling
      if (videoElement) {
        videoElement.classList.add('scanning');
      }
      
      // Reset scan attempts for new code (but DON'T reset lastScannedCode to allow duplicate prevention)
      this.scanAttempts = 0;
      
      console.log('✅ Scanner reiniciado - Listo para el próximo código');
      
    } catch (error) {
      console.error('Error reiniciando scanner:', error);
      // Fallback to closing if restart fails
      BarCodeScanner.close();
    }
  }

  /**
   * Toggle continuous scanning mode
   */
  static toggleContinuousMode() {
    if (window.barcodeScanner) {
      window.barcodeScanner.continuousMode = !window.barcodeScanner.continuousMode;
      const button = document.querySelector('[onclick="BarCodeScanner.toggleContinuousMode()"]');
      if (button) {
        const isEnabled = window.barcodeScanner.continuousMode;
        button.textContent = isEnabled ? '🔄 CONTINUO: ON' : '🔄 CONTINUO: OFF';
        button.style.background = isEnabled ? 
          'linear-gradient(135deg, #22c55e, #16a34a)' : 
          'linear-gradient(135deg, #6b7280, #4b5563)';
      }
      console.log('Modo continuo:', window.barcodeScanner.continuousMode ? 'ACTIVADO' : 'DESACTIVADO');
    }
  }

  /**
   * Toggle flash/torch (para móviles) - IMPROVED
   */
  static async toggleTorch() {
    if (!window.barcodeScanner || !window.barcodeScanner.stream) {
      console.warn('⚠️ No stream available for torch');
      return;
    }

    try {
      const track = window.barcodeScanner.stream.getVideoTracks()[0];
      if (!track) {
        console.warn('⚠️ No video track available');
        return;
      }

      // Check if torch is supported - More aggressive detection
      const capabilities = track.getCapabilities();
      console.log('🔍 Camera capabilities:', capabilities);
      
      // Try multiple ways to detect flash support
      const hasTorch = capabilities && (
        capabilities.torch === true || 
        'torch' in capabilities ||
        capabilities.flashMode ||
        capabilities.flash
      );
      
      if (!hasTorch) {
        console.warn('⚠️ Torch not supported on this device');
        console.log('Device capabilities:', JSON.stringify(capabilities));
        window.barcodeScanner.updateStatus('⚠️ Flash no detectado automáticamente', 'text-yellow-600', 'bg-yellow-50');
        
        // Try anyway on mobile devices (sometimes capabilities lie)
        if (!window.barcodeScanner.isMobile()) {
          return;
        } else {
          console.log('📱 Mobile device - attempting torch anyway...');
        }
      }

      const settings = track.getSettings();
      const currentTorch = settings.torch || false;
      const newTorchState = !currentTorch;

      console.log(`🔦 Toggling torch: ${currentTorch} → ${newTorchState}`);
      
      // Try multiple constraint formats for better compatibility
      try {
        await track.applyConstraints({
          advanced: [{ torch: newTorchState }]
        });
      } catch (error) {
        console.log('🔄 Trying alternative torch constraint...');
        // Try alternative constraint format
        await track.applyConstraints({
          torch: newTorchState
        });
      }

      // Update button text and status
      const torchButton = document.querySelector('[onclick="BarCodeScanner.toggleTorch()"]');
      if (torchButton) {
        torchButton.textContent = newTorchState ? '🔦 Flash ON' : '🔦 Flash';
        torchButton.style.backgroundColor = newTorchState ? '#f59e0b' : '';
      }

      window.barcodeScanner.updateStatus(
        newTorchState ? '🔦 Flash activado' : '🔦 Flash desactivado', 
        'text-blue-600', 
        'bg-blue-50'
      );

      console.log(`✅ Torch ${newTorchState ? 'enabled' : 'disabled'}`);

    } catch (error) {
      console.error('❌ Error toggling torch:', error);
      window.barcodeScanner.updateStatus('❌ Error activando flash', 'text-red-600', 'bg-red-50');
    }
  }

  /**
   * Handle unexpected stream interruption
   */
  handleStreamInterruption() {
    console.error('🚨 STREAM INTERRUPTED - Attempting recovery...');
    this.updateStatus('🔄 Reconectando cámara...', 'text-orange-600', 'bg-orange-50');
    
    // Stop current stream and clear video
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    const videoElement = document.getElementById('barcode-video');
    if (videoElement) {
      videoElement.srcObject = null;
      videoElement.style.backgroundColor = '#000000';
    }
    
    // Try to restart the stream
    setTimeout(() => {
      if (this.isScanning && this.currentCameraId) {
        console.log('🔄 Restarting camera stream...');
        this.startScanning().catch(error => {
          console.error('❌ Failed to restart stream:', error);
          this.updateStatus('❌ Error reconectando - Reinicia manualmente', 'text-red-600', 'bg-red-50');
          
          // Try to refresh camera list as fallback
          this.refreshCameraList();
        });
      }
    }, 1000);
  }
  
  // Add stream validation and recovery method
  async validateAndRecoverStream() {
    if (!this.stream) return false;
    
    const videoTrack = this.stream.getVideoTracks()[0];
    if (!videoTrack || videoTrack.readyState !== 'live') {
      console.warn('🔄 Stream track invalid, attempting recovery...');
      this.handleStreamInterruption();
      return false;
    }
    
    const videoElement = document.getElementById('barcode-video');
    if (videoElement && (videoElement.videoWidth === 0 || videoElement.videoHeight === 0)) {
      console.warn('🔄 Video has zero dimensions, forcing refresh...');
      videoElement.srcObject = null;
      setTimeout(() => {
        videoElement.srcObject = this.stream;
        videoElement.play().catch(console.error);
      }, 100);
      return false;
    }
    
    return true;
  }

  /**
   * Detener escaneo
   */
  stopScanning() {
    console.log('🛑 Stopping scanner...');
    this.isScanning = false;
    this.scanAttempts = 0;
    this.lastScannedCode = null;
    
    if (this.scanTimeout) {
      clearTimeout(this.scanTimeout);
    }
    
    // Clear supplementary scanning interval
    if (this.scanInterval) {
      clearInterval(this.scanInterval);
      this.scanInterval = null;
    }
    
    if (this.codeReader) {
      try {
        this.codeReader.reset();
      } catch (e) {
        console.warn('Warning resetting code reader:', e);
      }
      this.codeReader = null;
    }
    
    if (this.stream) {
      console.log('🛑 Stopping stream tracks...');
      this.stream.getTracks().forEach(track => {
        console.log('🛑 Stopping track:', track.kind, track.readyState);
        track.stop();
      });
      this.stream = null;
    }

    const videoElement = document.getElementById('barcode-video');
    if (videoElement) {
      videoElement.srcObject = null;
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
    if (videoElement) {
      videoElement.classList.remove('scanning');
    }
  }

  /**
   * Enhance image for better barcode detection
   */
  enhanceImageForBarcode(imageData, ctx, canvas) {
    const data = imageData.data;
    const width = imageData.width;
    const height = imageData.height;

    // Convert to grayscale and enhance contrast
    for (let i = 0; i < data.length; i += 4) {
      // Calculate grayscale value
      const gray = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
      
      // Enhance contrast for better barcode detection
      const enhanced = gray < 128 ? Math.max(0, gray - 30) : Math.min(255, gray + 30);
      
      // Apply to all RGB channels
      data[i] = enhanced;     // Red
      data[i + 1] = enhanced; // Green  
      data[i + 2] = enhanced; // Blue
      // Alpha channel stays the same
    }

    // Apply the enhanced image data back to canvas
    ctx.putImageData(imageData, 0, 0);
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
    this.scanThreshold = 50; // OPTIMIZED: Reduced to 50ms for faster detection
    this.minBarcodeLength = 3; // OPTIMIZED: Allow shorter codes
    this.maxBarcodeLength = 30; // OPTIMIZED: Allow longer codes  
    this.isListening = false;
    this.consecutiveScans = 0;
    this.lastScannedCode = '';
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
    // Remove aria-hidden to prevent accessibility warnings when focused
    hiddenInput.setAttribute('aria-label', 'Barcode scanner input');
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
      const timeDiff = now - this.lastInputTime;
      
      // OPTIMIZED: More aggressive buffer reset for faster detection
      if (timeDiff > this.scanThreshold) {
        this.buffer = '';
        this.consecutiveScans = 0;
      }
      
      this.lastInputTime = now;
      
      if (e.key === 'Enter') {
        // End of barcode scan
        this.processBarcodeBuffer();
      } else if (e.key.length === 1) {
        // OPTIMIZED: Add character to buffer (printable characters only)
        this.buffer += e.key;
        
        // OPTIMIZED: Faster auto-trigger for long barcodes
        if (this.buffer.length >= this.maxBarcodeLength) {
          setTimeout(() => this.processBarcodeBuffer(), 10); // Reduced from 50ms to 10ms
        }
        
        // OPTIMIZED: Early trigger for short but valid codes after quick succession
        if (this.buffer.length >= this.minBarcodeLength && timeDiff < 20) {
          this.consecutiveScans++;
          if (this.consecutiveScans >= 3) {
            setTimeout(() => this.processBarcodeBuffer(), 30);
          }
        }
      }
    };
    
    document.addEventListener('keydown', this.keydownHandler, true);
  }

  processBarcodeBuffer() {
    const code = this.buffer.trim();
    this.buffer = '';
    this.consecutiveScans = 0;
    
    // OPTIMIZED: Enhanced validation and duplicate prevention
    if (code.length >= this.minBarcodeLength && code.length <= this.maxBarcodeLength) {
      // Prevent immediate duplicates
      if (code === this.lastScannedCode) {
        console.log('🔄 Duplicate USB scan prevented:', code);
        return;
      }
      
      // OPTIMIZED: More flexible barcode pattern to support more formats
      const barcodePattern = /^[0-9A-Za-z\-_\.\*\+\@\#\$\%\^\&\(\)\[\]]+$/;
      if (barcodePattern.test(code)) {
        this.lastScannedCode = code;
        console.log('⚡ USB Scanner detected barcode:', code);
        
        // OPTIMIZED: Fire global event with enhanced data
        const barcodeEvent = new CustomEvent('barcodeScanned', {
          detail: {
            code: code,
            source: 'usb',
            timestamp: Date.now(),
            targetField: null, // USB scanner doesn't have specific target
            speed: 'fast' // Indicate this was a fast USB scan
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