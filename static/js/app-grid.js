console.log("app-grid.js started");
function toggleGridVisibility() {
    gridVisible = !gridVisible;
    updateGridVisibility();
    $(this).toggleClass('active', gridVisible);
}

function updateGridVisibility() {
    gridVisible ? $('.nutrition-grid-container').show() : $('.nutrition-grid-container').hide();
}

function positionNutritionGrid() {
    const navbarHeight = $('.navbar').outerHeight();
    const container = $('.container-main');
    const containerOffset = container.offset();
    const containerWidth = container.width();
    
    // Calculate responsive position
    const responsiveOffset = Math.min(40, window.innerWidth * 0.02);
    const gridLeft = containerOffset.left + containerWidth + responsiveOffset;
    
    // Apply responsive sizing
    const gridHeight = Math.min(900, window.innerHeight * 0.7);
    
    $('.nutrition-grid-container').css({
        'top': navbarHeight + 20,
        'left': gridLeft,
        'height': gridHeight + 'px'
    });
}

function updateGridFontSizes() {
    const baseSize = Math.min(16, window.innerWidth * 0.012);
    $('.grid-cell').css('font-size', baseSize + 'px');
    $('.grid-value').css('font-size', (baseSize * 1.1) + 'px');
    $('.grid-cell i').css('font-size', (baseSize * 1.4) + 'px');
}

function adjustGridScale() {
    const grid = $('.nutrition-grid-container');
    const windowHeight = window.innerHeight;
    const gridHeight = grid.height();
    
    if (windowHeight < 900) {
        const scale = Math.max(0.7, Math.min(1, windowHeight / 1000));
        grid.css('transform', `scale(${scale})`);
        
        // Adjust cell padding dynamically
        const cellPadding = Math.max(4, 8 * scale);
        $('.grid-cell').css('padding', `${cellPadding}px 3px`);
    }
}