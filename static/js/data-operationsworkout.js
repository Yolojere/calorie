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
    
    // Use jQuery AJAX instead of fetch to ensure CSRF token is included
    $.ajax({
        url: "/workout/save_template",
        method: "POST",
        data: {
            name: templateName,
            date: currentDate
        },
        success: function(data) {
            $btn.html(originalContent);
            $btn.prop('disabled', false);
            
            if (data.success) {
                alert("Template saved successfully!");
                // Invalidate templates cache since we've added a new template
                invalidateCache(CACHE_KEYS.TEMPLATES);
                // Use cached version of templates loading
                getTemplatesWithCache();
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

function previewTemplate(templateId) {
    // Show loading state in table body
    $("#template-preview-body").html(
        '<tr><td colspan="4" class="text-center py-3">' +
        '<i class="fas fa-spinner fa-spin me-2"></i>Loading template...' +
        '</td></tr>'
    );

    // Set up modal content (without date selector)
    $("#template-preview-modal-body").html(`
        <table class="table table-dark">
            <thead>
                <tr>
                    <th>Exercise</th>
                    <th>Muscle Group</th>
                    <th>Reps</th>
                    <th>Weight</th>
                </tr>
            </thead>
            <tbody id="template-preview-body"></tbody>
        </table>
    `);

    // Show the modal
    $("#templatePreviewModal").modal('show');

    // Use jQuery AJAX instead of fetch to ensure CSRF token is included
    $.ajax({
        url: `/workout/templates/${templateId}`,
        method: "GET",
        success: function(data) {
            const $previewBody = $("#template-preview-body");
            $previewBody.empty();

            if (data.success && data.exercises && data.exercises.length > 0) {
                data.exercises.forEach(ex => {
                    $previewBody.append(`
                        <tr>
                            <td>${ex.name}</td>
                            <td>${ex.muscle_group}</td>
                            <td>${ex.reps}</td>
                            <td>${ex.weight} kg</td>
                        </tr>
                    `);
                });
            } else {
                $previewBody.append(
                    '<tr><td colspan="4" class="text-center py-3">No exercises in this template</td></tr>'
                );
            }

            // Store template ID on apply button for later use
            $("#apply-template-btn").data('template-id', templateId);
        },
        error: function(xhr, status, error) {
            alert("Error loading template: " + error);
            $("#templatePreviewModal").modal('hide');
        }
    });
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
    const sourceDate = currentSelectedDate;
    
    if (sourceDate === targetDate) {
        alert("Cannot copy to the same date!");
        return;
    }
    
    // Show loading state
    const $btn = $("#copy-workout-btn, #copy-workout-mobile-btn");
    const originalContent = $btn.html();
    $btn.html('<i class="fas fa-spinner fa-spin me-1"></i> Copying...');
    $btn.prop('disabled', true);
    
    $.post("/workout/copy_session", {
        source_date: sourceDate,
        target_date: targetDate
    }, function(response) {
        $btn.html(originalContent);
        $btn.prop('disabled', false);
        
        if (response.success) {
            alert("Workout copied successfully!");
            // Invalidate session cache for target date since we've modified it
            const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
            if (cachedSessions[targetDate]) {
                delete cachedSessions[targetDate];
                setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
            }
            $("#copyWorkoutModal").modal("hide");
        } else {
            alert("Error: " + response.error);
        }
    }).fail(function() {
        $btn.html(originalContent);
        $btn.prop('disabled', false);
        alert("Network error. Please try again.");
    });
}

function navigateWeek(direction) {
    const days = direction === 'prev' ? -7 : 7
    currentDate.setDate(currentDate.getDate() + days);
    const weekDates = getWeekDates(currentDate);
    renderWeekDates(weekDates);
}