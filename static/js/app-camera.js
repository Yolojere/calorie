console.log("app-camera.js started");
function showCameraModal() {
    cameraModal.show();
}

function toggleCamera() {
    currentCamera = currentCamera === 'environment' ? 'user' : 'environment';
    localStorage.setItem('cameraPreference', currentCamera);
    stopCamera();
    
    // Update status
    const cameraType = currentCamera === 'environment' ? 'back' : 'front';
    $('#camera-status').text(`Switching to ${cameraType} camera...`);
    
    setTimeout(startCamera, 500);
}

function resumeScanning() {
    lastScannedCode = null;
    $('#scanned-result').text('');
    startCamera();
}

function prepareCameraModal() {
    // Recreate overlay elements
    $('#scanner-overlay').html(`
        <div class="scanning-text">POSITION BARCODE IN THE SCAN AREA</div>
        <div class="scan-guide"></div>
        <div class="scan-line"></div>
        <div id="scanned-result" class="scanned-result"></div>
    `);
}

function initializeCamera() {
    setTimeout(startCamera, 300);
}

function stopCamera() {
    scanningActive = false;
    if (codeReader) {
        try {
            codeReader.reset();
            // Stop video tracks without removing elements
            const videoElement = document.getElementById('camera-video');
            if (videoElement && videoElement.srcObject) {
                const tracks = videoElement.srcObject.getTracks();
                tracks.forEach(track => track.stop());
                videoElement.srcObject = null;
            }
            codeReader = null;
        } catch (e) {
            console.warn('Error stopping camera:', e);
        }
    }
    
    // Clear scanned result but preserve overlay
    $('#scanned-result').text('');
}

function startCamera() {
    scanningActive = true;
    $('#scanned-result').text('Initializing camera...').css('color', 'white');
    
    // Show the preview container
    $('#camera-preview').css('visibility', 'visible');

    // Initialize ZXing
    if (!codeReader) {
        codeReader = new ZXing.BrowserMultiFormatReader();
    }

    // Force back camera by default
    currentCamera = 'environment';
    
    // List available cameras
    codeReader.listVideoInputDevices()
        .then(videoInputDevices => {
            if (videoInputDevices.length === 0) {
                $('#scanned-result').html('No cameras found');
                return;
            }
            
            let cameraId;
            let cameraLabel = '';
            let backCamera = null;
            let frontCamera = null;
            
            // Classify cameras
            videoInputDevices.forEach(device => {
                if (/back|rear|environment|1|primary|main|wide/i.test(device.label.toLowerCase())) {
                    backCamera = device;
                } else if (/front|user|0|selfie|face/i.test(device.label.toLowerCase())) {
                    frontCamera = device;
                }
            });
            
            // Select camera based on preference
            if (currentCamera === 'environment' && backCamera) {
                cameraId = backCamera.deviceId;
                cameraLabel = 'back';
            } else if (currentCamera === 'user' && frontCamera) {
                cameraId = frontCamera.deviceId;
                cameraLabel = 'front';
            } else {
                // Fallback to first available camera
                cameraId = videoInputDevices[0].deviceId;
                cameraLabel = videoInputDevices[0].label;
            }

            // Start decoding
            codeReader.decodeFromVideoDevice(cameraId, 'camera-video', (result, err) => {
                if (result) {
                    const code = result.text;
                    if (lastScannedCode === code) return;
                    
                    lastScannedCode = code;
                    $('#scanned-result').html(`<strong>SCANNED:</strong> ${code}<br>Processing...`)
                        .css('color', '#00ff00');
                    
                    handleScannedCode(code);
                } 
                
                if (err && !(err instanceof ZXing.NotFoundException)) {
                    console.error('ZXing error:', err);
                    $('#scanned-result').text(`Error: ${err.message}`).css('color', 'red');
                }
            });
            
            $('#camera-status').text(`Using ${cameraLabel} camera`);
        })
        .catch(err => {
            console.error('Camera error:', err);
            $('#scanned-result').text(`Camera error: ${err.message}`).css('color', 'red');
        });
}

function handleScannedCode(code) {
    // Validate EAN code
    if (!/^\d{8,13}$/.test(code)) {
        $('#scanned-result').html(`<strong>Invalid barcode:</strong> ${code}<br>Only EAN-8/EAN-13 supported`)
            .css('color', 'orange');
        return;
    }

    // Close modal and process
    cameraModal.hide();
    stopCamera();
    
    // Set search field value
    $('#food-search').val(code);
    
    // Highlight the search field
    $('#food-search').addClass('highlight-search');
    setTimeout(() => $('#food-search').removeClass('highlight-search'), 3000);
    
    // Trigger search
    setTimeout(() => {
        $('#food-search').focus();
        const query = $('#food-search').val().trim();
        if (query.length > 0) {
            performFoodSearch(query);
        }
    }, 100);
}

function performFoodSearch(query) {
    $.post('/search_foods', { query }, data => {
        let resultsHtml = '';
        if (data.length > 0) {
            resultsHtml = '<div class="list-group">';
            data.forEach(food => resultsHtml += createFoodItemHtml(food));
            resultsHtml += '</div>';
            
            // AUTO-SELECT THE FIRST RESULT AFTER RENDERING
            setTimeout(() => {
                if ($('.food-item').length > 0) {
                    $('.food-item:first').trigger('click');
                }
            }, 300);
        } else {
            resultsHtml = '<div class="text-center p-2 small">No results found</div>';
        }
        $('#search-results').html(resultsHtml);
    });
}