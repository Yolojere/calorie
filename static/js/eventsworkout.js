// File: events.js
function setupEventListeners() {
    // Setup muscle group change listener
    $("#muscle-group-select, #muscle-group-select-mobile").change(renderExerciseOptions);
    
    // Save set listeners
    $("#save-set-btn").click(() => saveSet(false));
    $("#save-set-btn-mobile").click(() => saveSet(true));
    
    // Add exercise
    $(document).on("click", "#save-exercise-btn", addExercise);
    
    // Week navigation
    $("#prev-week-btn").click(() => navigateWeek('prev'));
    $("#next-week-btn").click(() => navigateWeek('next'));
    
    // Enter key submit
    $("#comments-input, #comments-input-mobile").keypress(function(e) {
        if (e.which === 13) {
            saveSet($(this).attr('id') === 'comments-input-mobile');
        }
    });
    // Template handling
    $("#save-template-btn").click(saveTemplate);
    $("#apply-template-btn").click(function() {
        const templateId = $(this).data('template-id');
        applyTemplate(templateId);
        const modal = bootstrap.Modal.getInstance(document.getElementById('templatePreviewModal'));
        if (modal) modal.hide();
    });
    $(document).on("click", ".template-item", function(e) {
        e.preventDefault();
        previewTemplate($(this).data('id'));
    });

    // Copy workout
$("#copy-workout-btn, #copy-workout-mobile-btn").click(function() {
    // Use currentSelectedDate instead of DOM element
    const sourceDate = currentSelectedDate; // ✅ Reliable source
    
    if (!sourceDate) {
        alert("Valitse ensin treeni kopioitavaksi");
        return;
    }
    
    $("#copyWorkoutModal").data("source-date", sourceDate);
    populateDateOptions();
    $("#copyWorkoutModal").modal("show");
});
    
    $(document).on("click", ".date-option", function() {
        copyWorkoutToDate($(this).data("date"));
    });
    
    // Admin-only events
    if (typeof current_user_role !== 'undefined' && current_user_role === 'admin') {
        $("#save-template-btn").click(saveTemplate);
        $("#save-template-mobile-btn").click(saveTemplate);
    }
}
function openCopyWorkoutModal() {
    hideWorkoutResults();
    const activeDate = currentSelectedDate;
    if (!activeDate) {
        alert("Valitse ensin treeni kopioitavaksi");
        return;
    }
    
    // Store source date consistently
    $("#copyWorkoutModal").data("source-date", activeDate);
    
    populateDateOptions();
    $("#copyWorkoutModal").modal("show");
}
function setupRirDropdowns() {
    // Hide dropdown when clicking elsewhere
    $(document).click(function() {
        $('.rir-options').hide();
        $('.complete-exercise-options').hide();
    });
    
    // RiR badge click
    $(document).on('click', '.rir-badge', function(e) {
        e.stopPropagation();
        // Hide any other open dropdowns
        $('.rir-options').hide();
        $('.complete-exercise-options').hide();
        
        // Show this dropdown
        $(this).siblings('.rir-options').toggle();
    });
    
    // RiR option selection
    $(document).on('click', '.rir-option', function(e) {
        e.stopPropagation();
        const value = $(this).data('value');
        const badge = $(this).closest('.rir-dropdown').find('.rir-badge');
        const setId = $(this).closest('.set-row').data('set-id');
        
        // Update badge text
        if (value === 'Failure') {
            badge.text('Failure');
        } else {
            badge.text(value + ' RiR');
        }
        
        // Hide dropdown
        $(this).closest('.rir-options').hide();
        
        // Update the RiR value in the database
        updateRir(setId, value);
    });
}


function setupExerciseCompletion() {
    // Prevent double-binding
    $(document).off('.complete');

    // Dropdown toggle
    $(document).on('click.complete', '.complete-exercise-icon', function(e) {
        e.stopPropagation(); // only stop bubbling, don't preventDefault

        const $dropdown = $(this).siblings('.complete-exercise-options');

        // Hide other dropdowns
        $('.complete-exercise-options').not($dropdown).hide();

        // Toggle this dropdown
        $dropdown.toggle();

        if (!$dropdown.is(':visible')) return;

        // Position dropdown (your existing logic)
        const $container = $(this).closest('.card, .grid-panel');
        const containerTop = $container.offset().top;
        const containerBottom = containerTop + $container.outerHeight();
        const iconOffset = $(this).offset().top;
        const iconHeight = $(this).outerHeight();
        const dropdownHeight = $dropdown.outerHeight();

        const spaceBelow = containerBottom - (iconOffset + iconHeight);
        const spaceAbove = iconOffset - containerTop;

        if (spaceBelow >= dropdownHeight) {
            $dropdown.css({ top: '100%', bottom: 'auto' });
        } else if (spaceAbove >= dropdownHeight) {
            $dropdown.css({ top: 'auto', bottom: '100%' });
        } else {
            $dropdown.css({ top: '100%', bottom: 'auto', maxHeight: spaceBelow, overflowY: 'auto' });
        }
    });

    // Option selection
    $(document).on('click.complete', '.complete-option', function(e) {
        e.stopPropagation();
        const value = $(this).data('value');
        const exerciseId = $(this).closest('.exercise').data('exercise-id');
        const groupName = $(this).closest('.workout-group').data('group');
        const date = $(".workout-date.active").data("date");

        if (value === 'yes') markExerciseCompleted(exerciseId, groupName, date);
        else markExerciseNotCompleted(exerciseId, groupName, date);

        $(this).closest('.complete-exercise-options').hide();
    });

    // Clicking outside closes dropdowns
    $(document).on('click.complete', function() {
        $('.complete-exercise-options').hide();
    });
}

// Handle resume from background / tab focus
document.addEventListener("visibilitychange", function() {
    if (!document.hidden) {
        $('.complete-exercise-options').hide(); // reset dropdowns
        setupExerciseCompletion();              // rebind handlers
    }
});


function markExerciseCompleted(exerciseId, groupName, date) {
    // Store completed state
    if (!completedExercises[date]) completedExercises[date] = {};
    completedExercises[date][exerciseId] = true;

    // Update UI
    const $exercise = $(`.exercise[data-exercise-id="${exerciseId}"]`);
    $exercise.find('.exercise-header').addClass('completed');
    $exercise.find('.complete-exercise-icon i').addClass('completed');

    // Move to end of group
    const $groupItems = $exercise.closest('.group-items');
    $exercise.detach().appendTo($groupItems);

    // Save state
    saveCollapseState();

    // Collapse the exercise if not already collapsed
    const exerciseCollapsed = collapseState.exercises[date] && collapseState.exercises[date][exerciseId];
    if (!exerciseCollapsed) {
        $exercise.find('.toggle-exercise').click();
    }

}


function markExerciseNotCompleted(exerciseId, groupName, date) {
    // Remove completed state
    if (completedExercises[date] && completedExercises[date][exerciseId]) {
        delete completedExercises[date][exerciseId];
    }

    // Update UI
    const $exercise = $(`.exercise[data-exercise-id="${exerciseId}"]`);
    $exercise.find('.exercise-header').removeClass('completed');
    $exercise.find('.complete-exercise-icon i').removeClass('completed');

    // Move back to original position (first in group)
    const $groupItems = $exercise.closest('.group-items');
    const $firstExercise = $groupItems.find('.exercise').first();
    if ($firstExercise.length && !$firstExercise.is($exercise)) {
        $exercise.detach().insertBefore($firstExercise);
    }

    // Save state
    saveCollapseState();

    // --- AJAX call removed ---
}

function setupCommentTooltips() {
    // Comment icon click
    $(document).on('click', '.comment-icon', function(e) {
    e.stopPropagation();
    activeCommentIcon = $(this); // store the clicked icon

    const tooltip = $('#comment-tooltip');
    const textarea = tooltip.find('textarea');

    // Pre-fill textarea if comment exists
    textarea.val(activeCommentIcon.data('comment') || '');

    tooltip.css({
        top: $(this).offset().top + 20,
        left: $(this).offset().left
    }).show();
});

// Save comment
$('#save-comment-btn').click(function() {
    if (!activeCommentIcon) return;

    const tooltip = $('#comment-tooltip');
    const textarea = tooltip.find('textarea');
    const comment = textarea.val();

    if (comment) {
        activeCommentIcon.removeClass('far').addClass('fas');
        activeCommentIcon.data('comment', comment);
    } else {
        activeCommentIcon.removeClass('fas').addClass('far');
        activeCommentIcon.data('comment', '');
    }

    tooltip.hide();
    activeCommentIcon = null; // reset
});

    // Hide comment tooltip when clicking outside
    $(document).click(function(e) {
        if (!$(e.target).closest('.comment-icon, #comment-tooltip').length) {
            $('#comment-tooltip').hide();
        }
    });
    
    // Prevent comment tooltip from closing when clicking inside it
    $('#comment-tooltip').click(function(e) {
        e.stopPropagation();
    });
}

// ===== EVENT HANDLERS =====
$(document).on('blur', '.set-input', handleSetUpdate);
$(document).on('keyup', '.set-input', function(e) {
    if (e.key === 'Enter') {
        handleSetUpdate.call(this);
    }
});

$(document).on("click", ".workout-table .delete-item", function() {
    // Now only applies to delete buttons INSIDE workout tables
    const $button = $(this);
    const row = $button.closest("tr");
    const setId = row.data("set-id");
    
    if (!setId) return; // Skip if no set ID
    
    $button.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i>');
    deleteSet(setId, $button);
});
// ✅ CARDIO-SPECIFIC delete handler
$(document).on("click", ".cardio-delete-btn", function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const sessionId = parseInt($(this).data('session-id'));
    
    if (!sessionId) {
        console.error('No session ID found on cardio delete button');
        return;
    }
    
    console.log('Deleting cardio session:', sessionId);
    deleteCardioSession(sessionId);
});
function recalcSessionTotals() {
    let totalSets = 0;
    let totalVolume = 0;

    $(".workout-group").each((_, groupEl) => {
        const $group = $(groupEl);
        $group.find(".exercise-sets tr.set-row").each((_, row) => {
            const $row = $(row);
            const reps = parseFloat($row.find(".set-reps").val()) || 0;
            const weight = parseFloat($row.find(".set-weight").val()) || 0;
            totalSets += 1;
            totalVolume += reps * weight;
        });
    });

    $("#session-total-sets").text(`${totalSets} Sarjaa`);
    $("#session-total-volume").text(`${totalVolume.toFixed(1)} kg`);
}
function recalcGroupTotals($group) {
    let totalSets = 0;
    let totalVolume = 0;

    $group.find(".exercise").each((_, exerciseEl) => {
        const $exercise = $(exerciseEl);
        $exercise.find(".exercise-sets tr.set-row").each((_, row) => {
            const $row = $(row);
            const reps = parseFloat($row.find(".set-reps").val()) || 0;
            const weight = parseFloat($row.find(".set-weight").val()) || 0;
            totalSets += 1;
            totalVolume += reps * weight;
        });
    });

    $group.find(".group-summary .summary-item").eq(0).text(`${totalSets} Sarjaa`);
    $group.find(".group-summary .summary-item").eq(1).text(`${totalVolume.toFixed(1)} kg`);
}
function updateExerciseHeader($exercise) {
    let exerciseSets = 0;
    let exerciseVolume = 0;

    $exercise.find(".exercise-sets tr.set-row").each((_, row) => {
        const $row = $(row);
        const reps = parseFloat($row.find(".set-reps").val()) || 0;
        const weight = parseFloat($row.find(".set-weight").val()) || 0;
        exerciseSets += 1;
        exerciseVolume += reps * weight;
    });

    $exercise.find(".exercise-summary-text").text(`${exerciseSets} Sarjaa, ${exerciseVolume.toFixed(1)} kg`);
}
function handleSetUpdate() {
    // 🟢 START TIMER ON SET EDIT
    startWorkoutTimer();

    const row = $(this).closest("tr");
    const repsInput = row.find(".set-reps");
    const weightInput = row.find(".set-weight");

    lastFocusedSetId = row.data("set-id");
    lastFocusedInputType = $(this).hasClass('set-reps') ? 'reps' : 'weight';

    const repsVal = repsInput.val().trim();
    const weightVal = weightInput.val().trim();

    if (!repsVal || !weightVal || isNaN(repsVal) || isNaN(weightVal)) {
        revertToOriginal();
        return;
    }

    const setId = row.data("set-id");
    const reps = parseFloat(repsVal);
    const weight = parseFloat(weightVal);
    const date = $(".workout-date.active").data("date");

    if (reps != repsInput.data("original") || weight != weightInput.data("original")) {
        const volumeDisplay = row.find(".volume-display");
        volumeDisplay.html('<i class="fas fa-spinner fa-spin"></i>');

        // Optimistic UI update for volume
        const newVolume = (reps * weight).toFixed(1);
        setTimeout(() => {
            volumeDisplay.text(newVolume);
            row.addClass("set-updated");
        }, 300);

        $.post("/workout/update_set", {
            set_id: setId,
            reps: reps,
            weight: weight
        }, function(response) {
            if (response.success) {
                repsInput.data("original", reps);
                weightInput.data("original", weight);

                // ✅ Update exercise header totals dynamically
                updateExerciseHeader(row.closest(".exercise"));

                // ✅ Update group totals dynamically
                const $group = row.closest(".workout-group");
                recalcGroupTotals($group);

                // ✅ Update overall session/workout totals
                recalcSessionTotals();
            } else {
                alert("Error: " + response.error);
                revertToOriginal();
            }
        }).fail(function() {
            alert("Network error. Please try again.");
            revertToOriginal();
        });
    }

    function revertToOriginal() {
        repsInput.val(repsInput.data("original"));
        weightInput.val(weightInput.data("original"));
        volumeDisplay.text((repsInput.data("original") * weightInput.data("original")).toFixed(1));
    }
}


// Add this function to properly attach event handlers
$(document).on('click', '.quick-add-set', function () {
    startWorkoutTimer();
    const $exercise = $(this).closest('.exercise');
    const exerciseId = $exercise.data('exercise-id');
    const date = $(".workout-date.active").data("date");
    const muscleGroup = $exercise.data('muscle-group');

    const $tbody = $exercise.find("tbody");
    const $lastRow = $tbody.find("tr:last");

    // Clone last set values
    const reps = parseInt($lastRow.find(".set-reps").val() || 0, 10);
    const weight = parseFloat($lastRow.find(".set-weight").val() || 0);
    const rirText = $lastRow.find(".rir-badge").text().trim();
    const rir = rirText === "Failure" ? "Failure" : rirText.includes("RiR") ? parseInt(rirText) : null;
    const comments = $lastRow.find(".comment-icon").data("comment") || "";

    $.post("/workout/save_set", {
        date: date,
        exercise_id: exerciseId,
        reps: reps,
        weight: weight,
        muscle_group: muscleGroup,
        sets_count: 1,
        rir: rir,
        comments: comments
    }, function(response) {
        if (response.success) {
            const newSetId = response.set_ids[0];
            const setIndex = $tbody.find(".set-row").length + 1;

    // Proper RiR badge text
    let rirDisplayText;
    if (rir === "Failure") {
        rirDisplayText = "Failure";
    } else if (rir !== null) {
        rirDisplayText = rir + " RiR";
    } else {
        rirDisplayText = "None";
    }

            const rirDisplay = `
                <div class="rir-dropdown">
                    <span class="rir-badge">${rirDisplayText}</span>
                    <div class="rir-options">
                        <div class="rir-option" data-value="Failure">Failure</div>
                        <div class="rir-option" data-value="1">1 RiR</div>
                        <div class="rir-option" data-value="2">2 RiR</div>
                        <div class="rir-option" data-value="3">3 RiR</div>
                        <div class="rir-option" data-value="4">4 RiR</div>
                        <div class="rir-option" data-value="5">5 RiR</div>
                    </div>
                </div>
            `;

            const commentIcon = comments
                ? `<i class="fas fa-comment comment-icon" data-comment="${comments.replace(/"/g, '&quot;')}"></i>`
                : `<i class="far fa-comment comment-icon" data-comment=""></i>`;

            const newRow = $(`
                <tr class="set-row" data-set-id="${newSetId}">
                    <td>
    <div>
        ${setIndex}
        ${rirDisplay}
        ${commentIcon}
    </div>

                    </td>
                    <td>
                        <input type="number" class="form-control set-reps set-input" value="${reps}" data-original="${reps}">
                    </td>
                    <td>
                        <input type="number" class="form-control set-weight set-input" value="${weight}" data-original="${weight}" step="0.5">
                    </td>
                    <td class="volume-display">${(reps * weight).toFixed(1)}</td>
                    <td class="actions-cell">
                        <button class="btn delete-item">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `);

            $tbody.append(newRow);

            // Attach instant volume calculation for the new row
            newRow.find(".set-reps, .set-weight").on('input', function() {
                const $row = $(this).closest('tr');
                const repsVal = parseFloat($row.find(".set-reps").val() || 0);
                const weightVal = parseFloat($row.find(".set-weight").val() || 0);
                $row.find(".volume-display").text((repsVal * weightVal).toFixed(1));
            });
            invalidateDateCache(date);
        } else {
            alert("Error: " + response.error);
            console.error(response.error);
        }
    });
});
$(document).on("click", "#save-template-btn", function() {
  const workoutId = $(this).data("id");
  $("#comparisonModal").modal("hide");

  // Attach workoutId for saving
  $("#confirm-save-template-btn").data("workout-id", workoutId);

  $("#copyTemplateModal").modal("show");
});

// Confirm save template
$(document).on("click", "#confirm-save-template-btn", function() {
  const workoutId = $(this).data("workout-id");
  const templateName = $("#template-name-input").val().trim() || "Untitled Template";

  $.ajax({
    url: "/workout/save_template",
    type: "POST",
    contentType: "application/json",
    data: JSON.stringify({ workoutId, templateName }),
    success: function(response) {
      $("#copyTemplateModal").modal("hide");
      alert("Template saved successfully!");
    },
    error: function(err) {
      console.error("Template save failed", err);
    }
  });
});
$(document).on("click", "#copy-to-date-btn", function() {
  let workoutId = $(this).data("id");
  $("#copyWorkoutModal").data("workout-id", workoutId).modal("show");
});
const workoutName = document.getElementById("workout-name");
const editBtn = document.getElementById("edit-workout-name");
const input = document.getElementById("workout-input");
const dateSelector = document.getElementById("mobile-date-selector");

// Helper: get current date key
function getDateKey() {
    return dateSelector?.value || new Date().toISOString().split("T")[0]; 
    // fallback = today
}

// Load workout name for current date
function loadWorkoutName() {
    const key = "workoutName_" + getDateKey();
    const savedName = localStorage.getItem(key);
    if (savedName) {
        workoutName.textContent = savedName;
        input.value = savedName;
    } else {
        workoutName.textContent = "Nimetön Treeni";
        input.value = "Nimetön Treeni";
    }
}

// Save workout name for current date
function saveEdit() {
    const newName = input.value.trim() || "Nimetön Treeni";
    workoutName.textContent = newName;

    const key = "workoutName_" + getDateKey();
    localStorage.setItem(key, newName);

    workoutName.classList.remove("d-none");
    editBtn.classList.remove("d-none");
    input.classList.add("d-none");
}
function setupCalendarEvents() {
    // Remove any existing event handlers to prevent duplicates
    $(document).off("click", ".month-nav.prev");
    $(document).off("click", ".month-nav.next");
    $(document).off("click", ".date-cell");
    
    // Setup event handlers for calendar navigation
    $(document).on("click", ".month-nav.prev", function() {
        const cm = window.calendarState.currentMonth;
        window.calendarState.currentMonth = new Date(Date.UTC(cm.getUTCFullYear(), cm.getUTCMonth() - 1, 1));
        window.renderCalendar(window.calendarState.currentMonth);
    });

    $(document).on("click", ".month-nav.next", function() {
        const cm = window.calendarState.currentMonth;
        window.calendarState.currentMonth = new Date(Date.UTC(cm.getUTCFullYear(), cm.getUTCMonth() + 1, 1));
        window.renderCalendar(window.calendarState.currentMonth);
    });
    
    // Date cell click handler
    $(document).on("click", ".date-cell", function(){
        $(".date-cell").removeClass("selected");
        $(this).addClass("selected");
        const date = $(this).data("date");
        window.calendarState.selectedDate = date;

        // Call your existing function
        if (typeof copyWorkoutToDate === 'function') {
            copyWorkoutToDate(date);
        }
    });
}
// Smart workout name suggestions
let suggestionTimeout;

// Handle input in the inline workout name editor
$(document).on('input', '.workout-name-input:visible', function() {
    const query = $(this).val().trim();
    const suggestionsContainer = $('#workout-name-suggestions-inline');
    
    // Clear previous timeout
    clearTimeout(suggestionTimeout);
    
    if (query.length < 2) {
        suggestionsContainer.hide().empty();
        return;
    }
    
    // Debounce the search
    suggestionTimeout = setTimeout(() => {
        fetchWorkoutSuggestionsInline(query);
    }, 300);
});

function fetchWorkoutSuggestionsInline(query) {
    $.ajax({
        url: '/workout/similar_names',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ query: query }),
        success: function(response) {
            displayWorkoutSuggestionsInline(response.suggestions);
        },
        error: function(xhr, status, error) {
            console.error('Error fetching suggestions:', error);
            $('#workout-name-suggestions-inline').hide().empty();
        }
    });
}

function displayWorkoutSuggestionsInline(suggestions) {
    const container = $('#workout-name-suggestions-inline');
    
    if (suggestions.length === 0) {
        container.hide().empty();
        return;
    }
    
    let html = '';
    suggestions.forEach(suggestion => {
        html += `
            <div class="suggestion-item" data-session-id="${suggestion.session_id}" data-name="${suggestion.name}">
                <div class="suggestion-name">${suggestion.name}</div>
                <div class="suggestion-details">
                    ${formatDateForDisplay(suggestion.date)} • ${suggestion.focus_type}
                </div>
                <div class="copy-workout-hint">Kopioi pohjaksi</div>
            </div>
        `;
    });
    
    container.html(html).show();
}

// Handle suggestion clicks for inline editor
$(document).on('click', '#workout-name-suggestions-inline .suggestion-item', function() {
    const sessionId = $(this).data('session-id');
    const workoutName = $(this).data('name');
    
    // Fill in the workout name
    $('.workout-name-input.visible').val(workoutName);
    // ✅ UPDATE THE DISPLAY NAME IMMEDIATELY
    $('.workout-name-display').text(workoutName);
    // ✅ SAVE TO LOCALSTORAGE IMMEDIATELY
    const currentDate = $('.workout-date.active').data('date') || currentSelectedDate || new Date().toISOString().split('T')[0];
    const key = getWorkoutNameKey(currentDate);
    localStorage.setItem(key, workoutName);

    $('#workout-name-suggestions-inline').hide().empty();
    
// ✅ TRIGGER BLUR TO EXIT EDIT MODE
    $('.workout-name-input.visible').blur();
    
    // Show confirmation modal for copying the workout
    showCopyWorkoutConfirmationInline(sessionId, workoutName);
});

function showCopyWorkoutConfirmationInline(sessionId, workoutName) {
    const currentDate = $('.workout-date.active').data('date') || new Date().toISOString().split('T')[0];

    const modalHtml = `
        <div class="modal fade" id="copyWorkoutConfirmationModalInline" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content bg-dark text-light">
                    <div class="modal-header">
                        <h5 class="modal-title">${t('copy_previous_workout')}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>${t('copy_workout_question').replace('{workoutName}', workoutName).replace('{date}', formatDateForDisplay(currentDate))}</p>
                        <p class="text-muted">${t('copy_workout_description')}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-jere" data-bs-dismiss="modal">${t('no')}</button> 
                        <button type="button" class="btn btn-jere" id="confirm-copy-workout-inline" 
                                data-session-id="${sessionId}" data-target-date="${currentDate}">
                            ${t('yes')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove any existing modal and add new one
    $('#copyWorkoutConfirmationModalInline').remove();
    $('body').append(modalHtml);
    
    // Show modal
    new bootstrap.Modal(document.getElementById('copyWorkoutConfirmationModalInline')).show();
}


// Handle copy confirmation for inline editor
$(document).on('click', '#confirm-copy-workout-inline', function() {
    const sessionId = $(this).data('session-id');
    const targetDate = $(this).data('target-date');
    
    copyWorkoutFromSessionInline(sessionId, targetDate);
});

function copyWorkoutFromSessionInline(sessionId, targetDate) {
    const $btn = $('#confirm-copy-workout-inline');
    const originalText = $btn.text();
    $btn.text('Copying...').prop('disabled', true);
    
    $.ajax({
        url: '/workout/copy_from_session',
        method: 'POST',
        data: {
            session_id: sessionId,
            target_date: targetDate
        },
        success: function(response) {
            console.log('Copy response:', response); // Debug log
            
            if (response.success) {
                // Close modal
                $('#copyWorkoutConfirmationModalInline').modal('hide');
                
                // Clear cache for target date
                if (typeof getCachedData === 'function') {
                    const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                    if (cachedSessions[targetDate]) {
                        delete cachedSessions[targetDate];
                        setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
                    }
                }
                
                // Reload current session
                if (typeof getSessionWithCache === 'function') {
                    getSessionWithCache(targetDate, function(data) {
                        renderWorkoutSession(data.session, data.exercises);
                    });
                } else {
                    location.reload();
                }
                
                alert(`Treeni kopioitu onnistuneesti! ${response.debug ? response.debug.sets_copied : ''} sarjaa kopioitu.`);
            } else {
                alert('Ongelma kopioinissa: ' + response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Copy error:', xhr.responseText);
            alert('Yhteysvirhe kopioinissa');
        },
        complete: function() {
            $btn.text(originalText).prop('disabled', false);
        }
    });
}

// Hide suggestions when clicking outside the inline editor
$(document).on('click', function(e) {
    if (!$(e.target).closest('.workout-name-input, #workout-name-suggestions-inline').length) {
        $('#workout-name-suggestions-inline').hide();
    }
});

// Hide suggestions when input loses focus (with delay to allow clicks)
$(document).on('blur', '.workout-name-input', function() {
    setTimeout(() => {
        $('#workout-name-suggestions-inline').hide();
    }, 200);
});
