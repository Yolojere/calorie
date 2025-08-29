console.log("app-portion.js started");
function handlePortionClick(e) {
    e.stopPropagation();
    
    // Reset all OTHER buttons but not this one
    $('.portion-btn').not(this).each(function() {
        const baseSize = parseFloat($(this).data('portion-size'));
        const portionType = $(this).data('portion-type');
        const label = portionType.charAt(0).toUpperCase() + portionType.slice(1);
        $(this).text(`${label} (${baseSize}g)`);
        $(this).data('multiple', 0);
        $(this).removeClass('active');
    });

    let multiple = parseInt($(this).data('multiple')) || 0;
    const baseSize = parseFloat($(this).data('portion-size'));
    const portionType = $(this).data('portion-type');
    const label = portionType.charAt(0).toUpperCase() + portionType.slice(1);

    // Increment multiple (first click = 1)
    multiple++;

    const totalGrams = baseSize * multiple;

    $(this).text(`${multiple} ${label} (${totalGrams}g)`);
    $(this).data('multiple', multiple);

    $('#grams').val(totalGrams).trigger('focus');
    updateRealTimeBreakdownFromForm();
    $(this).addClass('active');
}

function handleGramsInput() {
    resetPortionButtons();
    updateRealTimeBreakdownFromForm();
}

function handleGramsEnterKey(e) {
    if (e.which === 13) { // Enter key
        $('#add-food').click();
    }
}

function updatePortionButtons(food) {
    const container = $('#portion-buttons');
    container.empty();
    
    const portionTypes = [
        { type: 'serving', label: 'Serving', size: food.serving_size },
        { type: 'half', label: 'Half', size: food.half_size },
        { type: 'entire', label: 'Entire', size: food.entire_size }
    ];
    
    portionTypes.forEach(portion => {
        if (portion.size) {
            const button = $(`
                <button type="button" class="btn portion-btn" 
                        data-portion-type="${portion.type}" 
                        data-portion-size="${portion.size}"
                        data-multiple="0">
                    ${portion.label} (${portion.size}g)
                </button>
            `);
            container.append(button);
        }
    });
}

function initPortionControls() {
    // Document click handler to reset portion buttons
    $(document).on('click', function(e) {
        const target = $(e.target);
        
        // Check if click is inside whitelisted elements
        const isWhitelisted = target.closest('#meal-group').length > 0 || 
                             target.is('#grams') || 
                             target.closest('#add-food').length > 0 ||
                             target.closest('.portion-btn').length > 0 ||
                             target.is('#date-selector, #date-selector option');                  
        // If click is outside whitelisted elements, reset the portion buttons
        if (!isWhitelisted) {
            resetPortionButtons();
            updateRealTimeBreakdownFromForm();
        }
    });
}

function resetPortionButtons() {
    $('.portion-btn').each(function() {
        const baseSize = parseFloat($(this).data('portion-size'));
        const portionType = $(this).data('portion-type');
        const label = portionType.charAt(0).toUpperCase() + portionType.slice(1);
        $(this).text(`${label} (${baseSize}g)`);
        $(this).data('multiple', 0);
        $(this).removeClass('active');
    });

    if (!$('#grams').is(':focus')) {
        setTimeout(() => {
            $('#grams').trigger('focus').trigger('select');
        }, 50);
    }
}

function initGramsInputReset() {
    // Define whitelisted elements that should NOT trigger reset
    const whitelist = [
        '#meal-group',
        '#grams',
        '#add-food',
        '.portion-btn',
        '#portion-buttons',
        '.modal',
        '.btn-close'
    ];
    
    const whitelistSelector = whitelist.join(', ');
    
    $(document).on('click', function(e) {
        const $target = $(e.target);
        
        // Check if click is inside whitelisted elements
        const isWhitelisted = $target.is(whitelistSelector) || 
                             $target.closest(whitelistSelector).length > 0;
        
        // Reset grams input if click is outside whitelisted elements
        if (!isWhitelisted) {
            resetGramsInput();
        }
    });
}

function resetGramsInput() {
    $('#grams').val('');
    if (currentFood) {
        updateRealTimeBreakdown({
            calories: 0,
            proteins: 0,
            carbs: 0,
            fats: 0,
            grams: 0
        });
    }
    if (!$('#grams').is(':focus')) {
        setTimeout(() => {
            $('#grams').trigger('focus').trigger('select');
        }, 50);
    }
}