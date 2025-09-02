console.log("renderworkout.js started");
console.log('Rendering session', currentDate, session, exercises);
// File: render.js
// ===== RENDERING FUNCTIONS =====
function renderWeekDates(dates) {
    const container = $("#week-dates-container");
    container.empty();
    
    dates.forEach(date => {
        const dateObj = new Date(date);
        const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
        const dayNumber = dateObj.getDate();
        const isToday = date === new Date().toISOString().split('T')[0];
        
        const dateElement = `
            <div class="workout-date btn btn-outline-secondary mx-1 ${isToday ? 'active' : ''}" 
                 data-date="${date}">
                <div>${dayName}</div>
                <div class="fw-bold">${dayNumber}</div>
            </div>
        `;
        container.append(dateElement);
    });
    
    // Add click event to dates
    $(".workout-date").click(function() {
        $(".workout-date").removeClass("active");
        $(this).addClass("active");
        currentSelectedDate = $(this).data("date");
        // Use cached version of session loading
        getSessionWithCache($(this).data("date"), function(data) {
            renderWorkoutSession(data.session, data.exercises);
        });
    });
    
    // Update week display
    const start = new Date(dates[0]);
    const end = new Date(dates[6]);
    const weekDisplay = `Week ${getWeekNumber(start)}: ${formatDate(start)} - ${formatDate(end)}`;
    $("#week-display").text(weekDisplay);
}

function renderExerciseOptions() {
    const muscleGroup = $("#muscle-group-select").val();
    const select = $("#exercise-select");
    const currentExercise = select.val();
    
    const muscleGroupMobile = $("#muscle-group-select-mobile").val();
    const selectMobile = $("#exercise-select-mobile");
    const currentExerciseMobile = selectMobile.val();
    
    // Clear both selects
    select.empty();
    selectMobile.empty();
    
    // Filter exercises by muscle group and populate both selects
    exercises
        .filter(ex => ex.muscle_group === muscleGroup)
        .forEach(exercise => {
            select.append(`<option value="${exercise.id}">${exercise.name}</option>`);
        });
        
    exercises
        .filter(ex => ex.muscle_group === muscleGroupMobile)
        .forEach(exercise => {
            selectMobile.append(`<option value="${exercise.id}">${exercise.name}</option>`);
        });
    
    // Restore previous selections if they still exist
    if (currentExercise && select.find(`option[value="${currentExercise}"]`).length) {
        select.val(currentExercise);
    }
    
    if (currentExerciseMobile && selectMobile.find(`option[value="${currentExerciseMobile}"]`).length) {
        selectMobile.val(currentExerciseMobile);
    }
}

function renderWorkoutSession(session, exercises, options = {}) {
    const collapseGroups = options.collapseGroups || false;
    const container = $("#workout-session-container");
    container.empty();

    if (!session || !exercises || exercises.length === 0) {
        container.html(`<div class="alert alert-info">No workout recorded for this day. Add your first set below!</div>`);
        return;
    }

    const currentDate = $(".workout-date.active").data("date");
    if (!collapseState.groups[currentDate]) collapseState.groups[currentDate] = {};
    if (!collapseState.exercises[currentDate]) collapseState.exercises[currentDate] = {};

    // Group exercises by muscle group
    const groups = {};
    exercises.forEach(exercise => {
        const group = exercise.muscle_group;
        if (!groups[group]) {
            groups[group] = { exercises: [], totalSets: 0, totalVolume: 0 };
        }

        // Prevent duplicate sets
        const uniqueSets = Array.isArray(exercise.sets) ? [...exercise.sets] : [];
        const exerciseVolume = uniqueSets.reduce((sum, set) => sum + set.volume, 0);
        const exerciseSets = uniqueSets.length;

        groups[group].exercises.push({...exercise, sets: uniqueSets, exerciseSets, exerciseVolume});
        groups[group].totalSets += exerciseSets;
        groups[group].totalVolume += exerciseVolume;
    });

    // If copied workout or template, collapse groups by default
    if (collapseGroups || isCopiedWorkout || isApplyingTemplate) {
        for (const groupName in groups) {
            collapseState.groups[currentDate][groupName] = { collapsed: true };
            groups[groupName].exercises.forEach(exercise => {
                collapseState.exercises[currentDate][exercise.id] = true;
            });
        }
        saveCollapseState();
        isApplyingTemplate = false; // reset template flag
    }

    // Render session
    let sessionHTML = '';

    for (const groupName in groups) {
        // Ensure group state exists
        if (!collapseState.groups[currentDate][groupName]) {
            collapseState.groups[currentDate][groupName] = { collapsed: false };
        }

        const groupData = groups[groupName];
        const groupState = collapseState.groups[currentDate][groupName];
        const groupCollapsed = groupState.collapsed;

        let groupBlock = `
            <div class="workout-group ${groupName.toLowerCase()}" data-group="${groupName}">
                <div class="group-header">
                    <div class="d-flex align-items-center">
                        <div class="group-icon">
                            <i class="fas fa-${getMuscleIcon(groupName)}"></i>
                        </div>
                        <span class="group-title">${groupName}</span>
                    </div>
                    <div class="d-flex align-items-center">
                        <div class="group-summary">
                            <span class="summary-item">${groupData.totalSets} sets</span>
                            <span class="summary-item">${groupData.totalVolume.toFixed(1)} kg</span>
                        </div>
                        <div class="group-actions">
                            <button class="toggle-icon toggle-group" title="${groupCollapsed ? 'Expand' : 'Collapse'}">
                                <i class="fas fa-${groupCollapsed ? 'plus' : 'minus'}"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="group-items" style="${groupCollapsed ? 'display: none;' : ''}">
        `;

        // Sort exercises: completed ones last
        groupData.exercises.sort((a, b) => {
    const aCompleted = completedExercises[currentDate] && completedExercises[currentDate][a.id];
    const bCompleted = completedExercises[currentDate] && completedExercises[currentDate][b.id];

    if (aCompleted && !bCompleted) return 1;
    if (!aCompleted && bCompleted) return -1;

    // Both completed or both not completed -> preserve creation/order
    return (a.order || 0) - (b.order || 0);
});

        // Render exercises
        groupData.exercises.forEach(exercise => {
            const exerciseCollapsed = collapseState.exercises[currentDate][exercise.id] || false;
            const expandedClass = exerciseCollapsed ? '' : 'expanded';
            const isCompleted = completedExercises[currentDate] && completedExercises[currentDate][exercise.id];
            const completedClass = isCompleted ? 'completed' : '';

            groupBlock += `
                <div class="exercise" data-exercise-id="${exercise.id}">
                    <div class="exercise-header ${expandedClass} ${completedClass}">
                        <div class="exercise-header-content">
                            <div class="complete-exercise-dropdown">
                                <button class="complete-exercise-icon">
                                    <i class="fas fa-check ${isCompleted ? 'completed' : ''}"></i>
                                </button>
                                <div class="complete-exercise-options">
                                    <div class="complete-option" data-value="asdadasd">Complete Exercise?</div>
                                    <div class="complete-option" data-value="yes">✔️ Yes</div>
                                    <div class="complete-option" data-value="no">❌ No</div>
                                     <div class="complete-option quick-add-set" data-value="quick-add">➕ Quick Add Set</div>
                                </div>
                            </div>
                            <div class="exercise-title">${exercise.name}</div>
                        </div>
                        <div class="exercise-info">
                            <div class="exercise-summary-text">
                                ${exercise.exerciseSets} sets, ${exercise.exerciseVolume.toFixed(1)} kg
                            </div>
                            <button class="toggle-icon toggle-exercise" title="${exerciseCollapsed ? 'Expand' : 'Collapse'}">
                                <i class="fas fa-${exerciseCollapsed ? 'plus' : 'minus'}"></i>
                            </button>
                        </div>
                    </div>
                    <div class="exercise-sets" style="${exerciseCollapsed ? 'display: none;' : ''}">
                        <table class="workout-table">
                            <thead>
                                <tr>
                                    <th class="text-center">Set</th>
                                    <th class="text-center">Reps</th>
                                    <th class="text-center">Weight</th>
                                    <th class="text-center">Volume</th>
                                    <th class="text-center">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            exercise.sets.forEach((set, index) => {
                let rirDisplay = '';
                if (set.rir !== null && set.rir !== undefined && set.rir !== "") {
                    let rirText = (set.rir === -1 || set.rir === "Failure" || set.rir === 0) ? 'Failure' : `${set.rir} RiR`;
                    rirDisplay = `
                        <div class="rir-dropdown">
                            <span class="rir-badge">${rirText}</span>
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
                } else {
                    // If no RiR is set, show "None" and allow setting it
                    rirDisplay = `
                        <div class="rir-dropdown">
                            <span class="rir-badge">None</span>
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
                }

                const commentIcon = set.comments ? 
                    `<i class="fas fa-comment comment-icon" data-comment="${set.comments.replace(/"/g, '&quot;')}"></i>` :
                    `<i class="far fa-comment comment-icon" data-comment=""></i>`;

                groupBlock += `
                    <tr class="set-row" data-set-id="${set.id}">
                        <td class="set-number-cell">
                            <div class="d-flex align-items-center">
                                <div class="me-2">${index + 1}</div>
                                <div class="set-details">
                                    ${rirDisplay}
                                    ${commentIcon}
                                </div>
                            </div>
                        </td>
                        <td>
                            <input type="number" class="form-control set-reps set-input" 
                                value="${set.reps}" data-original="${set.reps}">
                        </td>
                        <td>
                            <input type="number" class="form-control set-weight set-input" 
                                value="${set.weight}" data-original="${set.weight}" step="0.5">
                        </td>
                        <td class="volume-display">${set.volume.toFixed(1)}</td>
                        <td class="actions-cell">
                            <button class="btn delete-item">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });

            groupBlock += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        });

        groupBlock += `
                </div>
            </div>
        `;

        sessionHTML += groupBlock;
    }

    container.html(sessionHTML);
    initTooltips();
    setTimeout(initTooltips, 100);
    
    // Setup the RiR dropdowns and comment tooltips
    setupRirDropdowns();
    setupCommentTooltips();
    setupExerciseCompletion();

    // Apply initial expanded class
    $(".exercise").each(function() {
        const exerciseId = $(this).data("exercise-id");
        const currentDate = $(".workout-date.active").data("date");
        const isCollapsed = collapseState.exercises[currentDate]?.[exerciseId] || false;
        const header = $(this).find(".exercise-header");
        if (!isCollapsed) {
            header.addClass("expanded");
        }
    });

    // Group toggle
    $(".toggle-group").click(function() {
        const groupHeader = $(this).closest(".group-header");
        const groupContainer = groupHeader.closest(".workout-group");
        const groupItems = groupContainer.find(".group-items");
        const isExpanded = groupItems.is(":visible");
        const groupName = groupContainer.data("group");
        const currentDate = $(".workout-date.active").data("date");

        groupItems.toggle(!isExpanded);
        $(this).html(`<i class="fas fa-${isExpanded ? 'plus' : 'minus'}"></i>`);
        $(this).attr('title', isExpanded ? 'Expand' : 'Collapse');

        collapseState.groups[currentDate][groupName].collapsed = isExpanded;
        saveCollapseState();
    });

    // Exercise toggle
    $(".toggle-exercise").click(function() {
        const exerciseHeader = $(this).closest(".exercise-header");
        const exerciseContainer = exerciseHeader.closest(".exercise");
        const exerciseId = exerciseContainer.data("exercise-id");
        const exerciseSets = exerciseContainer.find(".exercise-sets");
        const isExpanded = exerciseSets.is(":visible");
        const currentDate = $(".workout-date.active").data("date");

        exerciseSets.toggle(!isExpanded);
        $(this).html(`<i class="fas fa-${isExpanded ? 'plus' : 'minus'}"></i>`);
        $(this).attr('title', isExpanded ? 'Expand' : 'Collapse');

        if (isExpanded) {
            exerciseHeader.removeClass("expanded");
        } else {
            exerciseHeader.addClass("expanded");
        }

        collapseState.exercises[currentDate][exerciseId] = isExpanded;
        saveCollapseState();
    });
    
    $(document).trigger('workoutContentChanged');
    $(document).trigger('workoutRendered');
}
function renderTemplatePreview(templateData) {
    const grouped = {};

    // Aggregate sets by muscle group + exercise
    templateData.exercises.forEach(item => {
        const group = item.muscle_group || "Other";
        if (!grouped[group]) grouped[group] = {};

        if (!grouped[group][item.exercise]) {
            grouped[group][item.exercise] = 0;
        }
        grouped[group][item.exercise] += 1; // count sets
    });

    // Build HTML
    let html = "";
    Object.keys(grouped).forEach(group => {
        html += `<div class="mb-3">
            <h6 class="fw-bold text-primary border-bottom border-secondary pb-1">${group}</h6>
            <ul class="list-unstyled ps-3">`;

        Object.keys(grouped[group]).forEach(exercise => {
            const sets = grouped[group][exercise];
            html += `<li class="mb-1">
                        <span class="fw-semibold">${exercise}</span> × ${sets}
                     </li>`;
        });

        html += `</ul></div>`;
    });

    $("#template-preview-content").html(html);
}
function renderTemplates(templates) {
    const $templateListDesktop = $("#template-list-desktop");
    const $templateListMobile = $("#template-list-mobile");
    $templateListDesktop.empty();
    $templateListMobile.empty();
    
    if (templates && templates.length > 0) {
        templates.forEach(template => {
            const item = `
                <li><a class="dropdown-item template-item" href="#" 
                       data-id="${template.id}">${template.name}</a></li>
            `;
            $templateListDesktop.append(item);
            $templateListMobile.append(item);
        });
        
    } else {
        const noItem = '<li><a class="dropdown-item" href="#">No templates found</a></li>';
        $templateListDesktop.append(noItem);
        $templateListMobile.append(noItem);
    }
}

function populateDateOptions() {
    const container = $("#date-selection-container");
    container.empty();
    
    const today = new Date();
    const currentDate = new Date(currentSelectedDate);
    
    for (let i = 0; i < 7; i++) {
        const date = new Date();
        date.setDate(today.getDate() + i);
        const dateString = date.toISOString().split('T')[0];
        const formattedDate = date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric' 
        });
        
        const isCurrent = dateString === currentDate.toISOString().split('T')[0];
        
        container.append(`
            <div class="date-option btn btn-dark m-1 border-secondary ${isCurrent ? 'disabled' : ''}"
                 data-date="${dateString}"
                 ${isCurrent ? 'disabled' : ''}>
                ${formattedDate}
            </div>
        `);
    }
}
function getComparisonStyles(ex) {
    // Safe fallback in case currentSets not defined
    const currentSet = ex.currentSets && ex.currentSets[0] ? ex.currentSets[0] : { reps: 0, weight: 0 };

    const weightDiff = ex.lastWeight ? currentSet.weight - ex.lastWeight : 0;
    const repsDiff = ex.lastReps ? currentSet.reps - ex.lastReps : 0;
    const volumeDiff = ex.lastVolume ? (currentSet.reps * currentSet.weight) - ex.lastVolume : 0;

    return {
        weight: { value: currentSet.weight, diff: weightDiff, color: weightDiff > 0 ? "lime" : weightDiff < 0 ? "red" : "gray", icon: weightDiff > 0 ? "🔥" : "" },
        reps: { value: currentSet.reps, diff: repsDiff, color: repsDiff > 0 ? "lime" : repsDiff < 0 ? "red" : "gray", icon: repsDiff > 0 ? "🔥" : "" },
        volume: { value: currentSet.reps * currentSet.weight, diff: volumeDiff, color: volumeDiff > 0 ? "gold" : volumeDiff < 0 ? "red" : "gray", icon: volumeDiff > 0 ? "🏆" : "" }
    };
}

function renderComparisonUI(comparison, workoutId) {
    // Remove any previous UI
    $('.comparison-container, #comparison-backdrop').remove();

    // Add backdrop
    $('body').append('<div id="comparison-backdrop" class="comparison-backdrop show"></div>');

    // === Phase 0: Dumbbell loading ===
    const $loading = $(`
        <div class="comparison-container show" id="comparison-loading">
            <div class="text-center">
                <i class="fa-solid fa-dumbbell fa-4x mb-3 animate-spin"></i>
                <p>Analyzing your workout...</p>
            </div>
        </div>
    `);
    $('body').append($loading);

    setTimeout(() => {
        $loading.remove();

        // === Phase 1: Show exercises summary ===
        let html = `<div class="comparison-container" id="comparison-card">`;
        html += `<h5 class="mb-3">Performance vs Last Time</h5>`;

        if (!comparison || comparison.length === 0) {
            html += `<p>No previous data to compare yet.</p>`;
        } else {
            comparison.forEach((ex, exIndex) => {
                const totalVolume = ex.currentSets.reduce((sum, s) => sum + s.volume, 0);
                html += `
                    <div class="comparison-exercise mb-2" data-ex="${exIndex}">
                        <strong>${ex.name}</strong> - ${ex.currentSets.length} sets - ${totalVolume} volume
                        <div class="exercise-sets mt-1"></div>
                    </div>
                `;
            });
        }

        // Buttons
        html += `
            <div class="mt-3 text-center">
                <button id="copy-to-date-btn" class="btn btn-success copy-to-date-btn" data-id="${workoutId}">Copy to Another Date</button>
                <button class="btn btn-secondary ms-2 close-comparison-btn">Close</button>
            </div>
        </div>`;

        $('body').append(html);
        const $card = $('#comparison-card');
        setTimeout(() => $card.addClass("show"), 50);

        // === Phase 2: Slide in sets + reward icons ===
        comparison.forEach((ex, exIndex) => {
            const $exDiv = $(`.comparison-exercise[data-ex="${exIndex}"] .exercise-sets`);
            ex.currentSets.forEach((set, setIndex) => {
                const lastSet = ex.lastSets && ex.lastSets[setIndex] ? ex.lastSets[setIndex] : null;
                const weightDiff = lastSet ? set.weight - lastSet.weight : 0;
                const repsDiff = lastSet ? set.reps - lastSet.reps : 0;
                const volumeDiff = lastSet ? set.volume - lastSet.volume : 0;

                const icon = (volumeDiff > 0 ? "🏆" : (volumeDiff < 0 ? "⚡" : "")); // reward / negative
                setTimeout(() => {
                    $exDiv.append(`
                        <div class="set-row">
                            Set ${setIndex+1} - ${set.reps} reps - ${set.weight} kg - ${set.volume} vol ${icon}
                        </div>
                    `);
                }, setIndex * 200 + exIndex * 300);
            });
        });

        // === Phase 3: Final verdict ===
        setTimeout(() => {
            const positiveCount = comparison.reduce((sum, ex) => {
                return sum + ex.currentSets.reduce((s, set, i) => {
                    const lastSet = ex.lastSets && ex.lastSets[i] ? ex.lastSets[i] : null;
                    if (!lastSet) return s;
                    return s + ((set.volume - lastSet.volume) > 0 ? 1 : 0);
                }, 0);
            }, 0);

            let message = "Let's recover and kill it next time";
            if (positiveCount >= 3) message = "What was that? Insanity!";
            else if (positiveCount === 2) message = "That was a solid one :)";
            else if (positiveCount === 1) message = "Keep up the good work!";

            $card.append(`<div class="mt-3 final-message" style="font-size:1.5rem; font-weight:bold;">${message}</div>`);
        }, 1000 + comparison.length * 600);

    }, 1500); // Dumbbell loading duration

    // === Delegated events ===
    $(document).off('click', '.close-comparison-btn, #comparison-backdrop')
        .on('click', '.close-comparison-btn, #comparison-backdrop', () => {
            $('.comparison-container, #comparison-backdrop').remove();
        });

    $(document).off('click', '.copy-to-date-btn')
        .on('click', '.copy-to-date-btn', function() {
            const targetWorkoutId = $(this).data('id');
            console.log("Copy workout to id:", targetWorkoutId);
            // Add copy logic here
        });
}


function populateMobileDateSelector(selectedDate) {
    const $selector = $("#mobile-date-selector");
    const dates = generateDateOptions(selectedDate);
    
    $selector.empty();
    dates.forEach(d => {
        const selected = d.date === selectedDate;
        $selector.append(`<option value="${d.date}" ${selected ? 'selected' : ''}>${d.formatted}</option>`);
    });
}
// Navigation
let currentMonth = new Date();
$(document).on("click", ".month-nav.prev", function() {
    currentMonth.setMonth(currentMonth.getMonth() - 1);
    renderCalendar(currentMonth);
});
$(document).on("click", ".month-nav.next", function() {
    currentMonth.setMonth(currentMonth.getMonth() + 1);
    renderCalendar(currentMonth);
});

// Init on modal open
$('#copyWorkoutModal').on('shown.bs.modal', function() {
    renderCalendar(currentMonth);
});
    // glow up on date selector copy button
    $(document).on("click", ".date-option", function() {
    $(".date-option").removeClass("active");
    $(this).addClass("active");
    copyWorkoutToDate($(this).data("date"));
});
