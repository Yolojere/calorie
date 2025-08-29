console.log("app-init.js started");
function initializeApp() {
    initGramsInputReset();
    updateCalorieDifference();
    updateTemplateButtonState();
    loadTopFoods();
    positionNutritionGrid();
    initPortionControls();
    
    // Mobile button linking
    $('#move-items-mobile').click(() => $('#move-items').click());
    $('#save-template-btn-mobile').click(() => $('#save-template-btn').click());
    $('#apply-template-btn-mobile').click(() => $('#apply-template-btn').click());
    $('#clear-session-mobile').click(() => $('#clear-session').click());
    
    // Initial grid state
    $('#toggle-grid-btn').addClass('active');
    updateGridVisibility();
}

// CSRF TOKEN //
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        let token = $('meta[name="csrf-token"]').attr('content');
        if (token) {
            xhr.setRequestHeader("X-CSRFToken", token);
        }
    }
});

function initializeIcons() {
    if (window.FontAwesome) {
        FontAwesome.dom.i2svg();
    }
}

// Font Awesome watcher (from the separate script)
document.addEventListener('DOMContentLoaded', function() {
    if (window.FontAwesome) {
        FontAwesome.dom.watch();
    }
});