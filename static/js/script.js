$(document).ready(function() {
    let currentFood = null;
    const editModal = new bootstrap.Modal(document.getElementById('editModal'));
    
    // Food search functionality
    $('#food-search').on('input', function() {
        const query = $(this).val().trim();
        if (query.length < 2) {
            $('#search-results').empty();
            return;
        }
        
        $.post('/search_foods', { query: query }, function(data) {
            let resultsHtml = '';
            if (data.length > 0) {
                resultsHtml = '<div class="list-group">';
                data.forEach(food => {
                    resultsHtml += `
                        <a class="list-group-item list-group-item-action food-item small" 
                           data-id="${food.id}">
                            ${food.name} - ${food.calories} cal
                        </a>
                    `;
                });
                resultsHtml += '</div>';
            } else {
                resultsHtml = '<div class="text-center p-2 small">No results found</div>';
            }
            $('#search-results').html(resultsHtml);
        });
    });

    // Food selection
    $(document).on('click', '.food-item', function() {
        const foodId = $(this).data('id');
        $('#food-search').val($(this).text().split(' - ')[0]);
        $('#search-results').empty();
        
        $.post('/get_food_details', { 
            food_id: foodId,
            unit_type: 'grams',
            units: 100
        }, function(data) {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            // Store current food
            currentFood = data;
            
            // Show food details section
            $('#food-details').removeClass('d-none');
            $('#units').val(100);
            $('#unit-type').val('grams');
            $('#add-food').data('id', foodId);
            
            // Update unit type dropdown with gram values
            updateUnitTypeDropdown(data);
            
            // Update real-time breakdown
            updateRealTimeBreakdown(data);
        });
    });

    // Update unit type dropdown with gram values
    function updateUnitTypeDropdown(food) {
        const unitTypeSelect = $('#unit-type');
        unitTypeSelect.empty();
        
        // Always add grams option
        unitTypeSelect.append($('<option>', {
            value: 'grams',
            text: 'Grams'
        }));
        
        // Add other options if they exist
        if (food.serving_size) {
            unitTypeSelect.append($('<option>', {
                value: 'serving',
                text: `Serving (${food.serving_size}g)`
            }));
        }
        if (food.half_size) {
            unitTypeSelect.append($('<option>', {
                value: 'half',
                text: `Half (${food.half_size}g)`
            }));
        }
        if (food.entire_size) {
            unitTypeSelect.append($('<option>', {
                value: 'entire',
                text: `Entire (${food.entire_size}g)`
            }));
        }
    }

    // Update real-time breakdown when units change
    $('#units, #unit-type').on('change input', function() {
        if (!currentFood) return;
        
        const units = parseFloat($('#units').val()) || 0;
        const unitType = $('#unit-type').val();
        
        // Calculate equivalent grams
        let grams = units;
        if (unitType === 'serving' && currentFood.serving_size) {
            grams = units * currentFood.serving_size;
        } else if (unitType === 'half' && currentFood.half_size) {
            grams = units * currentFood.half_size;
        } else if (unitType === 'entire' && currentFood.entire_size) {
            grams = units * currentFood.entire_size;
        }
        
        // Calculate nutrition based on grams
        const factor = grams / 100;
        const updatedData = {
            calories: currentFood.calories * factor,
            proteins: currentFood.proteins * factor,
            carbs: currentFood.carbs * factor,
            fats: currentFood.fats * factor,
            sugars: currentFood.sugars * factor,
            fiber: currentFood.fiber * factor,
            grams: grams
        };
        
        updateRealTimeBreakdown(updatedData);
    });

    // Add food to log
    $('#add-food').click(function() {
        const foodId = $(this).data('id');
        const units = $('#units').val();
        const unitType = $('#unit-type').val();
        const mealGroup = $('#meal-group').val();
        
        $.post('/log_food', {
            food_id: foodId,
            unit_type: unitType,
            units: units,
            meal_group: mealGroup
        }, function(response) {
            updateSessionDisplay(response.session, response.totals);
            resetFoodForm();
        });
    });

    // Edit food item
    $(document).on('click', '.edit-item', function() {
        const index = $(this).closest('.list-group-item').data('index');
        const item = $(this).closest('.list-group-item').data('original');
        
        if (!item) return;
        
        // Populate modal with item data
        $('#edit-item-index').val(index);
        $('#edit-units').val(item.units);
        
        // Populate unit type dropdown
        const unitTypeSelect = $('#edit-unit-type');
        unitTypeSelect.empty();
        
        unitTypeSelect.append($('<option>', {
            value: 'grams',
            text: 'Grams',
            selected: item.unit_type === 'grams'
        }));
        
        if (item.serving_size) {
            unitTypeSelect.append($('<option>', {
                value: 'serving',
                text: `Serving (${item.serving_size}g)`,
                selected: item.unit_type === 'serving'
            }));
        }
        if (item.half_size) {
            unitTypeSelect.append($('<option>', {
                value: 'half',
                text: `Half (${item.half_size}g)`,
                selected: item.unit_type === 'half'
            }));
        }
        if (item.entire_size) {
            unitTypeSelect.append($('<option>', {
                value: 'entire',
                text: `Entire (${item.entire_size}g)`,
                selected: item.unit_type === 'entire'
            }));
        }
        
        editModal.show();
    });

    // Save edited item
    $('#save-edit').click(function() {
        const index = $('#edit-item-index').val();
        const units = $('#edit-units').val();
        const unitType = $('#edit-unit-type').val();
        
        $.post('/update_item', {
            item_index: index,
            units: units,
            unit_type: unitType
        }, function(response) {
            updateSessionDisplay(response.session, response.totals);
            editModal.hide();
        });
    });

    // Delete food item
    $(document).on('click', '.delete-item', function(e) {
        e.stopPropagation();
        const index = $(this).data('index');
        $.post('/delete_item', { item_index: index }, function(response) {
            updateSessionDisplay(response.session, response.totals);
        });
    });

    // Clear session
    $('#clear-session').click(function() {
        if (!confirm('Are you sure you want to clear all items?')) return;
        
        $.post('/clear_session', {}, function(response) {
            updateSessionDisplay(response.session, response.totals);
        });
    });

    // Change day
    $('#day-selector').change(function() {
        const day = $(this).val();
        $.post('/update_session', { day: day }, function(response) {
            updateSessionDisplay(response.session, response.totals);
            $('.card-header h6:contains("Food Log")').text(`Food Log (${day})`);
        });
    });

    // Move session to another day
    $('#move-day').click(function() {
        const targetDay = $('#day-selector').val();
        if (targetDay === CURRENT_DAY) {
            alert('Select a different day');
            return;
        }
        
        if (!confirm(`Move all items to ${targetDay}?`)) return;
        
        $.post('/move_to_day', {
            source_day: CURRENT_DAY,
            target_day: targetDay
        }, function() {
            alert(`Session moved to ${targetDay}`);
            // Refresh current session
            $.post('/update_session', { day: CURRENT_DAY }, updateSessionDisplay);
        });
    });

    // Helper functions
    function updateRealTimeBreakdown(data) {
        if (!data || !data.calories) {
            $('#rt-breakdown').addClass('d-none');
            $('#rt-breakdown-placeholder').removeClass('d-none');
            return;
        }
        
        $('#rt-breakdown-placeholder').addClass('d-none');
        $('#rt-breakdown').removeClass('d-none');
        
        $('#rt-calories').text(data.calories.toFixed(1));
        $('#rt-proteins').text(data.proteins.toFixed(1) + 'g');
        $('#rt-carbs').text(data.carbs.toFixed(1) + 'g');
        $('#rt-fats').text(data.fats.toFixed(1) + 'g');
        $('#rt-sugars').text(data.sugars?.toFixed(1) || '0.0' + 'g');
        $('#rt-fiber').text(data.fiber?.toFixed(1) || '0.0' + 'g');
        $('#rt-grams').text(data.grams.toFixed(1) + 'g');
    }
    
    function updateSessionDisplay(session, totals) {
        // Update food log
        let logHtml = '';
        if (session.length > 0) {
            session.forEach((item, index) => {
                // Store original item data for editing
                const originalItem = JSON.stringify(item);
                
                logHtml += `
                    <li class="list-group-item bg-dark text-light d-flex justify-content-between align-items-center py-1" 
                        data-index="${index}" data-original='${originalItem}'>
                        <div class="d-flex align-items-center">
                            <button class="btn btn-sm me-1 edit-item" style="background-color: #ff4444; color: black;">✏️</button>
                            <div>
                                <div class="d-flex align-items-center">
                                    <strong class="small">${item.name}</strong>
                                    <span class="badge bg-secondary ms-2 small">${item.group}</span>
                                </div>
                                <div class="text-muted x-small">
                                    ${item.units} ${item.unit_type} (${item.grams.toFixed(1)}g)
                                </div>
                            </div>
                        </div>
                        <div class="d-flex">
                            <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #0d6efd;">
                                <span class="value">${item.calories.toFixed(1)}</span>
                                <span class="label">kcal</span>
                            </div>
                            <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #ffc107; color: black;">
                                <span class="value">${item.proteins.toFixed(1)}g</span>
                                <span class="label">P</span>
                            </div>
                            <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #dc3545;">
                                <span class="value">${item.carbs.toFixed(1)}g</span>
                                <span class="label">C</span>
                            </div>
                            <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #6c757d;">
                                <span class="value">${item.fats.toFixed(1)}g</span>
                                <span class="label">F</span>
                            </div>
                            <button class="btn btn-sm delete-item ms-1" style="background-color: #ff4444; color: black;" data-index="${index}">X</button>
                        </div>
                    </li>
                `;
            });
        } else {
            logHtml = '<li class="list-group-item bg-dark text-light text-center text-muted py-3 small">No food logged yet</li>';
        }
        $('#food-log').html(logHtml);
        
        // Update nutrition summary
        $('.nutrition-value-sm .value').eq(0).text(totals.calories.toFixed(1));
        $('.nutrition-value-sm .value').eq(1).text(totals.proteins.toFixed(1));
        $('.nutrition-value-sm .value').eq(2).text(totals.carbs.toFixed(1));
        $('.nutrition-value-sm .value').eq(3).text(totals.fats.toFixed(1));
        $('.nutrition-value-xxs .value').eq(0).text(totals.sugars.toFixed(1));
        $('.nutrition-value-xxs .value').eq(1).text(totals.fiber.toFixed(1));
        $('.nutrition-value-xxs .value').eq(2).text(totals.salt.toFixed(1));
    }
    
    function resetFoodForm() {
        $('#food-search').val('');
        $('#units').val('1');
        $('#unit-type').val('grams');
        $('#food-details').addClass('d-none');
        currentFood = null;
        $('#rt-breakdown').addClass('d-none');
        $('#rt-breakdown-placeholder').removeClass('d-none');
    }
});