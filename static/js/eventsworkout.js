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

// Reattach when workout content changes (for mobile/desktop switching)
$(document).on('workoutContentChanged', function() {
    attachTemplateEventHandlers();
});

function setupExerciseCompletion() {
    $(document).on('click', '.complete-exercise-icon', function(e) {
        e.stopPropagation();

        const $dropdown = $(this).siblings('.complete-exercise-options');

        // Hide all other dropdowns
        $('.complete-exercise-options').not($dropdown).hide();

        // Toggle this dropdown
        $dropdown.toggle();

        if (!$dropdown.is(':visible')) return; // skip if just hidden

        // Get container boundaries
        const $container = $(this).closest('.card, .grid-panel'); // adjust if needed
        const containerTop = $container.offset().top;
        const containerBottom = $container.offset().top + $container.outerHeight();

        // Position dropdown
        const iconOffset = $(this).offset().top;
        const iconHeight = $(this).outerHeight();
        const dropdownHeight = $dropdown.outerHeight();

        const spaceBelow = containerBottom - (iconOffset + iconHeight);
        const spaceAbove = iconOffset - containerTop;

        if (spaceBelow >= dropdownHeight) {
            // Enough space below
            $dropdown.css({ top: '100%', bottom: 'auto' });
        } else if (spaceAbove >= dropdownHeight) {
            // Enough space above
            $dropdown.css({ top: 'auto', bottom: '100%' });
        } else {
            // Not enough space either side: prefer below, shrink if needed
            $dropdown.css({ top: '100%', bottom: 'auto', maxHeight: spaceBelow, overflowY: 'auto' });
        }
    });

    // Complete option selection
    $(document).on('click', '.complete-option', function(e) {
        e.stopPropagation();
        const value = $(this).data('value');
        const exerciseId = $(this).closest('.exercise').data('exercise-id');
        const groupName = $(this).closest('.workout-group').data('group');
        const date = $(".workout-date.active").data("date");

        // Update completed state
        if (value === 'yes') {
            markExerciseCompleted(exerciseId, groupName, date);
        } else {
            markExerciseNotCompleted(exerciseId, groupName, date);
        }

        // Hide dropdown
        $(this).closest('.complete-exercise-options').hide();
    });

    // Clicking outside closes all dropdowns
    $(document).on('click', function() {
        $('.complete-exercise-options').hide();
    });
}

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

    // --- AJAX call removed ---
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

$(document).on("click", ".delete-item", function() {
    const $button = $(this);
    const row = $button.closest("tr");
    const setId = row.data("set-id");
    
    if (!confirm("Are you sure you want to delete this set?")) return;
    
    // Disable button & show spinner
    $button.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i>');
    
    // Call delete with button reference
    deleteSet(setId, $button);
});

function handleSetUpdate() {
    const row = $(this).closest("tr");
    const repsInput = row.find(".set-reps");
    const weightInput = row.find(".set-weight");

    // Store focus information before updating
    lastFocusedSetId = row.data("set-id");
    lastFocusedInputType = $(this).hasClass('set-reps') ? 'reps' : 'weight';

    // Validate input
    const repsVal = repsInput.val().trim();
    const weightVal = weightInput.val().trim();

    if (repsVal === "" || weightVal === "" || isNaN(repsVal) || isNaN(weightVal)) {
        // Reset back to original values if invalid
        repsInput.val(repsInput.data("original"));
        weightInput.val(weightInput.data("original"));
        return; 
    }

    const setId = row.data("set-id");
    const reps = parseFloat(repsVal);
    const weight = parseFloat(weightVal);
    const date = $(".workout-date.active").data("date");

    if (reps != repsInput.data("original") || weight != weightInput.data("original")) {
        const volumeDisplay = row.find(".volume-display");
        volumeDisplay.html('<i class="fas fa-spinner fa-spin"></i>');

        // Optimistic UI update - show the new volume immediately
        const newVolume = (reps * weight).toFixed(1);
        setTimeout(() => {
            volumeDisplay.text(newVolume);
            row.addClass('set-updated');
        }, 300);

        $.post("/workout/update_set", {
            set_id: setId,
            reps: reps,
            weight: weight
        }, function(response) {
            if (response.success) {
                repsInput.data("original", reps);
                weightInput.data("original", weight);
                // Invalidate session cache for this date since we've modified it
                const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                if (cachedSessions[date]) {
                    delete cachedSessions[date];
                    setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
                }
            } else {
                alert("Error: " + response.error);
                // Revert to original values on error
                repsInput.val(repsInput.data("original"));
                weightInput.val(weightInput.data("original"));
                volumeDisplay.text(
                    (repsInput.data("original") * weightInput.data("original")).toFixed(1)
                );
            }
        }).fail(function() {
            // Revert to original values on network error
            repsInput.val(repsInput.data("original"));
            weightInput.val(weightInput.data("original"));
            volumeDisplay.text(
                (repsInput.data("original") * weightInput.data("original")).toFixed(1)
            );
            alert("Network error. Please try again.");
        });
    }
}

// Add this function to properly attach event handlers
function attachTemplateEventHandlers() {
    // Remove any existing handlers to prevent duplication
    $(".template-item").off('click');
    
    // Attach new handlers
    $(".template-item").on('click', function(e) {
        e.preventDefault();
        previewTemplate($(this).data('id'));
    });
}