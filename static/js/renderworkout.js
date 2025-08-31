console.log("renderworkout.js started");
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

function renderWorkoutSession(session, exercises) {
    const container = $("#workout-session-container");
    container.empty();
    
    if (!session || !exercises || exercises.length === 0) {
        const message = `
            <div class="alert alert-info">
                No workout recorded for this day. Add your first set below!
            </div>
        `;
        container.html(message);
        return;
    }
    
    // Get current date for state tracking
    const currentDate = $(".workout-date.active").data("date");
    
    // Initialize state for current date if needed
    if (!collapseState.groups[currentDate]) {
        collapseState.groups[currentDate] = {};
    }
    if (!collapseState.exercises[currentDate]) {
        collapseState.exercises[currentDate] = {};
    }
    
    // Group exercises by muscle group
    const groups = {};
    exercises.forEach(exercise => {
        const group = exercise.muscle_group;
        if (!groups[group]) {
            groups[group] = {
                exercises: [],
                totalSets: 0,
                totalReps: 0,
                totalVolume: 0
            };
        }

        // Calculate exercise totals
        const exerciseVolume = exercise.sets.reduce((sum, set) => sum + set.volume, 0);
        const exerciseSets = exercise.sets.length;
        const exerciseReps = exercise.sets.reduce((sum, set) => sum + set.reps, 0);

        groups[group].exercises.push({...exercise, exerciseVolume, exerciseSets, exerciseReps});
        groups[group].totalSets += exerciseSets;
        groups[group].totalReps += exerciseReps;
        groups[group].totalVolume += exerciseVolume;
    });

    // Apply template collapse if needed
    if (isApplyingTemplate) {
        for (const groupName in groups) {
            collapseState.groups[currentDate][groupName] = { collapsed: true };
            groups[groupName].exercises.forEach(exercise => {
                collapseState.exercises[currentDate][exercise.id] = true;
            });
        }
        saveCollapseState();
        isApplyingTemplate = false;
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
            return 0;
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
