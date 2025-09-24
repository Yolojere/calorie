// File: render.js
// ===== RENDERING FUNCTIONS =====
function renderWeekDates(dates) {
    const container = $("#week-dates-container");
    container.empty();

    const todayISO = new Date().toISOString().split('T')[0]; // today in UTC
    const weekdayKeys = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dates.forEach(date => {
        // Force UTC parsing to avoid local timezone shifts
        const dateObj = new Date(date + 'T00:00Z'); 

        // Use en-GB locale for weekday names (Mon, Tue...)
        const dayName = t(weekdayKeys[dateObj.getUTCDay()]);
        const dayNumber = dateObj.getUTCDate();

        // Compare ISO strings to mark today
        const isToday = date === todayISO;

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
        const selectedDate = $(this).data("date");
        selectDate(selectedDate);

        // Use cached version of session loading
        getSessionWithCache(selectedDate, function(data) {
            renderWorkoutSession(data.session, data.exercises);
        });
    });

    // Update week display
    const start = new Date(dates[0] + 'T00:00Z');
    const end = new Date(dates[6] + 'T00:00Z');

   const weekDisplay = `${t('weekDisplay')} ${getWeekNumber(start)}: ${formatDate(start)} - ${formatDate(end)}`;
    $("#week-display").text(weekDisplay);
}

function _escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/[&<>"'`=\/]/g, ch => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;'
    })[ch]);
}

// Robust renderer for both <select> and <input>+<datalist> patterns.
// It will attempt to refresh common select plugins (safe guards included).
function renderExerciseOptions() {
  const exList = Array.isArray(window.exercises) ? window.exercises : [];
  console.log('renderExerciseOptions() — exercises length:', exList.length);

  const mgEl = $('#muscle-group-select');
  const mgMobileEl = $('#muscle-group-select-mobile');

  const muscleGroup = (mgEl.val() || '').toLowerCase().trim();
  const muscleGroupMobile = (mgMobileEl.val() || '').toLowerCase().trim();

  // Targets we support (some projects use a <select>, some use <input> + <datalist>)
  const select = $('#exercise-select');                 // desktop <select>
  const selectMobile = $('#exercise-select-mobile');    // mobile <select>
  const input = $('#exercise-input');                   // possible input element
  const datalist = $('#exercise-datalist');            // possible <datalist>

  if (!select.length && !selectMobile.length && !input.length && !datalist.length) {
    console.warn('renderExerciseOptions: no #exercise-select/#exercise-select-mobile/#exercise-input/#exercise-datalist found in DOM');
    return;
  }

  // filter function: if muscle group empty or 'all' => show all
  const matchesGroup = (ex, mg) => {
    if (!mg || mg === 'all') return true;
    return ((ex.muscle_group || '').toLowerCase().trim() === mg);
  };

  const desktopExercises = exList.filter(ex => matchesGroup(ex, muscleGroup));
  const mobileExercises = exList.filter(ex => matchesGroup(ex, muscleGroupMobile));

  // Helper to refresh plugin UIs (guarded so it doesn't throw if plugin not present)
  const tryRefresh = (jq) => {
    try {
      if (!jq || !jq.length) return;
      // bootstrap-select
      if (typeof $.fn.selectpicker !== 'undefined') {
        jq.selectpicker && jq.selectpicker('refresh');
      }
      // select2
      if (jq.hasClass && jq.hasClass('select2-hidden-accessible')) {
        jq.trigger && jq.trigger('change.select2');
      }
      // Tom Select (vanilla: element.tomselect exists)
      if (jq[0] && jq[0].tomselect) {
        jq[0].tomselect.refresh && jq[0].tomselect.refresh();
      }
    } catch (e) {
      console.debug('refresh plugin failed (ignored):', e);
    }
  };

  // Populate <select> for desktop
  if (select.length) {
    const prev = select.val();
    select.empty();
    select.append(`<option value="">${t('selectExercise')}</option>`);
    desktopExercises.forEach(ex => {
      select.append(`<option value="${_escapeHtml(ex.id)}">${_escapeHtml(t(ex.name))}</option>`);
});
    if (prev && select.find(`option[value="${_escapeHtml(prev)}"]`).length) {
      select.val(prev);
    }
    tryRefresh(select);
    console.log('renderExerciseOptions: desktop options added:', desktopExercises.length);
  }

  // Populate <select> for mobile
  if (selectMobile.length) {
    const prevM = selectMobile.val();
    selectMobile.empty();
    selectMobile.append(`<option value="">${t('selectExercise')}</option>`);
    mobileExercises.forEach(ex => {
      selectMobile.append(`<option value="${_escapeHtml(ex.id)}">${_escapeHtml(t(ex.name))}</option>`);
});
    if (prevM && selectMobile.find(`option[value="${_escapeHtml(prevM)}"]`).length) {
      selectMobile.val(prevM);
    }
    tryRefresh(selectMobile);
    console.log('renderExerciseOptions: mobile options added:', mobileExercises.length);
  }

  // Populate datalist (input + datalist pattern)
  if (datalist.length) {
    datalist.empty();
    // datalist option uses the exercise name as value (inputs read option.value)
    desktopExercises.forEach(ex => {
      datalist.append(`<option value="${_escapeHtml(ex.name)}" data-id="${_escapeHtml(ex.id)}"></option>`);
    });
    console.log('renderExerciseOptions: datalist options added:', desktopExercises.length);
  }

  // If using an input and datalist - optionally you can add an event listener
  // that fills a hidden input with the selected exercise id by matching the datalist option.
  if (input.length && datalist.length && !input.data('exercise-listener')) {
    input.on('input', function () {
      const v = $(this).val();
      // find datalist option with value === v
      const opt = datalist.find(`option[value="${_escapeHtml(v)}"]`);
      const foundId = opt.length ? opt.attr('data-id') : '';
      // store id somewhere useful (example hidden field #exercise-id)
      $('#exercise-id').val(foundId || '');
    });
    input.data('exercise-listener', true);
  }

  // If nothing matched, help debugging:
  if ((select.length && select.find('option').length <= 1) && (datalist.length && datalist.find('option').length === 0)) {
    console.info('renderExerciseOptions: zero options after filtering — showing counts for debugging:');
    console.info('muscleGroup (selected):', muscleGroup, 'muscleGroupMobile:', muscleGroupMobile);
    console.info('all muscle groups present in exercises:', Array.from(new Set(exList.map(e=> (e.muscle_group||'').toLowerCase().trim()))));
  }
}

// Hook muscle-group selects so switching group re-renders options
$(document).ready(function () {
  $('#muscle-group-select, #muscle-group-select-mobile').on('change', renderExerciseOptions);
});

function renderWorkoutSession(session, exercises, options = {}) {
    const collapseGroups = options.collapseGroups || false;
    const container = $("#workout-session-container");
    container.empty();

    if (!session || !exercises || exercises.length === 0) {
        container.html(`<div class="alert alert-info">${t('no_workout_message')}</div>`);
        return;
    }

    const currentDate = $(".workout-date.active").data("date");
    if (!collapseState.groups[currentDate]) collapseState.groups[currentDate] = {};
    if (!collapseState.exercises[currentDate]) collapseState.exercises[currentDate] = {};

    // Group exercises by muscle group
    const groups = {};
    exercises.forEach(exercise => {
        const group = exercise.muscle_group;
        if (!groups[group]) groups[group] = { exercises: [], totalSets: 0, totalVolume: 0 };

        const uniqueSets = Array.isArray(exercise.sets) ? [...exercise.sets] : [];
        const exerciseVolume = uniqueSets.reduce((sum, set) => sum + set.volume, 0);
        const exerciseSets = uniqueSets.length;

        groups[group].exercises.push({ ...exercise, sets: uniqueSets, exerciseSets, exerciseVolume });
        groups[group].totalSets += exerciseSets;
        groups[group].totalVolume += exerciseVolume;
    });

    // Collapse groups/exercises if copy/template or collapseGroups option
    if (collapseGroups || isApplyingTemplate) {
        for (const groupName in groups) {
            collapseState.groups[currentDate][groupName] = { collapsed: true };
            groups[groupName].exercises.forEach(ex => collapseState.exercises[currentDate][ex.id] = true);
        }
        saveCollapseState();
        isApplyingTemplate = false;
    }

    // Render HTML
    let sessionHTML = '';

    for (const groupName in groups) {
        const groupData = groups[groupName];

        // Ensure collapse state exists
        if (!collapseState.groups[currentDate][groupName]) collapseState.groups[currentDate][groupName] = { collapsed: false };
        const groupCollapsed = collapseState.groups[currentDate][groupName].collapsed;

        let translatedGroupName = t(groupName.toLowerCase()) || groupName;

        let groupBlock = `
            <div class="workout-group ${groupName.toLowerCase()}" data-group="${groupName}">
                <div class="group-header">
                    <div class="d-flex align-items-center">
                        <div class="group-icon">
                            <i class="fas fa-${getMuscleIcon(groupName)}"></i>
                        </div>
                        <span class="group-title">${translatedGroupName}</span>
                    </div>
                    <div class="d-flex align-items-center">
                        <div class="group-summary">
                            <span class="summary-item">${groupData.totalSets} ${t('sets')}</span>
                            <span class="summary-item">${groupData.totalVolume.toFixed(1)} kg</span>
                        </div>
                        <div class="group-actions">
                            <button class="toggle-icon toggle-group" title="${groupCollapsed ? t('expand') : t('collapse')}">
                                <i class="fas fa-${groupCollapsed ? 'plus' : 'minus'}"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="group-items" style="${groupCollapsed ? 'display: none;' : ''}">
        `;

        // Sort exercises: completed last
        groupData.exercises.sort((a, b) => {
            const aDone = completedExercises[currentDate]?.[a.id];
            const bDone = completedExercises[currentDate]?.[b.id];
            if (aDone && !bDone) return 1;
            if (!aDone && bDone) return -1;
            return (a.order || 0) - (b.order || 0);
        });

        // Exercises
        groupData.exercises.forEach(exercise => {
            const exerciseCollapsed = collapseState.exercises[currentDate][exercise.id] || false;
            const expandedClass = exerciseCollapsed ? '' : 'expanded';
            const isCompleted = completedExercises[currentDate]?.[exercise.id] || false;
            const completedClass = isCompleted ? 'completed' : '';

            const exerciseName = exercise.name || 'Unknown Exercise';
            const translatedExerciseName = t(exerciseName);

            groupBlock += `
                <div class="exercise" data-exercise-id="${exercise.id}">
                    <div class="exercise-header ${expandedClass} ${completedClass}">
                        <div class="exercise-header-content">
                            <div class="complete-exercise-dropdown">
                                <button class="complete-exercise-icon">
                                    <i class="fas fa-check ${isCompleted ? 'completed' : ''}"></i>
                                </button>
                                <div class="complete-exercise-options">
                                    <div class="complete-option" data-value="yes"><i class="fa-solid fa-check"></i>&nbsp;&nbsp;${t('valmis')}</div>
                                    <div class="complete-option" data-value="no"><i class="fa-solid fa-xmark"></i>&nbsp;&nbsp;${t('hylkaa')}</div>
                                    <div class="complete-option quick-add-set" data-value="quick-add"><i class="fa-solid fa-circle-plus"></i>&nbsp;&nbsp;${t('lisaaSarja')}</div>
                                </div>
                            </div>
                            <div class="exercise-title">${translatedExerciseName}</div>
                        </div>
                        <div class="exercise-info">
                            <div class="exercise-summary-text">
                                ${exercise.exerciseSets} ${t('sets')}, ${exercise.exerciseVolume.toFixed(1)} kg
                            </div>
                            <button class="toggle-icon toggle-exercise" title="${exerciseCollapsed ? 'Expand' : 'Collapse'}">
                                <i class="fas fa-${exerciseCollapsed ? 'plus' : 'minus'}"></i>
                            </button>
                        </div>
                    </div>
                    <div class="exercise-sets" style="${exerciseCollapsed ? 'display:none;' : ''}">
                        <table class="workout-table">
                            <thead>
                                <tr>
                                    <th>${t('set')}</th><th>${t('reps')}</th><th>${t('weight')}</th><th>${t('volume')}</th><th>${t('actions')}</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            exercise.sets.forEach((set, index) => {
                const rirText = (set.rir === -1 || set.rir === 0 || set.rir === "Failure") ? 'Failure' : `${set.rir} RiR`;
                const rirDisplay = `
                    <div class="rir-dropdown">
                        <span class="rir-badge">${set.rir != null ? rirText : 'None'}</span>
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
                const commentIcon = set.comments ? 
                    `<i class="fas fa-comment comment-icon" data-comment="${set.comments.replace(/"/g, '&quot;')}"></i>` :
                    `<i class="far fa-comment comment-icon" data-comment=""></i>`;

                groupBlock += `
                    <tr class="set-row" data-set-id="${set.id}">
                        <td><div>${index+1}${rirDisplay}${commentIcon}</div></td>
                        <td><input type="number" class="form-control set-reps set-input" value="${set.reps}" data-original="${set.reps}"></td>
                        <td><input type="number" class="form-control set-weight set-input" value="${set.weight}" data-original="${set.weight}" step="0.5"></td>
                        <td class="volume-display">${set.volume.toFixed(1)}</td>
                        <td><button class="btn delete-item"><i class="fas fa-trash"></i></button></td>
                    </tr>
                `;
            });

            groupBlock += `</tbody></table></div></div>`;
        });

        groupBlock += `</div></div>`;
        sessionHTML += groupBlock;
    }

    container.html(sessionHTML);

    // Init helpers
    initTooltips();
    setTimeout(initTooltips, 100);
    setupRirDropdowns();
    setupCommentTooltips();
    setupExerciseCompletion();

    // Group toggle
    $(".toggle-group").off("click").on("click", function() {
        const $group = $(this).closest(".workout-group");
        const groupName = $group.data("group");
        const groupItems = $group.find(".group-items");
        const isExpanded = groupItems.is(":visible");

        groupItems.toggle(!isExpanded);
        $(this).html(`<i class="fas fa-${isExpanded ? 'plus' : 'minus'}"></i>`);
        $(this).attr('title', isExpanded ? 'Expand' : 'Collapse');

        collapseState.groups[currentDate][groupName].collapsed = isExpanded;
        saveCollapseState();
    });

    // Exercise toggle
    $(".toggle-exercise").off("click").on("click", function() {
        const $exercise = $(this).closest(".exercise");
        const exerciseId = $exercise.data("exercise-id");
        const exerciseSets = $exercise.find(".exercise-sets");
        const isExpanded = exerciseSets.is(":visible");

        exerciseSets.toggle(!isExpanded);
        $(this).html(`<i class="fas fa-${isExpanded ? 'plus' : 'minus'}"></i>`);
        $(this).attr('title', isExpanded ? 'Expand' : 'Collapse');
        $exercise.find(".exercise-header").toggleClass("expanded", !isExpanded);

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

    const todayUTC = new Date(Date.UTC(
        new Date().getUTCFullYear(),
        new Date().getUTCMonth(),
        new Date().getUTCDate()
    ));

    const currentDateUTC = currentSelectedDate 
        ? new Date(currentSelectedDate + 'T00:00Z')
        : todayUTC;

    for (let i = 0; i < 7; i++) {
        // add days in UTC
        const date = new Date(Date.UTC(
            todayUTC.getUTCFullYear(),
            todayUTC.getUTCMonth(),
            todayUTC.getUTCDate() + i
        ));

        const dateString = `${date.getUTCFullYear()}-${pad2(date.getUTCMonth()+1)}-${pad2(date.getUTCDate())}`;

        const formattedDate = date.toLocaleDateString('fi-FI', { 
            weekday: 'short', 
            day: 'numeric', 
            month: 'short' 
        });

        const isCurrent = dateString === `${currentDateUTC.getUTCFullYear()}-${pad2(currentDateUTC.getUTCMonth()+1)}-${pad2(currentDateUTC.getUTCDate())}`;

        container.append(`
            <div class="date-option btn btn-dark m-1 border-secondary ${isCurrent ? 'disabled' : ''}"
                 data-date="${dateString}"
                 ${isCurrent ? 'disabled' : ''}>
                ${formattedDate}
            </div>
        `);
    }
}

// Helper
function pad2(n){ return String(n).padStart(2,'0'); }

// Show animated analysis overlay
function showWorkoutAnalysis() {
    const overlay = $(`
        <div class="workout-analysis-overlay" id="workout-analysis">
            <div class="analysis-content">
                <div class="spinning-dumbbell">
                    <i class="fas fa-dumbbell"></i>
                </div>
                <div class="analysis-text">${t('analyzingWorkout')}</div>
                <div class="analysis-subtext" id="analysis-stage">${t('comparingSessions')}</div>
                <div class="analysis-progress">
                    <div class="analysis-progress-bar" id="progress-bar"></div>
                </div>
            </div>
        </div>
    `);
    
    $('body').append(overlay);
    
    // Animate progress bar and update text
    let progress = 0;
    const stages = [
        t('comparingSessions'),
        t('detectingPRs'),
        t('calculatingTrends'),
        t('finalizingAnalysis')
    ];
    
    const progressInterval = setInterval(() => {
        progress += 25;
        $('#progress-bar').css('width', progress + '%');
        
        if (progress <= 100) {
            const stageIndex = Math.floor((progress - 1) / 25);
            $('#analysis-stage').text(stages[stageIndex] || stages[0]);
        }
        
        if (progress >= 100) {
            clearInterval(progressInterval);
        }
    }, 1000);
}

// Hide analysis overlay
function hideWorkoutAnalysis() {
    $('#workout-analysis').fadeOut(300, function() {
        $(this).remove();
    });
}

// Show workout results with achievements and PRs
function showWorkoutResults(comparisonData, achievements) {
    // Handle undefined data gracefully
    comparisonData = comparisonData || {};
    achievements = achievements || {};
    
    // Calculate key metrics
    const totalVolume = comparisonData.totalVolume || 0;
    const volumeChange = comparisonData.volumeChange || 0;
    const personalRecords = achievements.personalRecords || [];
    const improvements = achievements.improvements || [];
    
    let resultsHTML = `
        <div class="workout-results-modal" id="workout-results">
            <div class="results-header">
                <h2 class="results-title">${t('workoutComplete')}</h2>
                <div class="results-subtitle">${t('performanceAnalysis')}</div>
            </div>
            <div class="results-body">
    `;
    
    // Show PR celebrations if any
    if (personalRecords.length > 0) {
    personalRecords.forEach(pr => {
        if (pr.type === 'bestSet') {
            resultsHTML += `
                <div class="pr-celebration">
                    <div class="pr-trophy">🏆</div>
                    <div class="pr-text">${t('newBestSet')}</div>
                    <div class="pr-details">${pr.exercise}: ${pr.weight}kg x ${pr.reps} toistoa</div>
                    <div class="pr-details">${t('previousBest')}: ${pr.previousBest.weight}kg x ${pr.previousBest.reps} toistoa</div>
                </div>`;
        } else if (pr.type === 'heaviestWeight') {
            resultsHTML += `
                <div class="pr-celebration">
                    <div class="pr-trophy">🏆</div>
                    <div class="pr-text">${t('heaviestWeight')}</div>
                    <div class="pr-details">${pr.exercise}: ${pr.weight}kg</div>
                    <div class="pr-details">${t('previousBest')}: ${pr.previousBest.weight}kg</div>
                </div>`;
        }
    });
}
    
    // Achievement cards
    resultsHTML += `
        <div class="achievement-grid">
            <div class="achievement-card">
                <div class="achievement-icon">💪</div>
                <div class="achievement-title">${t('totalVolume')}</div>
                <div class="achievement-value">${totalVolume.toLocaleString()} kg</div>
                <div class="achievement-change ${volumeChange > 0 ? 'improvement' : volumeChange < 0 ? 'decline' : 'neutral'}">
                    <i class="fas fa-${volumeChange > 0 ? 'arrow-up' : volumeChange < 0 ? 'arrow-down' : 'minus'}"></i>
                    ${Math.abs(volumeChange).toFixed(1)}% ${t('fromLastWorkout')}
                </div>
            </div>
            
            <div class="achievement-card">
                <div class="achievement-icon">🎯</div>
                <div class="achievement-title">${t('setsCompleted')}</div>
                <div class="achievement-value">${comparisonData.totalSets || 0}</div>
                <div class="achievement-change ${comparisonData.setsChange > 0 ? 'improvement' : 'neutral'}">
                    <i class="fas fa-${comparisonData.setsChange > 0 ? 'plus' : 'check'}"></i>
                    ${comparisonData.setsChange > 0 ? '+' : ''}${comparisonData.setsChange || 0} ${t('fromLastWorkout')}
                </div>
            </div>
            
            <div class="achievement-card">
                <div class="achievement-icon">⚡</div>
               <div class="achievement-title">${t('personalRecords')}</div>
                <div class="achievement-value">${personalRecords.length}</div>
                <div class="achievement-change improvement">
                    <i class="fas fa-trophy"></i>
                    ${personalRecords.length > 0 ? t('newRecordsToday') : t('keepPushing')}
                </div>
            </div>
            
            <div class="achievement-card">
                <div class="achievement-icon">📈</div>
                <div class="achievement-title">${t('improvements')}</div>
                <div class="achievement-value">${improvements.length}</div>
                <div class="achievement-change improvement">
                    <i class="fas fa-trending-up"></i>
                    ${improvements.length > 0 ? t('setsImproved') : t('greatEffort')}
                </div>
            </div>
        </div>
    `;
    
    // Close button <button LETS USE THIS IN FUTURE FOR SHARING !!! class="btn-results btn-primary-results" onclick="shareWorkout()">${t('shareResults')}</button> 
            resultsHTML += `
            </div>
            <div class="results-actions">
             
                <button class="btn-results btn-secondary-results" onclick="hideWorkoutResults()">
                    ${t('close')}
                </button>
                <button 
                    class="btn-results btn-primary-results" 
                    onclick="openCopyWorkoutModal()">
                    ${t('copy')}
                </button>
            </div>
        </div>
            `;
                
    $('body').append(resultsHTML);
    
    // Auto-hide after 15 seconds if user doesn't interact
    setTimeout(() => {
        if ($('#workout-results').is(':visible')) {
            hideWorkoutResults();
        }
    }, 45000);
}

// Hide workout results
function hideWorkoutResults() {
    $('#workout-results').fadeOut(300, function() {
        $(this).remove();
    });
}

// Update set rows with progress indicators
function updateSetRowsWithProgress(comparisonData) {
    if (!comparisonData || !comparisonData.setComparisons) return;
    
    comparisonData.setComparisons.forEach(comparison => {
        const $setRow = $(`.set-row[data-set-id="${comparison.setId}"]`);
        if ($setRow.length === 0) return;
        if (comparison.noPrevious) {
        $setRow.find('.set-progress-indicator').remove();
        const indicator = $(`<div class="set-progress-indicator first-session">${t('firstSession')}</div>`);
        $setRow.find('.volume-display').css('position', 'relative').append(indicator);
        return;
    }
        // Add progress indicator
        const progressClass = comparison.volumeChange > 0 ? 'progress-up' : 
                             comparison.volumeChange < 0 ? 'progress-down' : 'progress-new';
        const changeText = comparison.isNew ? 'NEW' : 
                          comparison.volumeChange > 0 ? `+${comparison.volumeChange.toFixed(1)}kg` :
                          comparison.volumeChange < 0 ? `${comparison.volumeChange.toFixed(1)}kg` : '=';
        
        // Remove existing indicators
        $setRow.find('.set-progress-indicator').remove();
        
        // Add new indicator
        const indicator = $(`<div class="set-progress-indicator ${progressClass}">${changeText}</div>`);
        $setRow.find('.volume-display').css('position', 'relative').append(indicator);
        
        // Add row animation
        if (comparison.volumeChange > 0) {
            $setRow.addClass('improved');
        } else if (comparison.volumeChange < 0) {
            $setRow.addClass('declined');
        }
        
        // Add tooltip with detailed comparison
        $setRow.attr('title', 
            `Previous: ${comparison.previousWeight}kg x ${comparison.previousReps} reps (${comparison.previousVolume.toFixed(1)}kg)\\n` +
            `Current: ${comparison.currentWeight}kg x ${comparison.currentReps} reps (${comparison.currentVolume.toFixed(1)}kg)\\n` +
            `Change: ${comparison.volumeChange > 0 ? '+' : ''}${comparison.volumeChange.toFixed(1)}kg`
        ).tooltip();
    });
}

// Share workout (optional feature)
function shareWorkout() {
    // Create a simple share text
    const shareText = `Just completed an amazing workout! 💪\\n` +
                     `Check out my progress on the TrackYou app!`;
    
    if (navigator.share) {
        navigator.share({
            title: 'My Workout Results',
            text: shareText,
            url: window.location.href
        });
    } else {
        // Fallback - copy to clipboard
        navigator.clipboard.writeText(shareText).then(() => {
            alert('Workout results copied to clipboard!');
        }).catch(() => {
            alert('Share feature not supported on this device');
        });
    }
    
    hideWorkoutResults();
}

// Click outside to close results
$(document).on('click', '.workout-results-modal', function(e) {
    if (e.target === this) {
        hideWorkoutResults();
    }
});

// Escape key to close results
$(document).on('keydown', function(e) {
    if (e.key === 'Escape' && $('#workout-results').is(':visible')) {
        hideWorkoutResults();
    }
});


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
        const sourceDate = $(".workout-date.active").data("date");
    if (sourceDate) {
        $("#copyWorkoutModal").data("source-date", sourceDate);
    }
    if (!window.calendarState.currentMonth) {
        window.calendarState.currentMonth = new Date(Date.UTC(today.getFullYear(), today.getMonth(), 1));
    }
    
    // FIXED: Force render the calendar immediately
    setTimeout(() => {
        window.renderCalendar(window.calendarState.currentMonth);
    }, 100); // Small delay to ensure modal is fully rendered
});
    // glow up on date selector copy button
    $(document).on("click", ".date-option", function() {
    $(".date-option").removeClass("active");
    $(this).addClass("active");
    copyWorkoutToDate($(this).data("date"));
});
function hideEmptyWorkoutGroups() {
    const currentDate = $(".workout-date.active").data("date");
    
    // First, remove empty exercises
    $('.exercise').each(function() {
        const $exercise = $(this);
        const $sets = $exercise.find('.set-row');
        
        if ($sets.length === 0) {
            // Remove from collapse state
            const exerciseId = $exercise.data('exercise-id');
            if (collapseState.exercises[currentDate] && collapseState.exercises[currentDate][exerciseId]) {
                delete collapseState.exercises[currentDate][exerciseId];
            }
            
            $exercise.fadeOut(300, function() {
                $(this).remove();
            });
        }
    });
    
    // Then, remove empty groups after exercises have been processed
    setTimeout(() => {
        $('.workout-group').each(function() {
            const $group = $(this);
            const $exercises = $group.find('.exercise');
            
            if ($exercises.length === 0) {
                // Remove from collapse state
                const groupName = $group.data('group');
                if (collapseState.groups[currentDate] && collapseState.groups[currentDate][groupName]) {
                    delete collapseState.groups[currentDate][groupName];
                }
                
                $group.fadeOut(300, function() {
                    $(this).remove();
                    
                    // If no groups left, show empty state
                    if ($('.workout-group').length === 0) {
                        $('#workout-session-container').html(`<div class="alert alert-info">${t('no_workout_message')}</div>`);
                    }
                });
            }
        });
        
        // Save the updated collapse state
        saveCollapseState();
    }, 350); // Slightly longer than the fadeOut duration
}
