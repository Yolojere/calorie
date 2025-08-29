console.log("app-events.js started");
// Attach all events
function attachEvents() {
    // Admin mode
    $(document).keydown(handleAdminKeyCombo);
    $('#admin-toggle').click(toggleAdminMode);
    
    // Grid toggle
    $('#toggle-grid-btn').click(toggleGridVisibility);
    
    // Food search
    $('#food-search').on('input', handleFoodSearch);
    $('#clear-search').click(clearSearch);            
    
    // Portion controls
    $(document).on('click', '.portion-btn', handlePortionClick);
    $('#grams').on('input', handleGramsInput);
    
    // Add food
    $('#add-food').click(addFoodToLog);
    $('#grams').on('keypress', handleGramsEnterKey);
    
    // Food groups
    $(document).on('click', '.toggle-group', toggleFoodGroup);
    $(document).on('dblclick', '.group-header', toggleFoodGroup);
    
    // Edit grams
    $(document).on('click', '.edit-grams', handleEditGrams);
    
    // Delete items
    $(document).on('click', '.delete-food-btn', handleAdminFoodDelete);
    $(document).on('click', '.delete-item', handleFoodItemDelete);
    
    // Session management
    $('#clear-session').click(clearSession);
    $('#date-selector').on('change', handleDateChange);
    
    // Item selection
    $(document).on('click', '.group-items .list-group-item', handleItemSelection);
    $(document).on('click', '.food-item', handleFoodItemClick);
    updateTemplateButtonState();
    
    // Move/copy functionality
    $('#move-items').click(showMoveItemsModal);
    $('#action-move, #action-copy').click(handleActionSelection);
    $('#confirm-action').click(confirmMoveCopyAction);
    
    // Recipe functionality
    $('#create-recipe').click(showRecipeModal);
    $('#recipe-yes').click(showRecipeNameInput);
    $('#recipe-save').click(saveRecipe);
    
    // Templates
    $('#save-template-btn').click(showSaveTemplateModal);
    $('#confirm-save-template').click(saveTemplate);
    $('#apply-template-btn').click(showApplyTemplateModal);
    $('#confirm-apply-template').click(applyTemplate);
    
    // Camera functionality
    $('#scan-ean').click(showCameraModal);
    $('#toggle-camera').click(toggleCamera);
    $('#resume-scan').click(resumeScanning);
    $('#cameraModal').on('show.bs.modal', prepareCameraModal);
    $('#cameraModal').on('shown.bs.modal', initializeCamera);
    $('#cameraModal').on('hidden.bs.modal', stopCamera);
    
    // Mobile navigation
    $('.mobile-tab-btn').click(handleMobileTabSwitch);
    
    // Window events
    $(window).resize(handleWindowResize);
}