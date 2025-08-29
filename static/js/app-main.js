console.log("app-main.js started");
    // ===== STATE VARIABLES =====
    let currentSelectedDate = CURRENT_DATE;
    let codeReader = null;
    let currentFood = null;
    let selectedItems = [];
    let selectedItemsForRecipe = [];
    let gridVisible = true;
    let isAdminMode = false;
    let keySequence = [];
    let currentCamera = localStorage.getItem('cameraPreference') || 'user';
    let scanningActive = false;
    let lastScannedCode = null;
    $(document).ready(function() {
    
    // ===== MODAL INSTANCES =====
    const editGramsModal = new bootstrap.Modal(document.getElementById('editGramsModal'));
    const moveItemsModal = new bootstrap.Modal(document.getElementById('moveItemsModal'));
    const recipeModal = new bootstrap.Modal(document.getElementById('recipeModal'));
    const cameraModal = new bootstrap.Modal(document.getElementById('cameraModal'));
    
    // Startup
    $('#date-selector').val(currentSelectedDate);
    initializeApp();
    setTimeout(() => {
        $('#date-selector').trigger('change');
    }, 100);
    
    // Attach all events
    attachEvents();
    
    // ===== INITIALIZE THE APP =====
    initializeApp();
});