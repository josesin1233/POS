/**
 * BarCodeScanner - Lector de códigos de barras MEJORADO
 * Compatible con múltiples cámaras + optimizado para códigos difíciles
 */
class BarCodeScanner {
  constructor() {
    this.isScanning = false;
    this.stream = null;
    this.codeReader = null;
    this.detector = null;
    this.rafId = null;
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
          <div class="video-container" style="position: relative; width: 100%; height: 300px; max-height: 50vh; border-radius: 12px; overflow: hidden; background: black;">
            <video id="barcode-video" style="width: 100%; height: 100%; background-color: black; object-fit: cover; border-radius: 12px;" autoplay playsinline muted></video>
            
            <!-- Overlay con guía visual RESPONSIVE -->
            <div id="scanner-overlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; pointer-events: none; padding: 20px;">
              <div style="border: 3px dashed #ef4444; max-width: 280px; width: 80%; height: 80px; max-height: 25%; border-radius: 12px; background: rgba(239, 68, 68, 0.1); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px);">
                <span style="color: white; font-size: 14px; font-weight: 600; background: rgba(239, 68, 68, 0.8); padding: 8px 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                  📱 Posiciona el código aquí
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
            <button onclick="BarCodeScanner.toggleTorch()" type="button" class="scanner-btn scanner-btn-torch">
              🔦 Flash
            </button>
            <button onclick="BarCodeScanner.close()" type="button" class="scanner-btn scanner-btn-cancel">
              ❌ Cancelar
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
      // Check HTTPS compatibility first
      const httpsCheck = this.checkHTTPS();
      console.log('🔒 HTTPS Check:', httpsCheck);

      if (httpsCheck.required && !httpsCheck.available) {
        this.updateStatus(httpsCheck.message + ' - Cámara no disponible', 'text-red-600', 'bg-red-50');
        return;
      }

      // Check if permission was already granted (skip prompt if so)
      let permissionAlreadyGranted = false;
      try {
        if (navigator.permissions && navigator.permissions.query) {
          const permStatus = await navigator.permissions.query({ name: 'camera' });
          permissionAlreadyGranted = permStatus.state === 'granted';
          console.log('📷 Camera permission state:', permStatus.state);
        }
      } catch (e) {
        // permissions.query not supported (e.g. Safari), fall through
        console.log('📷 permissions.query not supported, checking via enumerateDevices');
        // Alternative check: if enumerateDevices returns labels, permission was granted
        const devs = await navigator.mediaDevices.enumerateDevices();
        const videoDevs = devs.filter(d => d.kind === 'videoinput');
        permissionAlreadyGranted = videoDevs.length > 0 && videoDevs[0].label !== '';
      }

      if (permissionAlreadyGranted) {
        console.log('✅ Camera permission already granted, skipping prompt');
        this.updateStatus('✅ Permisos concedidos, detectando cámaras...', 'text-green-600', 'bg-green-50');
      } else {
        // Need to request permission
        if (this.isiOS()) {
          const iosVersion = this.getIOSVersion();
          if (iosVersion) {
            console.log(`📱 iOS ${iosVersion.full} detected`);
            this.updateStatus(`📱 iOS ${iosVersion.full} - Solicitando permisos...`, 'text-blue-600', 'bg-blue-50');
          }
        } else {
          this.updateStatus('🔐 Solicitando permisos de cámara...', 'text-blue-600', 'bg-blue-50');
        }

        try {
          const constraints = this.isiPhone6S() ? {
            video: {
              width: { ideal: 640, max: 1280 },
              height: { ideal: 480, max: 720 },
              facingMode: 'environment'
            },
            audio: false
          } : {
            video: {
              width: { ideal: 1920 },
              height: { ideal: 1080 }
            },
            audio: false
          };

          const tempStream = await navigator.mediaDevices.getUserMedia(constraints);
          tempStream.getTracks().forEach(track => track.stop());
          this.updateStatus('✅ Permisos concedidos, detectando cámaras...', 'text-green-600', 'bg-green-50');
        } catch (permissionError) {
          console.error('❌ Permission error:', permissionError);

          if (this.isiPhone6S()) {
            const iosVersion = this.getIOSVersion();
            if (iosVersion && iosVersion.major < 11) {
              this.updateStatus(`❌ iOS ${iosVersion.full}: getUserMedia no soportado`, 'text-red-600', 'bg-red-50');
              return;
            }
          }

          this.updateStatus('❌ Permisos de cámara denegados - Permite el acceso', 'text-red-600', 'bg-red-50');
          console.error('Permisos denegados:', permissionError);
          return;
        }
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
      modal.style.display = ''; // CRITICAL: Reset display in case close() set it to none

      // Reset scanner overlay and status to initial state
      const overlay = document.getElementById('scanner-overlay');
      if (overlay) {
        overlay.classList.remove('success');
        overlay.innerHTML = `
          <div style="border: 3px dashed #ef4444; max-width: 280px; width: 80%; height: 80px; max-height: 25%; border-radius: 12px; background: rgba(239, 68, 68, 0.1); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px);">
            <span style="color: white; font-size: 14px; font-weight: 600; background: rgba(239, 68, 68, 0.8); padding: 8px 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
              📱 Posiciona el código aquí
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
          // Auto-iniciar inmediatamente
          window.barcodeScanner.startScanning();
        }
      }, 100);
    }
  }

  /**
   * Cerrar modal - FIXED FOR REOPEN
   */
  static close() {
    if (window.barcodeScanner) {
      console.log('🛑 Closing scanner - stopping all streams...');
      window.barcodeScanner.stopScanning();

      // CRITICAL: Completely clean up the scanner state
      window.barcodeScanner.isScanning = false;
      window.barcodeScanner.codeReader = null;
      window.barcodeScanner.scanAttempts = 0;
      window.barcodeScanner.lastScannedCode = null;
      window.barcodeScanner.lastScanTime = 0;
      window.barcodeScanner.targetField = null;

      // Clean up video element completely
      const videoElement = document.getElementById('barcode-video');
      if (videoElement) {
        videoElement.srcObject = null;
        videoElement.removeAttribute('src');
        videoElement.style.backgroundColor = 'black';
      }
    }

    const modal = document.getElementById('barcode-modal');
    if (modal) {
      modal.classList.add('hidden');
      // Do NOT set display:none - let the hidden class handle visibility
      // This way open() can simply remove 'hidden' to show it again
    }

    console.log('✅ Scanner modal completely closed and cleaned');
  }

  /**
   * Iniciar escaneo - REESCRITO PARA iPHONE 6S
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

      // iPhone 6S specific status
      if (this.isiPhone6S()) {
        this.updateStatus('📱 iPhone 6S: Iniciando cámara optimizada...', 'text-blue-600', 'bg-blue-50');
      } else {
        this.updateStatus('🔄 Iniciando cámara de alta resolución...', 'text-blue-600', 'bg-blue-50');
      }
      
      this.scanAttempts = 0;
      this.lastScannedCode = null;

      // iPhone 6S SPECIFIC CONSTRAINTS - Very conservative
      const constraints = this.isiPhone6S() ? {
        video: {
          deviceId: { exact: this.currentCameraId },
          width: { ideal: 640, max: 1280, min: 480 }, // Conservative for iPhone 6S
          height: { ideal: 480, max: 720, min: 360 },
          facingMode: 'environment',
          frameRate: { ideal: 20, max: 25 }, // Lower frame rate for iPhone 6S
          aspectRatio: { ideal: 4/3 } // More stable ratio
        },
        audio: false
      } : {
        // Modern devices - full resolution
        video: {
          deviceId: { exact: this.currentCameraId },
          width: { ideal: this.isMobile() ? 1280 : 1920, min: 640 },
          height: { ideal: this.isMobile() ? 720 : 1080, min: 480 },
          facingMode: this.isMobile() ? 'environment' : undefined,
          ...(this.isiOS() && {
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
                width: { ideal: 640 },
                height: { ideal: 480 }
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
      
      // iPhone 6S gets special treatment - HTTPS COMPATIBLE
      const setupDelay = this.isiPhone6S() ? 1500 : (this.isiOS() ? 200 : 100);
      
      setTimeout(() => {
        // CRITICAL: Clear video first for iPhone 6S
        if (this.isiPhone6S()) {
          console.log('📱 iPhone 6S: Clearing video element...');
          videoElement.srcObject = null;
          videoElement.removeAttribute('src');
          videoElement.load(); // Force reload for iPhone 6S
        }
        
        // Set video source
        videoElement.srcObject = this.stream;
        
        // CRITICAL: Use setAttribute (not property assignment) for iOS compatibility
        videoElement.setAttribute('autoplay', '');
        videoElement.setAttribute('muted', ''); 
        videoElement.setAttribute('playsinline', '');
        videoElement.setAttribute('webkit-playsinline', ''); // iOS specific
        
        // Also set properties for double security
        videoElement.autoplay = true;
        videoElement.muted = true;
        videoElement.playsInline = true;
        
        // Force CSS properties for better rendering
        videoElement.style.display = 'block';
        videoElement.style.visibility = 'visible';
        videoElement.style.opacity = '1';
        
        // iPhone 6S specific fixes for iOS 9-15
        if (this.isiPhone6S()) {
          const iosVersion = this.getIOSVersion();
          console.log(`📱 Applying iPhone 6S fixes for iOS ${iosVersion?.full || 'unknown'}...`);
          
          // Less aggressive styling for old iOS
          videoElement.style.objectFit = 'contain';
          videoElement.style.webkitTransform = 'translate3d(0, 0, 0)';
          videoElement.style.transform = 'translate3d(0, 0, 0)';
          videoElement.style.webkitBackfaceVisibility = 'hidden';
          videoElement.style.backfaceVisibility = 'hidden';
          
          // Force hardware acceleration
          videoElement.style.willChange = 'transform';
          videoElement.style.webkitPerspective = '1000px';
          
          // iPhone 6S - Multiple play attempts with increasing delays
          let playAttempt = 0;
          const attemptPlay = () => {
            playAttempt++;
            console.log(`📱 iPhone 6S play attempt ${playAttempt}...`);
            
            videoElement.play()
              .then(() => {
                console.log(`✅ iPhone 6S video playing on attempt ${playAttempt}`);
                this.updateStatus(`✅ iPhone 6S: Cámara activa (intento ${playAttempt})`, 'text-green-600', 'bg-green-50');
              })
              .catch(e => {
                console.error(`❌ iPhone 6S play attempt ${playAttempt} failed:`, e);
                
                if (playAttempt < 3) {
                  this.updateStatus(`⚠️ iPhone 6S: Reintentando ${playAttempt}/3...`, 'text-yellow-600', 'bg-yellow-50');
                  setTimeout(attemptPlay, 1000 * playAttempt); // Increasing delay
                } else {
                  this.updateStatus('❌ iPhone 6S: Error de video - iOS muy antiguo?', 'text-red-600', 'bg-red-50');
                }
              });
          };
          
          // Start first attempt after delay
          setTimeout(attemptPlay, 800);
          
        } else if (this.isiOS()) {
          // Modern iOS devices
          videoElement.style.objectFit = 'cover';
          videoElement.style.webkitBackfaceVisibility = 'hidden';
          videoElement.style.webkitTransform = 'translate3d(0, 0, 0)';
          videoElement.style.transform = 'translate3d(0, 0, 0)';
        }
      }, setupDelay);
      
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

      // Cargar detector y comenzar
      await this.loadBarcodeDetector();
      this.startBarcodeDetector();

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
   * iPhone 6S specific detection with iOS version checking
   */
  isiPhone6S() {
    const userAgent = navigator.userAgent;
    
    // Detect iPhone 6S specifically
    if (/iPhone/.test(userAgent)) {
      const iosMatch = userAgent.match(/OS (\d+)_(\d+)/);
      if (iosMatch) {
        const iosVersion = parseInt(iosMatch[1]);
        const iosMinor = parseInt(iosMatch[2]);
        
        // iPhone 6S detection - focus on problematic iOS versions
        return iosVersion <= 15; // iOS 9-15 had various getUserMedia issues
      }
    }
    
    return false;
  }

  /**
   * Get iOS version for compatibility checks
   */
  getIOSVersion() {
    const userAgent = navigator.userAgent;
    const iosMatch = userAgent.match(/OS (\d+)_(\d+)/);
    if (iosMatch && /iPhone|iPad|iPod/.test(userAgent)) {
      return {
        major: parseInt(iosMatch[1]),
        minor: parseInt(iosMatch[2]),
        full: `${iosMatch[1]}.${iosMatch[2]}`
      };
    }
    return null;
  }

  /**
   * Check if HTTPS is required and available
   */
  checkHTTPS() {
    const isHTTPS = location.protocol === 'https:';
    const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    
    if (!isHTTPS && !isLocalhost && this.isiOS()) {
      const iosVersion = this.getIOSVersion();
      if (iosVersion && iosVersion.major >= 12) {
        return {
          required: true,
          available: false,
          message: `⚠️ iOS ${iosVersion.full}: HTTPS requerido para cámara`
        };
      }
    }
    
    return {
      required: false,
      available: isHTTPS || isLocalhost,
      message: isHTTPS ? '✅ HTTPS activo' : '⚠️ Usando HTTP'
    };
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
   * Cargar BarcodeDetector (nativo en Chrome/Android, polyfill ZXing-WASM en iOS/Firefox)
   */
  async loadBarcodeDetector() {
    if ('BarcodeDetector' in window) return; // Ya disponible nativamente

    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      // Polyfill que usa ZXing-WASM: nativo en Chrome/Edge/Android, WASM en iOS/Firefox
      script.src = 'https://cdn.jsdelivr.net/npm/barcode-detector@3/dist/es2022/polyfill.min.js';
      script.onload = () => {
        this.updateStatus('Librería cargada - Escáner listo', 'text-blue-600', 'bg-blue-50');
        resolve();
      };
      script.onerror = () => {
        // Si el CDN falla, el escáner no puede continuar
        reject(new Error('No se pudo cargar la librería del escáner'));
      };
      document.head.appendChild(script);
    });
  }

  /**
   * Iniciar detección de códigos de barras con BarcodeDetector API
   * - Chrome/Android/Edge: usa detección nativa por hardware (muy rápido)
   * - iOS Safari / Firefox: usa polyfill ZXing-WASM (más rápido que ZXing JS)
   */
  async startBarcodeDetector() {
    try {
      const formats = [
        'ean_13', 'ean_8', 'upc_a', 'upc_e',
        'code_128', 'code_39', 'code_93',
        'qr_code', 'itf', 'data_matrix', 'aztec', 'pdf417'
      ];

      this.detector = new BarcodeDetector({ formats });

      const videoElement = document.getElementById('barcode-video');
      let streamCheckCounter = 0;

      const scan = async () => {
        if (!this.isScanning || !videoElement) return;

        streamCheckCounter++;
        if (streamCheckCounter % 150 === 0) {
          this.validateAndRecoverStream();
        }

        if (videoElement.videoWidth > 0 && videoElement.readyState >= 2) {
          try {
            const barcodes = await this.detector.detect(videoElement);
            if (barcodes.length > 0) {
              const code = barcodes[0].rawValue;
              const now = Date.now();
              if (this.lastScannedCode !== code || (now - this.lastScanTime) > 2000) {
                console.log('Codigo detectado:', code);
                this.lastScannedCode = code;
                this.lastScanTime = now;
                this.onCodeScanned(code);
                return; // Pausa el loop hasta que el usuario esté listo para otro escaneo
              }
            }
          } catch (e) {
            // Silent fail, continuar escaneando
          }
        }

        this.rafId = requestAnimationFrame(scan);
      };

      this.rafId = requestAnimationFrame(scan);
      this.updateStatus('Escaneador activo - Posiciona el codigo', 'text-green-600 animate-pulse', 'bg-green-50');

    } catch (error) {
      console.error('Error BarcodeDetector:', error);
      this.updateStatus('Error del escaner - Intenta reiniciar', 'text-red-600', 'bg-red-50');
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
        <div style="border: 3px solid #00ff88; max-width: 280px; width: 80%; height: 80px; max-height: 25%; border-radius: 12px; background: rgba(0, 255, 136, 0.2); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px); animation: successPulse 0.6s ease-out;">
          <span style="color: #000000; font-size: 14px; font-weight: 700; background: rgba(0, 255, 136, 0.9); padding: 8px 16px; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
            ✅ ¡Código capturado!
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
    
    // Cerrar modal después del escaneo exitoso
    setTimeout(() => {
      BarCodeScanner.close();
    }, 800);
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
        torchButton.textContent = newTorchState ? '💡 Flash ON' : '🔦 Flash';
        if (newTorchState) {
          torchButton.style.background = 'linear-gradient(135deg, #fbbf24, #f59e0b)';
          torchButton.style.boxShadow = '0 4px 12px rgba(251, 191, 36, 0.4)';
        } else {
          torchButton.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
          torchButton.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
        }
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
    
    // Cancelar loop de animación
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    this.detector = null;

    // Compatibilidad: limpiar codeReader si quedó de sesión anterior
    if (this.codeReader) {
      try {
        this.codeReader.reset();
      } catch (e) {}
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