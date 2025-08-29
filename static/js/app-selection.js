console.log("app-selection.js started");
function handleItemSelection(e) {
    if ($(e.target).is('button') || $(e.target).is('.edit-grams')) {
        return;
    }
    
    const itemId = $(this).data('id');
    const isSelected = $(this).hasClass('selected');
    
    if (isSelected) {
        $(this).removeClass('selected');
        selectedItems = selectedItems.filter(id => id !== itemId);
    } else {
        $(this).addClass('selected');
        selectedItems.push(itemId);
    }
    
    // Enable/disable buttons based on selection
    $('#move-items, #move-items-mobile').prop('disabled', selectedItems.length === 0);
    
    // Show recipe button if at least 2 items selected
    $('#create-recipe').toggleClass('d-none', selectedItems.length < 2);
    $('#create-recipe').prop('disabled', selectedItems.length < 2);
    updateTemplateButtonState();
}

function updateTemplateButtonState() {
    $('#save-template-btn').prop('disabled', selectedItems.length === 0);
}

function showMoveItemsModal() {
    $('#moveItemsModal').modal('show');
}

function handleActionSelection() {
    selectedAction = $(this).attr('id') === 'action-move' ? 'move' : 'copy';
    
    if (selectedAction === 'move') {
        $('#action-move').addClass('active').addClass('btn-danger').removeClass('btn-outline-danger');
        $('#action-copy').removeClass('active').removeClass('btn-success').addClass('btn-outline-success');
    } else {
        $('#action-copy').addClass('active').addClass('btn-success').removeClass('btn-outline-success');
        $('#action-move').removeClass('active').removeClass('btn-danger').addClass('btn-outline-danger');
    }
}

function confirmMoveCopyAction() {
    const targetDate = $('#target-date').val();
    const targetGroup = $('#target-group').val();
    const currentDate = currentSelectedDate; // Use the global date variable
    
    $.post('/' + selectedAction + '_items', {
        date: currentDate,
        item_ids: JSON.stringify(selectedItems),
        new_group: targetGroup,
        target_date: targetDate
    }, response => {
        selectedItems = [];
        $('#move-items, #move-items-mobile').prop('disabled', true);
        $('#create-recipe').addClass('d-none').prop('disabled', true);
        $('#moveItemsModal').modal('hide');
        
        updateSessionDisplay(response.session, response.totals, response.breakdown);
        refreshDateSelector();
        updateCalorieDifference();
    }).fail(function(xhr, status, error) {
        console.error('Move/Copy error:', error);
        alert('Failed to move/copy items. Please try again.');
    });
}

function showRecipeModal() {
    selectedItemsForRecipe = selectedItems.map(itemId => itemId);
    
    $('#recipe-confirm').removeClass('d-none');
    $('#recipe-name-input').addClass('d-none');
    $('#recipe-yes').removeClass('d-none');
    $('#recipe-save').addClass('d-none');
    recipeModal.show();
}

function showRecipeNameInput() {
    $('#recipe-confirm').addClass('d-none');
    $('#recipe-name-input').removeClass('d-none');
    $('#recipe-yes').addClass('d-none');
    $('#recipe-save').removeClass('d-none');
}

function saveRecipe() {
    const recipeName = $('#recipe-name').val().trim();
    const date = $('#date-selector').val();
    
    if (!recipeName) {
        alert('Please enter a recipe name');
        return;
    }
    
    $.post('/save_recipe', {
        recipe_name: recipeName,
        selected_ids: JSON.stringify(selectedItemsForRecipe),
        date: date
    }, response => {
        if (response.success) {
            alert('Recipe saved successfully!');
            recipeModal.hide();
            resetRecipeSelection();
            loadTopFoods();
        } else {
            alert('Error: ' + (response.error || 'Failed to save recipe'));
        }
    }).fail(xhr => {
        alert('Error: ' + (xhr.responseJSON?.error || 'Failed to save recipe'));
    });
}

function resetRecipeSelection() {
    selectedItems = [];
    selectedItemsForRecipe = [];
    $('.list-group-item.selected').removeClass('selected');
    $('#move-items').prop('disabled', true);
    $('#create-recipe').addClass('d-none').prop('disabled', true);
}

function showSaveTemplateModal() {
    if (selectedItems.length === 0) return;
    $('#saveTemplateModal').modal('show');
}

function saveTemplate() {
    const templateName = $('#template-name').val().trim();
    if (!templateName) {
        alert('Please enter a template name');
        return;
    }

    // Get the current grams and food keys for each selected item
    const itemsWithData = [];
    selectedItems.forEach(itemId => {
        const itemElement = $(`.list-group-item[data-id="${itemId}"]`);
        const grams = parseFloat(itemElement.find('.edit-grams').text().replace('g', ''));
        const foodKey = itemElement.find('.edit-grams').data('key');
        
        itemsWithData.push({
            id: itemId,
            food_key: foodKey,
            grams: grams
        });
    });

    if (itemsWithData.length === 0) {
        alert('No valid items selected for template');
        return;
    }

    console.log(`Saving template "${templateName}" with ${itemsWithData.length} items`);
    
    $.post(SAVE_TEMPLATE_URL, {
        name: templateName,
        items: JSON.stringify(itemsWithData)
    }, response => {
        if (response.success) {
            alert('Template saved successfully!');
            $('#saveTemplateModal').modal('hide');
            $('#template-name').val('');
        } else {
            alert('Error: ' + (response.error || 'Failed to save template'));
        }
    }).fail((xhr, status, error) => {
        console.error('Template error:', error);
        alert('Failed to save template. Please check your connection and try again.');
    });
}

function showApplyTemplateModal() {
    loadTemplates();
    $('#applyTemplateModal').modal('show');
}

function applyTemplate() {
    const templateId = $('#template-select').val();
    const mealGroup = $('#template-meal-group').val();
    const date = currentSelectedDate; // Use the global date variable
    
    if (!templateId) return;
    
    $.post(APPLY_TEMPLATE_URL, {
        template_id: templateId,
        meal_group: mealGroup,
        date: date // Ensure date is always sent
    }, response => {
        if (response.success) {
            updateSessionDisplay(response.session, response.totals, response.breakdown);
            updateCalorieDifference();
            $('#applyTemplateModal').modal('hide');
        } else {
            alert('Error: ' + (response.error || 'Failed to apply template'));
        }
    }).fail(function(xhr, status, error) {
        console.error('Template application error:', error);
        alert('Failed to apply template. Please try again.');
    });
}

function loadTemplates() {
    $.get('/get_templates_food', templates => {
        const select = $('#template-select');
        select.empty();
        
        if (templates.length === 0) {
            select.append('<option value="">No templates available</option>');
            $('#confirm-apply-template').prop('disabled', true);
        } else {
            templates.forEach(template => {
                select.append(`<option value="${template.id}">${template.name}</option>`);
            });
            $('#confirm-apply-template').prop('disabled', false);
        }
    });
}