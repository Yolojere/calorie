console.log("data-operationworkout.js started");
// File: data-operations.js
// ===== DATA OPERATION FUNCTIONS =====
function saveSet(isMobile = false) {
    // 🟢 START TIMER ON FIRST SET
    startWorkoutTimer();
    
    const repsInput = isMobile ? $("#reps-input-mobile") : $("#reps-input");
    const weightInput = isMobile ? $("#weight-input-mobile") : $("#weight-input");
    
    saveScrollPosition();
    
    const exerciseId = isMobile ? $("#exercise-select-mobile").val() : $("#exercise-select").val();
    const reps = isMobile ? $("#reps-input-mobile").val() : $("#reps-input").val();
    const weight = isMobile ? $("#weight-input-mobile").val() : $("#weight-input").val();
    const muscleGroup = isMobile ? $("#muscle-group-select-mobile").val() : $("#muscle-group-select").val();
    const setsCount = isMobile ? $("#sets-input-mobile").val() : $("#sets-input").val();
    const rirRaw = isMobile ? $("#rir-input-mobile").val() : $("#rir-input").val();
    const comments = isMobile ? $("#comments-input-mobile").val() : $("#comments-input").val();
    const date = $(".workout-date.active").data("date");
    const rir = rirRaw === "Failure" ? -1 : 
           (rirRaw === "" ? null : Number(rirRaw));
    
    $.post("/workout/save_set", {
        date: date,
        exercise_id: exerciseId,
        reps: reps,
        weight: weight,
        muscle_group: muscleGroup,
        sets_count: setsCount,
        rir: rir,
        comments: comments
    }, function(response) {
        if (response.success) {
            // ✅ FIXED: Invalidate cache and use getSessionWithCache instead of loadWorkoutData
            invalidateDateCache(date);
            getSessionWithCache(date, function(data) {
                console.log('✅ Workout refreshed after adding set');
            });
            resetSetForm(isMobile);
        } else {
            alert("Error: " + response.error);
        }
    });
}
    
function deleteSet(setId, $button) {
    saveScrollPosition();

    const $row = $button.closest('tr');
    const $exercise = $row.closest('.exercise-card'); // adjust selector to your container

    // Animate row removal
    $row.fadeOut(300, function() {
        $(this).remove();

        // Check if exercise group is now empty
        const $tbody = $exercise.find("tbody");
        if ($tbody.find("tr.set-row").length === 0) {
            $exercise.fadeOut(300, function() {
                $(this).remove();
                hideEmptyWorkoutGroups();
            });
        } else {
            hideEmptyWorkoutGroups();
        }
    });

    // Call backend to delete set
    $.post("/workout/delete_set", { set_id: setId }, function(response) {
        const date = $(".workout-date.active").data("date");
        if (response.success) {
            // ✅ FIXED: Use invalidateDateCache and getSessionWithCache instead of loadWorkoutData
            invalidateDateCache(date);
            getSessionWithCache(date, function(data) {
                console.log('✅ Workout refreshed after deleting set');
            });
        } else {
            // ✅ FIXED: Use getSessionWithCache instead of loadWorkoutData  
            getSessionWithCache(date, function(data) {
                console.log('✅ Workout refreshed after delete error');
            });
        }
    }).fail(function() {
        const date = $(".workout-date.active").data("date");
        // ✅ FIXED: Use getSessionWithCache instead of loadWorkoutData
        getSessionWithCache(date, function(data) {
            console.log('✅ Workout refreshed after delete failure');
        });
    });
}

function addExercise() {
    const name = $("#new-exercise-name").val();
    const muscleGroup = $("#new-muscle-group").val();
    const description = $("#new-exercise-desc").val();
    
    // Validate input
    if (!name || !muscleGroup) {
        alert("Exercise name and muscle group are required!");
        return;
    }
    
    $.post("/workout/add_exercise", {
        name: name,
        muscle_group: muscleGroup,
        description: description
    }, function(response) {
        if (response.success) {
            // Invalidate exercises cache since we've added a new exercise
            invalidateCache(CACHE_KEYS.EXERCISES);
            
            // Use cached version of exercises loading
            getExercisesWithCache(function() {
                renderExerciseOptions();
            });
            $("#addExerciseModal").modal("hide");
            resetExerciseForm();
            alert("Exercise added successfully!");
        } else {
            alert("Error: " + response.error);
        }
    }).fail(function() {
        alert("Network error. Please try again.");
    });
}

function updateRir(setId, rirValue) {
    $.ajax({
        url: "/workout/update_rir",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ set_id: setId, rir: rirValue }),
        success: function(response) {
            if (!response.success) {
                alert('Error updating RiR');
                const date = $(".workout-date.active").data("date");
                // Use cached version of session loading
                getSessionWithCache(date, function(data) {
                    renderWorkoutSession(data.session, data.exercises);
                });
            }
        }
    });
}

function updateComment(setId, comment) {
    $.ajax({
        url: "/workout/update_comment",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ set_id: setId, comment: comment }),
        success: function(response) {
            if (!response.success) {
                alert('Error updating comment');
                const date = $(".workout-date.active").data("date");
                // Use cached version of session loading
                getSessionWithCache(date, function(data) {
                    renderWorkoutSession(data.session, data.exercises);
                });
            }
        }
    });
}

function saveTemplate() {
    const templateName = prompt("Enter a name for this template:");
    if (!templateName) return;

    const $btn = $("#save-template-btn");
    const originalContent = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin me-1"></i> Saving...');
    $btn.prop('disabled', true);

    const currentDate = $(".workout-date.active").data("date");

    // Get CSRF token from meta tag
    const csrfToken = $('meta[name="csrf-token"]').attr('content');

    $.ajax({
        url: "/workout/save_template",
        method: "POST",
        data: {
            name: templateName,
            date: currentDate,
            csrf_token: csrfToken  // <-- Include CSRF
        },
        success: function(data) {
            $btn.html(originalContent);
            $btn.prop('disabled', false);

            if (data.success) {
                alert("Template saved successfully!");
                invalidateCache(CACHE_KEYS.TEMPLATES);
                getTemplatesWithCache();
            } else {
                alert("Error: " + data.error);
            }
        },
        error: function(xhr, status, error) {
            $btn.html(originalContent);
            $btn.prop('disabled', false);
            alert("Error: " + (xhr.responseJSON?.error || error));
        }
    });
}

function previewTemplate(templateId) {
    $("#template-preview-content").html(
        '<div class="text-center py-3">' +
        '<i class="fas fa-spinner fa-spin me-2"></i>Loading template...' +
        '</div>'
    );

    $("#templatePreviewModal").modal('show');

    $.ajax({
        url: `/workout/templates/${templateId}`,
        method: "GET",
        success: function(data) {
            if (data.success && data.exercises.length > 0) {
                let html = "";
                const groups = {};

                // Organize exercises by muscle group
                data.exercises.forEach(ex => {
                    if (!groups[ex.muscle_group]) groups[ex.muscle_group] = [];
                    groups[ex.muscle_group].push(ex);
                });

                // Build collapsible HTML with custom icons
                Object.keys(groups).forEach((group, idx) => {
                    const groupId = `muscleGroup-${idx}`;
                    const totalSets = groups[group].reduce((sum, ex) => sum + ex.sets, 0);
                    const icon = getMuscleIcon(group); // Use your icons

                    const translatedGroup = t(group.toLowerCase());

                    html += `
                        <div class="mb-3 muscle-group-card">
        <button class="btn btn-dark w-100 d-flex justify-content-between align-items-center muscle-group-btn"
                type="button"
                data-bs-toggle="collapse"
                data-bs-target="#${groupId}"
                aria-expanded="true"
                aria-controls="${groupId}">
            <span><i class="fas fa-${icon} me-2"></i>${translatedGroup} (${totalSets} ${t('set')})</span>
            <i class="fas fa-chevron-down chevron-icon"></i>
        </button>
        <div class="collapse show mt-2" id="${groupId}">
            <ul class="list-unstyled ps-4 mb-0">`;
                    groups[group].forEach(exercise => {
                        const translatedExercise = t(exercise.exercise);
                        html += `<li class="mb-1">
                                    <span class="fw-semibold">${translatedExercise}</span> × ${exercise.sets} ${t('sets')}
                                 </li>`;
                    });

                    html += `</ul></div></div>`;
                });

                $("#template-preview-content").html(html);
                $("#template-preview-name").text(t(data.template.name));
                $("#apply-template-btn").data('template-id', templateId);

                // Animate chevron rotation
                $('.muscle-group-btn').on('click', function() {
                    const $chevron = $(this).find('.chevron-icon');
                    const targetId = $(this).attr('data-bs-target');
                    const $collapseDiv = $(targetId);

                    $collapseDiv.on('shown.bs.collapse', function() {
                        $chevron.css('transform', 'rotate(180deg)');
                    });
                    $collapseDiv.on('hidden.bs.collapse', function() {
                        $chevron.css('transform', 'rotate(0deg)');
                    });
                });

            } else {
                $("#template-preview-content").html(
                    `<div class="text-center py-3">${t('noTemplatesFound')}</div>`
                );
            }
        },
        error: function(xhr, status, error) {
            alert("Error loading template: " + error);
            $("#templatePreviewModal").modal('hide');
        }
    });
}

// Example muscle icon mapping function
function getMuscleIcon(muscleGroup) {
    const icons = {
        'Chest': 'heart',
        'Back': 'user-shield',
        'Legs': 'running',
        'Shoulders': 'mountain',
        'Arms': 'hand-fist',
        'Core': 'apple-alt'
    };
    return icons[muscleGroup] || 'dumbbell';
}


function applyTemplate(templateId) {
    const currentDate = $(".workout-date.active").data("date");
    
    // Show loading state
    const $btn = $("#apply-template-btn");
    const originalContent = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin me-1"></i> Applying...');
    $btn.prop('disabled', true);
    
    // Use jQuery AJAX instead of fetch to ensure CSRF token is included
    $.ajax({
        url: "/workout/apply_template",
        method: "POST",
        data: {
            template_id: templateId,
            date: currentDate
        },
        success: function(data) {
            $btn.html(originalContent);
            $btn.prop('disabled', false);
            
            if (data.success) {
                alert("Template applied successfully!");
                // Invalidate session cache for this date since we've modified it
                const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                if (cachedSessions[currentDate]) {
                    delete cachedSessions[currentDate];
                    setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
                }
                
                isApplyingTemplate = true;
                // Use cached version of session loading
                getSessionWithCache(currentDate, function(data) {
                    renderWorkoutSession(data.session, data.exercises);
                });
            } else {
                alert("Error: " + data.error);
            }
        },
        error: function(xhr, status, error) {
            $btn.html(originalContent);
            $btn.prop('disabled', false);
            alert("Error: " + error);
        }
    });
}

function copyWorkoutToDate(targetDate) {
    if (isCopyingWorkout) {
        console.log("Copy already in progress, please wait...");
        return;
    }
    isCopyingWorkout = true;

    const sourceDate = $("#copyWorkoutModal").data("source-date");
    
    if (!sourceDate) {
        console.error("No source date available for copying");
        isCopyingWorkout = false;
        return;
    }

    const $btn = $("#copy-workout-btn, #copy-workout-mobile-btn");
    const originalContent = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin me-1"></i> Copying...');
    $btn.prop('disabled', true);

    // Show loading overlay
    showLoadingOverlay("Kopioidaan treeni...");

    // Check if target date has existing workout
    getSessionWithCache(targetDate, function(data) {
        if (data.session && data.exercises && data.exercises.length > 0) {
            if (!confirm("Tällä päivällä on jo merkattu treeni. Kopioidaanko sen päälle?")) {
                hideLoadingOverlay();
                $btn.html(originalContent);
                $btn.prop('disabled', false);
                isCopyingWorkout = false;
                return;
            }
        }

        // Perform the copy
        $.post("/workout/copy_session", {
            source_date: sourceDate,
            target_date: targetDate
        })
        .done(function(response) {
            if (response.success) {
                // Aggressively clear cache for target date
                const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                delete cachedSessions[targetDate];
                setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
                
                // Also clear any other related cache entries
                localStorage.removeItem(`workout_${targetDate}`);
                localStorage.removeItem(`session_${targetDate}`);
                
                // Force fresh server fetch
                $.post("/workout/get_session", { date: targetDate })
                .done(function(freshData) {
                    // Update cache with fresh data
                    const updatedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                    updatedSessions[targetDate] = freshData;
                    setCachedData(CACHE_KEYS.SESSIONS, updatedSessions);
                    
                    // Re-render if this is the currently selected date
                    if (targetDate === currentSelectedDate) {
                        renderWorkoutSession(freshData.session, freshData.exercises, { collapseGroups: true });
                    }
                })
                .fail(function() {
                    console.error("Failed to fetch fresh session data");
                });
                
                $("#copyWorkoutModal").modal("hide");
                
                // Show success toast
                const toastEl = document.getElementById('copySuccessToast');
                const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
                toast.show();
                
            } else {
                showErrorMessage("Error: " + response.error);
            }
        })
        .fail(function(xhr, status, error) {
            showErrorMessage("Network error. Please try again.");
            console.error("Copy workout error:", xhr.responseText, status, error);
        })
        .always(function() {
            hideLoadingOverlay();
            $btn.html(originalContent);
            $btn.prop('disabled', false);
            isCopyingWorkout = false;
        });
    });
}

// Helper functions for user feedback
function showLoadingOverlay(message) {
    $('body').append(`
        <div id="loading-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        ">
            <div class="text-center">
                <i class="fas fa-spinner fa-spin fa-2x"></i>
                <p class="mt-2">${message}</p>
            </div>
        </div>
    `);
}

function hideLoadingOverlay() {
    $('#loading-overlay').remove();
}

function showSuccessMessage(message) {
    // You can use a toast notification library or custom implementation
    alert(message); // Replace with a better notification system
}

function showErrorMessage(message) {
    alert(message); // Replace with a better notification system
}

// Toggle focus selection buttons
$(document).on("click", ".focus-btn", function() {
    $(".focus-btn").removeClass("active");
    $(this).addClass("active");
});

// Get exercises from the UI
function getExercisesFromUI() {
    const exercises = [];

    $(".exercise").each(function() {
        const $exercise = $(this);
        const exId = $exercise.data("exercise-id");
        const exName = $exercise.find(".exercise-title").text().trim();
        const muscleGroup = $exercise.closest(".workout-group").data("group") || "Other";

        const sets = [];
        $exercise.find(".set-row").each(function() {
            const $row = $(this);
            const reps = parseInt($row.find(".set-reps").val()) || 0;
            const weight = parseFloat($row.find(".set-weight").val()) || 0;
            sets.push({ reps, weight });
        });

        exercises.push({
            id: exId,
            name: exName,
            muscle_group: muscleGroup,
            sets
        });
    });

    return exercises;
}
// Enhanced Save Workout with Analysis and PR Detection
$(document).off("click", "#save-workout-btn").on("click", "#save-workout-btn", function() {
    const name = $("#workout-name-input").val().trim() || "Unnamed Workout";
    const focus_type = $(".focus-btn.active").data("focus");
    const date = currentSelectedDate;
    const exercises = getExercisesFromUI();
    
    // 🔴 STOP TIMER WHEN SAVING
    stopWorkoutTimer();
    
    // Get timer and cardio data
    const timerData = getWorkoutTimerData();
    const cardioSessions = getCardioSessionsFromUI(); // New function needed
    
    // Show analysis overlay
    showWorkoutAnalysis();
    
    $.ajax({
        url: "/workout/save",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            name,
            focus_type,
            date,
            exercises,
            timer_data: timerData, // Add timer data
            cardio_sessions: cardioSessions // Add cardio data
        }),
        dataType: "json",
        success: function(response) {
            if (response.success) {
                $("#saveWorkoutModal").modal("hide");
                
                // Continue analysis for 4 seconds, then show results
                setTimeout(() => {
                    hideWorkoutAnalysis();
                    showWorkoutResults(response.comparisonData, response.achievements);
                    updateSetRowsWithProgress(response.comparisonData);
                }, 4000);
                const date = currentSelectedDate;
                localStorage.removeItem(getWorkoutNameKey(date));
            } else {
                hideWorkoutAnalysis();
                alert("Error saving workout: " + response.error);
            }
        },
        error: function(xhr, status, error) {
            hideWorkoutAnalysis();
            console.error("AJAX Error:", status, error);
            alert("An error occurred while saving the workout.");
        }
    });
});

function navigateWeek(direction) {
    const days = direction === 'prev' ? -7 : 7
    currentDate.setDate(currentDate.getDate() + days);
    const weekDates = getWeekDates(currentDate);
    renderWeekDates(weekDates);
}
// ===== CARDIO SEARCH FUNCTIONALITY =====

let cardioSearchTimeout = null;
let selectedCardioExercises = {
    desktop: null,
    mobile: null
};

// Initialize cardio search functionality
function initCardioSearch() {
    console.log('Initializing cardio search functionality');
    
    // Setup search for both desktop and mobile
    setupCardioSearch('', false); // Desktop
    setupCardioSearch('-mobile', true); // Mobile
}

// Setup search functionality for a specific version (desktop/mobile)
function setupCardioSearch(suffix, isMobile) {
    const searchInput = document.getElementById(`cardio-search-input${suffix}`);
    const hiddenInput = document.getElementById(`cardio-exercise-id${suffix}`);
    const resultsContainer = document.getElementById(`cardio-search-results${suffix}`);
    const clearBtn = document.getElementById(`cardio-clear${suffix}`);
    
    if (!searchInput || !resultsContainer) {
        console.warn('Cardio search elements not found for suffix:', suffix);
        return;
    }
    
    // Search input handler
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        if (query.length === 0) {
            hideCardioResults(suffix);
            return;
        }
        
        if (query.length < 2) {
            return; // Wait for at least 2 characters
        }
        
        // Debounce search
        clearTimeout(cardioSearchTimeout);
        cardioSearchTimeout = setTimeout(() => {
            searchCardioExercises(query, suffix, isMobile);
        }, 300);
    });
    
    // Focus handler - show recent results if available
    searchInput.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length >= 2) {
            searchCardioExercises(query, suffix, isMobile);
        } else if (cardioExercises && Object.keys(cardioExercises).length > 0) {
            // Show popular exercises when focusing empty field
            showPopularCardioExercises(suffix);
        }
    });
    
    // Blur handler - hide results with delay to allow clicking
    searchInput.addEventListener('blur', function() {
        setTimeout(() => {
            hideCardioResults(suffix);
        }, 200);
    });
    
    // Clear button handler
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            clearCardioSelection(suffix, isMobile);
        });
    }
    
    // Keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
        handleCardioKeyboardNavigation(e, suffix);
    });
    
    // Click outside to close
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.cardio-search-container')) {
            hideCardioResults('');
            hideCardioResults('-mobile');
        }
    });
}

// Search through cardio exercises
function searchCardioExercises(query, suffix, isMobile) {
    const resultsContainer = document.getElementById(`cardio-search-results${suffix}`);
    
    if (!cardioExercises || Object.keys(cardioExercises).length === 0) {
        console.warn('No cardio exercises loaded');
        return;
    }
    
    const searchQuery = query.toLowerCase();
    const results = [];
    
    // Search through all exercise types
    Object.keys(cardioExercises).forEach(type => {
        cardioExercises[type].forEach(exercise => {
            const nameMatch = exercise.name.toLowerCase().includes(searchQuery);
            const typeMatch = type.toLowerCase().includes(searchQuery);
            
            if (nameMatch || typeMatch) {
                results.push({
                    ...exercise,
                    type: type,
                    relevance: nameMatch ? 2 : 1 // Higher relevance for name matches
                });
            }
        });
    });
    
    // Sort by relevance and name
    results.sort((a, b) => {
        if (a.relevance !== b.relevance) {
            return b.relevance - a.relevance;
        }
        return a.name.localeCompare(b.name);
    });
    
    displayCardioResults(results, suffix, isMobile);
}

// Display search results
function displayCardioResults(results, suffix, isMobile) {
    const resultsContainer = document.getElementById(`cardio-search-results${suffix}`);
    
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="cardio-search-no-results">
                No exercises found. Try a different search term.
            </div>
        `;
        resultsContainer.classList.add('show');
        return;
    }
    
    let html = '';
    let currentType = '';
    
    results.forEach(exercise => {
        // Add type header if it's a new type
        if (exercise.type !== currentType) {
            currentType = exercise.type;
            const typeLabel = exercise.type.charAt(0).toUpperCase() + 
                            exercise.type.slice(1).replace('_', ' ');
            html += `<div class="cardio-group-header">${typeLabel}</div>`;
        }
        
        html += `
            <div class="cardio-search-item" 
                 data-exercise-id="${exercise.id}"
                 data-exercise-name="${exercise.name}"
                 data-met-value="${exercise.met_value}"
                 data-type="${exercise.type}">
                <div class="cardio-exercise-name">${exercise.name}</div>
                <div class="cardio-exercise-details">${exercise.met_value} METs • ${exercise.type.replace('_', ' ')}</div>
            </div>
        `;
    });
    
    resultsContainer.innerHTML = html;
    resultsContainer.classList.add('show');
    
    // Add click handlers
    resultsContainer.querySelectorAll('.cardio-search-item').forEach(item => {
        item.addEventListener('click', function() {
            selectCardioExercise(this, suffix, isMobile);
        });
    });
}

// Show popular cardio exercises when focusing empty field
function showPopularCardioExercises(suffix) {
    if (!cardioExercises) return;
    
    const popular = [];
    
    // Get some popular exercises from each category
    Object.keys(cardioExercises).forEach(type => {
        const exercises = cardioExercises[type].slice(0, 2); // First 2 from each type
        exercises.forEach(exercise => {
            popular.push({
                ...exercise,
                type: type,
                relevance: 1
            });
        });
    });
    
    if (popular.length > 0) {
        displayCardioResults(popular, suffix);
    }
}

// Select a cardio exercise
function selectCardioExercise(item, suffix, isMobile) {
    const exerciseId = item.dataset.exerciseId;
    const exerciseName = item.dataset.exerciseName;
    const metValue = item.dataset.metValue;
    
    const searchInput = document.getElementById(`cardio-search-input${suffix}`);
    const hiddenInput = document.getElementById(`cardio-exercise-id${suffix}`);
    const clearBtn = document.getElementById(`cardio-clear${suffix}`);
    
    // Update inputs
    searchInput.value = exerciseName;
    searchInput.classList.add('selected');
    hiddenInput.value = exerciseId;
    
    // Show clear button
    if (clearBtn) {
        clearBtn.classList.remove('d-none');
    }
    
    // Store selection
    selectedCardioExercises[isMobile ? 'mobile' : 'desktop'] = {
        id: exerciseId,
        name: exerciseName,
        met_value: parseFloat(metValue)
    };
    
    // Hide results
    hideCardioResults(suffix);
    
    // Update calorie preview
    updateCaloriePreview(isMobile);
    
    console.log('Selected cardio exercise:', exerciseName, 'ID:', exerciseId);
}

// Clear cardio selection
function clearCardioSelection(suffix, isMobile) {
    const searchInput = document.getElementById(`cardio-search-input${suffix}`);
    const hiddenInput = document.getElementById(`cardio-exercise-id${suffix}`);
    const clearBtn = document.getElementById(`cardio-clear${suffix}`);
    
    searchInput.value = '';
    searchInput.classList.remove('selected');
    hiddenInput.value = '';
    
    if (clearBtn) {
        clearBtn.classList.add('d-none');
    }
    
    selectedCardioExercises[isMobile ? 'mobile' : 'desktop'] = null;
    
    hideCardioResults(suffix);
    updateCaloriePreview(isMobile);
    
    // Focus back to search input
    searchInput.focus();
}

// Hide search results
function hideCardioResults(suffix) {
    const resultsContainer = document.getElementById(`cardio-search-results${suffix}`);
    if (resultsContainer) {
        resultsContainer.classList.remove('show');
    }
}

// Keyboard navigation for search results
function handleCardioKeyboardNavigation(e, suffix) {
    const resultsContainer = document.getElementById(`cardio-search-results${suffix}`);
    const items = resultsContainer.querySelectorAll('.cardio-search-item');
    
    if (items.length === 0) return;
    
    let highlighted = resultsContainer.querySelector('.cardio-search-item.highlighted');
    let currentIndex = highlighted ? Array.from(items).indexOf(highlighted) : -1;
    
    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            if (highlighted) highlighted.classList.remove('highlighted');
            currentIndex = (currentIndex + 1) % items.length;
            items[currentIndex].classList.add('highlighted');
            items[currentIndex].scrollIntoView({ block: 'nearest' });
            break;
            
        case 'ArrowUp':
            e.preventDefault();
            if (highlighted) highlighted.classList.remove('highlighted');
            currentIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
            items[currentIndex].classList.add('highlighted');
            items[currentIndex].scrollIntoView({ block: 'nearest' });
            break;
            
        case 'Enter':
            e.preventDefault();
            if (highlighted) {
                const isMobile = suffix === '-mobile';
                selectCardioExercise(highlighted, suffix, isMobile);
            }
            break;
            
        case 'Escape':
            hideCardioResults(suffix);
            break;
    }
}

// Load cardio exercises
async function loadCardioExercises() {
    try {
        const response = await fetch('/workout/cardio-exercises');
        const data = await response.json();
        
        if (data.exercises) {
            cardioExercises = data.exercises;
            populateCardioSelects();
        }
    } catch (error) {
        console.error('Error loading cardio exercises:', error);
    }
}
// ✅ NEW FUNCTION: Load user profile data from database
async function loadUserProfileData() {
    try {
        const response = await fetch('/user/profile-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update global variables with database values
            if (result.weight) {
                userWeight = parseFloat(result.weight);
                console.log('Loaded user weight from database:', userWeight);
            }
            
            if (result.gender) {
                userGender = result.gender;
                console.log('Loaded user gender from database:', userGender);
            }
        } else {
            console.warn('Could not load user profile data:', result.error);
            // Keep defaults
        }
    } catch (error) {
        console.error('Error loading user profile data:', error);
        // Keep defaults
    }
}

function populateCardioSelects() {
    const selects = ['cardio-type-select', 'cardio-type-select-mobile'];
    
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Clear existing options except first
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        // Add exercises grouped by type
        Object.keys(cardioExercises).forEach(type => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ');
            
            cardioExercises[type].forEach(exercise => {
                const option = document.createElement('option');
                option.value = exercise.id;
                option.textContent = `${exercise.name} (${exercise.met_value} METs)`;
                option.dataset.metValue = exercise.met_value;
                optgroup.appendChild(option);
            });
            
            select.appendChild(optgroup);
        });
    });
}

// ✅ ENHANCED: Calculate estimated calories with multiple methods
function calculateCardioCalories(metValue, durationMinutes, heartRate = null, watts = null, distance = null) {
    if (!metValue || !durationMinutes) return 0;
    
    let calories = 0;
    let method = "MET";
    const durationHours = durationMinutes / 60.0;
    
    // Method 1: Watts-based (most accurate for cycling)
    if (watts && watts > 0) {
        calories = watts * durationHours * 3.6;
        method = "Watts";
    }
    // Method 2: Distance-based (good for running/walking)
    else if (distance && distance > 0) {
        const speedKmh = distance / durationHours;
        
        if (speedKmh > 6) {
            // Running METs based on speed
            let runningMet;
            if (speedKmh >= 16) runningMet = 15.0;
            else if (speedKmh >= 13) runningMet = 12.0;
            else if (speedKmh >= 11) runningMet = 11.0;
            else if (speedKmh >= 9) runningMet = 9.0;
            else if (speedKmh >= 8) runningMet = 8.0;
            else runningMet = 7.0;
            
            calories = runningMet * userWeight * durationHours;
            method = `Running (${speedKmh.toFixed(1)} km/h)`;
        } else {
            // Walking METs based on speed
            let walkingMet;
            if (speedKmh >= 5.5) walkingMet = 4.3;
            else if (speedKmh >= 4.8) walkingMet = 3.8;
            else if (speedKmh >= 4.0) walkingMet = 3.5;
            else if (speedKmh >= 3.2) walkingMet = 3.0;
            else walkingMet = 2.5;
            
            calories = walkingMet * userWeight * durationHours;
            method = `Walking (${speedKmh.toFixed(1)} km/h)`;
        }
    }
    // Method 3: Heart rate (when available)
    else if (heartRate && userAge && userGender) {
        if (userGender.toLowerCase() === 'male') {
            calories = durationMinutes * (0.6309 * heartRate + 0.1988 * userWeight + 0.2017 * userAge - 55.0969) / 4.184;
        } else {
            calories = durationMinutes * (0.4472 * heartRate - 0.1263 * userWeight + 0.074 * userAge - 20.4022) / 4.184;
        }
        method = `Heart Rate (${heartRate} bpm)`;
    }
    // Method 4: Standard MET calculation (fallback)
    else {
        calories = metValue * userWeight * durationHours;
        method = "MET";
    }
    
    console.log(`Calorie calculation - Method: ${method}, Calories: ${calories.toFixed(1)}`);
    return Math.max(0, calories);
}

// ✅ ENHANCED: Update calorie preview with multiple input methods
function updateCaloriePreview(isMobile = false) {
    const suffix = isMobile ? '-mobile' : '';
    const selectedExercise = selectedCardioExercises[isMobile ? 'mobile' : 'desktop'];
    const durationInput = document.getElementById(`duration-input${suffix}`);
    const heartRateInput = document.getElementById(`heart-rate-input${suffix}`);
    const wattsInput = document.getElementById(`watts-input${suffix}`);
    const distanceInput = document.getElementById(`distance-input${suffix}`);
    const caloriesPreview = document.getElementById(`calories-preview${suffix}`);
    
    if (!caloriesPreview || !selectedExercise || !durationInput) return;
    
    const metValue = selectedExercise.met_value;
    const duration = parseFloat(durationInput.value) || 0;
    const heartRate = heartRateInput ? parseFloat(heartRateInput.value) : null;
    const watts = wattsInput ? parseFloat(wattsInput.value) : null;
    const distance = distanceInput ? parseFloat(distanceInput.value) : null;
    
    if (metValue && duration) {
        const calories = calculateCardioCalories(metValue, duration, heartRate, watts, distance);
        caloriesPreview.textContent = `${isMobile ? 'Kalorit' : 'Estimated Calories'}: ${Math.round(calories)}`;
    } else {
        caloriesPreview.textContent = `${isMobile ? 'Kalorit' : 'Estimated Calories'}: --`;
    }
}

// Initialize search when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait for cardio exercises to load, then initialize search
    if (typeof loadCardioExercises === 'function') {
        loadCardioExercises().then(() => {
            initCardioSearch();
        });
    } else {
        // Fallback - try to initialize after a delay
        setTimeout(initCardioSearch, 1000);
    }
});

// Also initialize when cardio exercises are loaded
const originalPopulateCardioSelects = populateCardioSelects;
populateCardioSelects = function() {
    // Call original function (if needed for backward compatibility)
    if (typeof originalPopulateCardioSelects === 'function') {
        originalPopulateCardioSelects();
    }
    
    // Initialize search functionality
    initCardioSearch();
};

// ✅ UPDATED: Add cardio session without sending weight/gender (backend gets from DB)
async function addCardioSession(isMobile = false) {
    const suffix = isMobile ? '-mobile' : '';
    
    // Get the selected exercise ID from hidden input instead of select
    const hiddenInput = document.getElementById(`cardio-exercise-id${suffix}`);
    const selectedExercise = selectedCardioExercises[isMobile ? 'mobile' : 'desktop'];
    
    if (!selectedExercise || !hiddenInput.value) {
        alert('Please select a cardio exercise first');
        return;
    }
    
    const submitBtn = document.getElementById(`add-cardio-btn${suffix}`);
    if (submitBtn.disabled) return;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
    
    // Get other form values...
    const durationInput = document.getElementById(`duration-input${suffix}`);
    const distanceInput = document.getElementById(`distance-input${suffix}`);
    const paceInput = document.getElementById(`pace-input${suffix}`);
    const heartRateInput = document.getElementById(`heart-rate-input${suffix}`);
    const wattsInput = document.getElementById(`watts-input${suffix}`);
    const notesInput = document.getElementById(`cardio-notes-input${suffix}`);
    
    try {
        // Validate required fields
        if (!durationInput.value) {
            alert('Please enter duration');
            return;
        }
        
        const cardioData = {
            cardio_exercise_id: parseInt(hiddenInput.value),
            duration_minutes: parseFloat(durationInput.value),
            distance_km: distanceInput && distanceInput.value ? parseFloat(distanceInput.value) : null,
            avg_pace_min_per_km: paceInput && paceInput.value ? parseFloat(paceInput.value) : null,
            avg_heart_rate: heartRateInput && heartRateInput.value ? parseInt(heartRateInput.value) : null,
            watts: wattsInput && wattsInput.value ? parseInt(wattsInput.value) : null,
            notes: notesInput ? notesInput.value : '',
            date: currentSelectedDate,
            workout_name: document.querySelector('.workout-name-display')?.textContent || 'Mixed Session'
        };
        
        console.log('Adding cardio session with search data:', cardioData);
        
        const response = await fetch('/workout/add-cardio', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(cardioData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Cardio session added successfully');
            
            // Clear form
            clearCardioSelection(suffix, isMobile);
            if (durationInput) durationInput.value = '';
            if (distanceInput) distanceInput.value = '';
            if (paceInput) paceInput.value = '';
            if (heartRateInput) heartRateInput.value = '';
            if (wattsInput) wattsInput.value = '';
            if (notesInput) notesInput.value = '';
            
            // Update calorie preview
            updateCaloriePreview(isMobile);
            
            // Invalidate cache and refresh
            invalidateDateCache(currentSelectedDate);
            getSessionWithCache(currentSelectedDate, function(data) {
                console.log('Workout data refreshed after cardio addition');
            });
        } else {
            console.error('Failed to add cardio session:', result);
            alert(result.error || 'Error adding cardio session');
        }
    } catch (error) {
        console.error('Error adding cardio session:', error);
        alert('Network error adding cardio session');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fas fa-heart me-1"></i><span data-i18n="add-cardio">Add Cardio</span>`;
    }
}

// ✅ ENHANCED: Event listeners for cardio functionality (including new inputs)
function setupCardioEventListeners() {
    // Desktop events
    const typeSelect = document.getElementById('cardio-type-select');
    const durationInput = document.getElementById('duration-input');
    const heartRateInput = document.getElementById('heart-rate-input');
    const wattsInput = document.getElementById('watts-input');
    const distanceInput = document.getElementById('distance-input');
    const addCardioBtn = document.getElementById('add-cardio-btn');
    
    if (typeSelect) typeSelect.addEventListener('change', () => updateCaloriePreview(false));
    if (durationInput) durationInput.addEventListener('input', () => updateCaloriePreview(false));
    if (heartRateInput) heartRateInput.addEventListener('input', () => updateCaloriePreview(false));
    if (wattsInput) wattsInput.addEventListener('input', () => updateCaloriePreview(false));
    if (distanceInput) distanceInput.addEventListener('input', () => updateCaloriePreview(false));
    if (addCardioBtn) addCardioBtn.addEventListener('click', () => addCardioSession(false));
    
    // Mobile events
    const typeSelectMobile = document.getElementById('cardio-type-select-mobile');
    const durationInputMobile = document.getElementById('duration-input-mobile');
    const heartRateInputMobile = document.getElementById('heart-rate-input-mobile');
    const wattsInputMobile = document.getElementById('watts-input-mobile');
    const distanceInputMobile = document.getElementById('distance-input-mobile');
    const addCardioBtnMobile = document.getElementById('add-cardio-btn-mobile');
    
    if (typeSelectMobile) typeSelectMobile.addEventListener('change', () => updateCaloriePreview(true));
    if (durationInputMobile) durationInputMobile.addEventListener('input', () => updateCaloriePreview(true));
    if (heartRateInputMobile) heartRateInputMobile.addEventListener('input', () => updateCaloriePreview(true));
    if (wattsInputMobile) wattsInputMobile.addEventListener('input', () => updateCaloriePreview(true));
    if (distanceInputMobile) distanceInputMobile.addEventListener('input', () => updateCaloriePreview(true));
    if (addCardioBtnMobile) addCardioBtnMobile.addEventListener('click', () => addCardioSession(true));
}

// Initialize cardio functionality
document.addEventListener('DOMContentLoaded', function() {
    // ✅ LOAD USER DATA FIRST, THEN INITIALIZE
    loadUserProfileData().then(() => {
        loadCardioExercises();
        setupCardioEventListeners();
    });
});
