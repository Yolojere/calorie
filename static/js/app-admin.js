console.log("app-admin.js started");
function toggleAdminMode() {
    isAdminMode = !isAdminMode;
    $('#admin-toggle').toggle(isAdminMode);
    $('body').toggleClass('admin-active', isAdminMode);
    $('.delete-food-btn').toggle(isAdminMode);
    
    alert(`Admin mode ${isAdminMode ? 'ENABLED' : 'DISABLED'}`);
}

function handleAdminKeyCombo(e) {
    keySequence.push(e.key);
    if (keySequence.length > ADMIN_KEY_COMBO.length) {
        keySequence.shift();
    }
    
    if (keySequence.join('') === ADMIN_KEY_COMBO.join('')) {
        toggleAdminMode();
        keySequence = [];
    }
}