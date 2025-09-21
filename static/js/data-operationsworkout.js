console.log("data-operationworkout.js started");
// File: data-operations.js
// ===== DATA OPERATION FUNCTIONS =====
function saveSet(isMobile = false) {
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
            // Invalidate session cache for this date since we've modified it
            const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
            if (cachedSessions[date]) {
                delete cachedSessions[date];
                setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
            }
            
            // Use cached version of session loading
            getSessionWithCache(date, function(data) {
                renderWorkoutSession(data.session, data.exercises);
            });
            resetSetForm(isMobile);
        } else {
            alert("Error: " + response.error);
        }
    });
}
    
function deleteSet(setId, $button) {
    saveScrollPosition(); // Save before making changes
    
    // Optimistic UI update - remove the set immediately
    const $row = $button.closest('tr');
    $row.addClass('set-updated');
    
    setTimeout(() => {
        $row.remove();
        hideEmptyWorkoutGroups();
    }, 1000);
    
    $.post("/workout/delete_set", { set_id: setId }, function(response) {
        if (response.success) {
            // Invalidate session cache for this date since we've modified it
            const date = $(".workout-date.active").data("date");
            const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
            if (cachedSessions[date]) {
                delete cachedSessions[date];
                setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
            }
        } else {
            // If the server request failed, reload the session to restore the set
            const date = $(".workout-date.active").data("date");
            // Use cached version of session loading
            getSessionWithCache(date, function(data) {
                renderWorkoutSession(data.session, data.exercises);
            });
        }
    }).fail(function() {
        // If there was a network error, reload the session to restore the set
        const date = $(".workout-date.active").data("date");
        // Use cached version of session loading
        getSessionWithCache(date, function(data) {
            renderWorkoutSession(data.session, data.exercises);
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
    if (sourceDate === targetDate) {
        alert("Ei pysty kopioimaan samalle päivälle!");
        isCopyingWorkout = false;
        return;
    }

    const $btn = $("#copy-workout-btn, #copy-workout-mobile-btn");
    const originalContent = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin me-1"></i> Copying...');
    $btn.prop('disabled', true);

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

    // Show a loading overlay for better UX
    showLoadingOverlay("Kopioidaan treeni...");
    

    $.post("/workout/copy_session", {
        source_date: sourceDate,
        target_date: targetDate
    })
    .done(function(response) {
        if (response.success) {
            // Clear cache for target date more aggressively
            const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
            delete cachedSessions[targetDate];
            setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
            
            // Force a fresh server fetch instead of using cache
            $.post("/workout/get_session", { date: targetDate }, function(data) {
                // Update cache with fresh data
                const updatedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                updatedSessions[targetDate] = data;
                setCachedData(CACHE_KEYS.SESSIONS, updatedSessions);
                
                renderWorkoutSession(data.session, data.exercises, { collapseGroups: true });
            });
            
            $("#copyWorkoutModal").modal("hide");
            // Show success toast
    const toastEl = document.getElementById('copySuccessToast');
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 }); // auto-hide after 3s
    toast.show();

        } else {
            showErrorMessage("Error: " + response.error);
        }
    })
    .fail(function(xhr, status, error) {
        showErrorMessage("Network error. Please try again.");
        console.error("Copy workout error:", status, error);
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
            exercises
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
