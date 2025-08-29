console.log("app-utils.js started");
function handleWindowResize() {
    positionNutritionGrid();
    updateGridFontSizes();
    adjustGridScale();
    
    if (currentFood) {
        updateRealTimeBreakdownFromForm();
    }
}

function formatCalories(calories) {
    const num = parseFloat(calories);
    if (isNaN(num)) return "0";
    
    const formatted = num.toFixed(2);
    return formatted.length > 5 ? num.toFixed(1) : formatted;
}