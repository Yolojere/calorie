console.log("app-session.js started");
function clearSession() {
    if (!confirm('Are you sure you want to clear all items?')) return;
    
    $.post('/clear_session', {}, response => {
        updateSessionDisplay(response.session, response.totals, response.breakdown);
        updateCalorieDifference();
    });
}

function handleDateChange() {
    const date = $(this).val();
    currentSelectedDate = date; // Update the global date variable
    console.log("Date changed to:", date);
    
    $.post('/update_session', { date })
        .done(response => {
            console.log("Date change response:", response);
            if (response.session && response.totals && response.breakdown) {
                updateSessionDisplay(response.session, response.totals, response.breakdown);
                updateCalorieDifference();
                if (response.current_date_formatted) {
                    $('.card-header h6:contains("Food Log")').text(`Food Log (${response.current_date_formatted})`);
                }
            } else {
                console.error("Invalid response format from server");
            }
        })
        .fail((xhr, status, error) => {
            console.error('Date change failed:', error);
            alert('Failed to change date. Please try again.');
        });
}

function refreshDateSelector() {
    const currentDate = $('#date-selector').val();
    
    $.post('/update_session', { date: currentDate }, response => {
        updateSessionDisplay(response.session, response.totals, response.breakdown);
        updateCalorieDifference();
        $('.card-header h6:contains("Food Log")').text(`Food Log (${response.current_date_formatted})`);
    });
}

function updateSessionDisplay(session, totals, breakdown) {
    console.log("Updating session display:", totals, breakdown);
    updateNutritionGrid(totals);
    updateMobileNutrition(totals);
    updateCalorieDifference();
    
    // Remember collapsed states
    const collapseStates = {};
    $('.food-group').each(function() {
        const group = $(this).data('group');
        collapseStates[group] = $(this).hasClass('collapsed-group');
    });
    
    let logHtml = '';
    
    if (breakdown) {
        for (const group in breakdown) {
            const groupData = breakdown[group];
            logHtml += `
                <div class="food-group ${group}" data-group="${group}">
                    <div class="group-header d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <div class="group-icon">
                                ${group === 'breakfast' ? '<i class="fas fa-sun"></i>' : 
                                  group === 'lunch' ? '<i class="fas fa-utensils"></i>' : 
                                  group === 'dinner' ? '<i class="fas fa-moon"></i>' : 
                                  group === 'snack' ? '<i class="fas fa-apple-alt"></i>' : 
                                  '<i class="fas fa-question"></i>'}
                            </div>
                            <span class="group-title">${group.toUpperCase()}</span>
                        </div>
                        <div class="group-nutrition-container">
                            <div class="group-nutrition">
                                <div class="nutrition-value-xxs d-inline-block m-1 nutrition-calories" style="background-color: #ffffff;color: black;">
                                    <span>${groupData['calories'].toFixed(1)} kcal</span>
                                </div>
                                <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #b61336; color: black;">
                                    <span>${groupData['proteins'].toFixed(1)}g P</span>
                                </div>
                                <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #b61336;color: black;">
                                    <span>${groupData['carbs'].toFixed(1)}g C</span>
                                </div>
                                <div class="nutrition-value-xxs d-inline-block m-1" style="background-color: #b61336;color: black;">
                                    <span>${groupData['fats'].toFixed(1)}g F</span>
                                </div>
                            </div>
                            <button class="btn btn-sm toggle-group ms-1">−</button>
                        </div>
                    </div>
                    <ul class="group-items list-group list-group-flush">
            `;
            
            groupData['items'].forEach((item, index) => {
                logHtml += `
                    <li class="list-group-item bg-dark text-light d-flex justify-content-between align-items-center" data-id="${item.id}">
                        <div class="food-item-container">
                            <div>
                                <div class="d-flex align-items-center">
                                    <strong>${item.name}</strong>
                                </div>
                            </div>
                            <span class="edit-grams badge edit-grams-btn mx-1" 
                                data-id="${item.id}" 
                                data-key="${item.key}">
                                ${item.grams.toFixed(1)}g
                                    </span>
                        </div>
                        <div class="nutrition-and-actions">
                            <div class="nutrition-values-container d-flex">
                                <div class="nutrition-value-xxs d-inline-block mx-1 nutrition-calories" style="background-color: #ffffff;color: black;">
                                    <span>${item.calories.toFixed(1)} kcal</span>
                                </div>
                                <div class="nutrition-value-xxs d-inline-block mx-1" style="background-color: #b61336; color: black;">
                                    <span>${item.proteins.toFixed(1)}g P</span>
                                </div>
                                <div class="nutrition-value-xxs d-inline-block mx-1" style="background-color: #b61336;color: black;">
                                    <span>${item.carbs.toFixed(1)}g C</span>
                                </div>
                                <div class="nutrition-value-xxs d-inline-block mx-1" style="background-color: #b61336;color: black;">
                                    <span>${item.fats.toFixed(1)}g F</span>
                                </div>
                            </div>
                            <button class="btn delete-item" data-id="${item.id}">
                                <i class="fa-solid fa-circle-xmark"></i>
                            </button>
                        </div>
                    </li>
                `;
            });
            
            logHtml += `
                    </ul>
                </div>
            `;
        }
    }
    
    if (logHtml === '') {
        logHtml = '<div class="empty-state">No food logged yet</div>';
    }
    
    $('#food-log').html(logHtml);
    
    // Auto-scroll on mobile if items exist
    if ($(window).width() < 992 && session.length > 0) {
        setTimeout(() => {
            const lastItem = $('.list-group-item').last();
            if (lastItem.length) {
                $('#food-log').animate({
                    scrollTop: lastItem.offset().top - 100
                }, 500);
            }
        }, 300);
    }

    // Reapply collapse states
    Object.keys(collapseStates).forEach(group => {
        if (collapseStates[group]) {
            $(`.food-group[data-group="${group}"]`).addClass('collapsed-group');
            $(`.food-group[data-group="${group}"] .group-items`).hide();
            $(`.food-group[data-group="${group}"] .toggle-group`).text('+');
        }
    });
}

function updateNutritionGrid(totals) {
    const safeParse = (value) => {
        const num = parseFloat(value) || 0;
        if (num < 0.1) return num.toFixed(2);
        if (num < 1) return num.toFixed(1);
        return num.toFixed(0);
    };
    
    $('#grid-calories').text(safeParse(totals.calories));
    $('#grid-proteins').text(safeParse(totals.proteins) + 'g');
    $('#grid-carbs').text(safeParse(totals.carbs) + 'g');
    $('#grid-fats').text(safeParse(totals.fats) + 'g');
    $('#grid-saturated').text(safeParse(totals.saturated) + 'g');
    $('#grid-sugars').text(safeParse(totals.sugars) + 'g');
    $('#grid-fiber').text(safeParse(totals.fiber) + 'g');
    $('#grid-salt').text(safeParse(totals.salt) + 'g');
}

function updateCalorieDifference() {
    const tdee = CURRENT_TDEE;
    const loggedCalories = parseFloat($('#grid-calories').text()) || 0;
    const difference = tdee - loggedCalories;
    const absDiff = Math.abs(difference);
    // Update the calorie difference display
    $('#calorie-difference').text(absDiff.toFixed(0));
    $('#calorie-difference-mobile').text(absDiff.toFixed(0));

    // Determine status and set appropriate class
    let status, statusClass;
    if (absDiff <= 50) {
        status = "maintaining";
        statusClass = "status-maintain";
    } else if (difference > 0) {
        status = "calories left";
        statusClass = "status-loss";
    } else {
        status = "calories over";
        statusClass = "status-gain";
    }

    // Update status text and class
    $('#calorie-status, #calorie-status-mobile').text(status)
        .removeClass('status-maintain status-loss status-gain')
        .addClass(statusClass);
}
