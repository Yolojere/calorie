console.log("app-search.js started");
function handleFoodSearch() {
    const query = $(this).val().trim();
    
    if (query.length === 0) {
        loadTopFoods();
        return;
    }
    
    $.post('/search_foods', { query }, data => {
        let resultsHtml = '';
        
        if (data.length > 0) {
            resultsHtml = '<div class="list-group">';
            data.forEach(food => resultsHtml += createFoodItemHtml(food));
            resultsHtml += '</div>';
        } else {
            resultsHtml = '<div class="text-center p-2 small">No results found</div>';
        }
        
        $('#search-results').html(resultsHtml);
    });
}

function clearSearch() {
    $('#food-search').val('');
    loadTopFoods();
    $('#food-details').addClass('d-none');
    currentFood = null;
    $('#rt-breakdown-container').addClass('d-none');
}

function loadTopFoods() {
    $.post('/search_foods', { query: '' }, data => {
        let resultsHtml = '';
        if (data.length > 0) {
            resultsHtml = '<div class="list-group">';
            data.forEach(food => resultsHtml += createFoodItemHtml(food));
            resultsHtml += '</div>';
        } else {
            resultsHtml = '<div class="text-center p-2 small">No foods available</div>';
        }
        $('#search-results').html(resultsHtml);
    });
}

function createFoodItemHtml(food) {
    const displayCalories = formatCalories(food.calories) + ' kcal';
    
    return `
        <a class="list-group-item list-group-item-action food-item small text-start" 
           data-id="${food.id}" 
           data-serving="${food.serving_size || ''}"
           data-half="${food.half_size || ''}"
           data-entire="${food.entire_size || ''}">
            <div class="d-flex justify-content-between align-items-center">
                <span class="food-name">${food.name}</span>
                <div>
                    <span class="calorie-badge">${displayCalories}</span>
                    <button class="delete-food-btn" data-id="${food.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </a>
    `;
}

function handleFoodItemClick() {
    const foodId = $(this).data('id');
    const servingSize = $(this).data('serving');
    const halfSize = $(this).data('half');
    const entireSize = $(this).data('entire');
    
    $('#food-search').val($(this).find('.food-name').text().trim());
    $('#search-results').empty();
    
    // Fetch actual food data from server
    $.post('/get_food_details', { 
        food_id: foodId 
    }, function(foodData) {
        if (foodData && foodData.success) {
            // Store current food with actual nutrition data
            currentFood = {
                id: foodId,
                serving_size: servingSize,
                half_size: halfSize,
                entire_size: entireSize,
                calories: parseFloat(foodData.calories) || 0,
                proteins: parseFloat(foodData.proteins) || 0,
                carbs: parseFloat(foodData.carbs) || 0,
                fats: parseFloat(foodData.fats) || 0,
                saturated: parseFloat(foodData.saturated) || 0,
                fiber: parseFloat(foodData.fiber) || 0,
                sugars: parseFloat(foodData.sugars) || 0,
                salt: parseFloat(foodData.salt) || 0
            };
            
            $('#food-details').removeClass('d-none');
            $('#grams').val(""); // Default to 100g
            $('#add-food').data('id', foodId);
            
            updatePortionButtons(currentFood);
            $('#rt-breakdown-container').removeClass('d-none');
            updateRealTimeBreakdownFromForm();
            
            setTimeout(function() {
                $('#grams').trigger('focus').trigger('select');
            }, 100);
        } else {
            alert('Error loading food details');
        }
    }).fail(function() {
        alert('Failed to fetch food details');
    });
}