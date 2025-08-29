console.log("app-log.js started");
function addFoodToLog() {
    const foodId = $(this).data('id');
    const grams = parseFloat($('#grams').val()) || 0;
    const mealGroup = $('#meal-group').val();
    
    let unitType = 'grams';
    let units = grams;
    
    // Check if there is an active portion button
    const activeButton = $('.portion-btn.active');
    if (activeButton.length) {
        unitType = activeButton.data('portion-type');
        units = 1;
    }
    
    $.post('/log_food', {
        food_id: foodId,
        unit_type: 'grams',
        units: grams,
        meal_group: mealGroup
    }, response => {
        // Save scroll position before updating
        const scrollPos = $('#food-log').scrollTop();
        
        updateSessionDisplay(response.session, response.totals, response.breakdown);
        updateCalorieDifference();
        
        // Restore scroll position after update
        $('#food-log').scrollTop(scrollPos);
        resetFoodForm();
        
        if (response.is_mobile) {
            $('.mobile-tab-btn[data-panel="food-log-panel"]').click();
        }
    });
}

function toggleFoodGroup(e) {
    // Prevent double-click from triggering two click events
    if (e.type === 'dblclick') {
        e.stopPropagation();
        e.preventDefault();
    }
    
    const groupHeader = $(this).closest('.group-header');
    const groupContainer = groupHeader.closest('.food-group');
    const groupItems = groupHeader.next('.group-items');
    const isExpanded = groupItems.is(':visible');
    
    if (isExpanded) {
        groupItems.slideUp(1);
        groupContainer.find('.toggle-group').text('+');
        groupContainer.addClass('collapsed-group');
    } else {
        groupItems.slideDown(1);
        groupContainer.find('.toggle-group').text('−');
        groupContainer.removeClass('collapsed-group');
    }
}

function handleEditGrams(e) {
    e.stopPropagation();
    
    const $button = $(this);
    const originalGrams = $button.text().replace('g', '');
    const id = $button.data('id');
    const key = $button.data('key');

    // Create styled input (mimics button)
    const $input = $(`<input type="number" 
                          class="edit-grams-input" 
                          value="${originalGrams}" 
                          min="0.1" step="0.1">`);

    // Replace button with input
    $button.replaceWith($input);
    $input.focus().select();

    // Handle save action
    function saveValue(newVal) {
        const date = $('#date-selector').val();
        if (!newVal || isNaN(newVal) || parseFloat(newVal) < 1) {
            newVal = 1;
        }

        // Recreate button
        const $newButton = $(`<button class="edit-grams" data-id="${id}" data-key="${key}">${newVal}g</button>`);
        $input.replaceWith($newButton);

        if (parseFloat(newVal) === 0) {
            // Delete item
            $.post('/delete_item', { 
                item_id: id,
                date: date
            }, response => {
                updateSessionDisplay(response.session, response.totals, response.breakdown);
                updateCalorieDifference();
            });
        } else {
            // Update grams
            $.post('/update_grams', {
                item_id: id,
                food_key: key,
                new_grams: newVal,
                date: date
            }, response => {
                updateSessionDisplay(response.session, response.totals, response.breakdown);
                updateCalorieDifference();
            });
        }
    }

    // Save on Enter
    $input.on('keydown', function(e) {
        if (e.key === 'Enter') {
            saveValue($input.val());
        } else if (e.key === 'Escape') {
            saveValue(originalGrams);
        }
    });

    // Save on blur
    $input.on('blur', function() {
        saveValue($input.val());
    });
}

function handleAdminFoodDelete(e) {
    e.stopPropagation();
    const foodId = $(this).data('id');
    
    if (!confirm('Are you sure you want to permanently delete this food from the database?')) {
        return;
    }
    
    // Show processing indicator
    const button = $(this);
    const originalHTML = button.html();
    button.html('<div class="spinner-delete"></div>');
    
    // Send delete request
    $.post('/delete_food', { 
        food_id: foodId 
    }, response => {
        if (response.success) {
            // Remove the food item from search results
            $(`a.food-item[data-id="${foodId}"]`).remove();
            
            // If we're viewing the food details, reset the form
            if (currentFood && currentFood.id === foodId) {
                resetFoodForm();
            }
        } else {
            alert('Error: ' + (response.error || 'Failed to delete food'));
        }
    }).fail(() => {
        alert('Failed to delete food. Please try again.');
    }).always(() => {
        button.html(originalHTML);
    });
}

function handleFoodItemDelete(e) {
    e.stopPropagation();
    const button = $(this);
    const itemId = button.data('id');
    const date = $('#date-selector').val();
    
    // Store original content
    const originalHTML = button.html();
    
    // Show spinner and disable button
    button.prop('disabled', true);
    button.html('<div class="spinner-delete"></div>');
    
    $.post('/delete_item', {
        item_id: itemId,
        date: date
    }, response => {
        updateSessionDisplay(response.session, response.totals, response.breakdown);
        updateCalorieDifference();
    }).fail(() => {
        // Revert button on failure
        button.html(originalHTML);
        button.prop('disabled', false);
        alert('Failed to delete item. Please try again.');
    });
}

function updateRealTimeBreakdownFromForm() {
    if (!currentFood) return;
    
    const grams = parseFloat($('#grams').val()) || 0;
    const factor = grams / 100;
    
    const updatedData = {
        calories: (currentFood.calories * factor),
        proteins: (currentFood.proteins * factor),
        carbs: (currentFood.carbs * factor),
        fats: (currentFood.fats * factor),
        saturated: (currentFood.saturated * factor),
        fiber: (currentFood.fiber * factor),
        sugars: (currentFood.sugars * factor),
        salt: (currentFood.salt * factor),
        grams: grams
    };
    
    updateRealTimeBreakdown(updatedData);
}

function updateRealTimeBreakdown(data) {
    if (!$('#rt-breakdown-container').is(':visible')) return;
    
    const formatValue = (value) => {
        if (value < 0.1) return value.toFixed(2);
        if (value < 1) return value.toFixed(1);
        return value.toFixed(0);
    };
    
    // Update values
    $('#rt-calories').text(formatValue(data.calories));
    $('#rt-proteins').text(formatValue(data.proteins) + 'g');
    $('#rt-carbs').text(formatValue(data.carbs) + 'g');
    $('#rt-fats').text(formatValue(data.fats) + 'g');
    $('#rt-grams').text(formatValue(data.grams) + 'g');
    
    // Mobile-specific font adjustments
    if ($(window).width() < 992) {
        const isOldPhone = window.innerWidth <= 360;
        const baseSize = isOldPhone ? 12 : 14;
        
        adjustMobileFontSize($('#rt-calories')[0], baseSize);
        adjustMobileFontSize($('#rt-proteins')[0], baseSize);
        adjustMobileFontSize($('#rt-carbs')[0], baseSize);
        adjustMobileFontSize($('#rt-fats')[0], baseSize);
    }
}

function resetFoodForm() {
    $('#food-search').val('');
    $('#grams').val('');
    $('#food-details').addClass('d-none');
    $('#portion-buttons').empty();
    currentFood = null;
    $('#rt-breakdown-container').addClass('d-none');
    loadTopFoods();
    initializeIcons();
}