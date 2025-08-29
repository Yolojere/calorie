console.log("app-mobile.js started");
function handleMobileTabSwitch() {
    const panelId = $(this).data('panel');
    
    // Hide all panels
    $('.mobile-panel').removeClass('active');
    
    // Show selected panel
    $('#' + panelId).addClass('active');
    
    // Update active button
    $('.mobile-tab-btn').removeClass('active');
    $(this).addClass('active');
    
    // Close modals if open
    $('.modal').modal('hide');
}
function adjustMobileFontSize(element, baseSize) {
    if (!element) return;

    // Scale font size based on text length
    const textLength = element.textContent.length;

    // Example: shrink for longer numbers
    let fontSize = baseSize;
    if (textLength > 6) {
        fontSize -= 2;
    }
    if (textLength > 9) {
        fontSize -= 4;
    }

    element.style.fontSize = fontSize + "px";
}
function updateMobileNutrition(totals) {
    const safeParse = (value) => {
        const num = parseFloat(value) || 0;
        if (num < 0.1) return num.toFixed(2);
        if (num < 1) return num.toFixed(1);
        return num.toFixed(0);
    };
    
    $('#mobile-calories').text(safeParse(totals.calories));
    $('#mobile-proteins').text(safeParse(totals.proteins) + 'g');
    $('#mobile-carbs').text(safeParse(totals.carbs) + 'g');
    $('#mobile-fats').text(safeParse(totals.fats) + 'g');
    $('#mobile-sugars').text(safeParse(totals.sugars) + 'g');
    $('#mobile-fiber').text(safeParse(totals.fiber) + 'g');
    $('#mobile-salt').text(safeParse(totals.salt) + 'g');
    $('#mobile-saturated').text(safeParse(totals.saturated) + 'g');
}