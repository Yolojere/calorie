// File: render.js
// ===== RENDERING FUNCTIONS =====

// ===== WORKOUT TIMER FUNCTIONALITY =====
let workoutTimer = {
    startTime: null,
    endTime: null,
    isActive: false,
    lastActivity: null,
    totalSeconds: 0,
    intervalId: null,
    inactivityTimeout: null,
    pausedTime: 0,
    pausedAt: null
};
const TIMER_STORAGE_KEY = 'workoutTimer';
const TIMER_DATE_KEY = 'workoutTimerDate';

function saveTimerState() {
    if (!workoutTimer.startTime) return;
    
    const state = {
        startTime: workoutTimer.startTime.toISOString(),
        endTime: workoutTimer.endTime ? workoutTimer.endTime.toISOString() : null,
        isActive: workoutTimer.isActive,
        lastActivity: workoutTimer.lastActivity ? workoutTimer.lastActivity.toISOString() : null,
        totalSeconds: Math.floor(workoutTimer.totalSeconds || 0),        // ✅ Floor
        pausedTime: Math.floor(workoutTimer.pausedTime || 0),           // ✅ Floor
        pausedAt: workoutTimer.pausedAt ? workoutTimer.pausedAt.toISOString() : null
    };
    
    const currentDate = currentSelectedDate || new Date().toISOString().split('T')[0];
    localStorage.setItem(TIMER_STORAGE_KEY, JSON.stringify(state));
    localStorage.setItem(TIMER_DATE_KEY, currentDate);
}
function loadTimerState() {
    try {
        const storedState = localStorage.getItem(TIMER_STORAGE_KEY);
        const storedDate = localStorage.getItem(TIMER_DATE_KEY);
        
        if (!storedState || !storedDate) return false;
        
        const timerState = JSON.parse(storedState);
        const currentDate = currentSelectedDate || new Date().toISOString().split('T')[0];
        
        if (storedDate !== currentDate) {
            clearTimerState();
            return false;
        }
        
        // Restore timer state
        workoutTimer.startTime = new Date(timerState.startTime);
        workoutTimer.endTime = timerState.endTime ? new Date(timerState.endTime) : null;
        workoutTimer.lastActivity = timerState.lastActivity ? new Date(timerState.lastActivity) : null;
        workoutTimer.totalSeconds = Math.floor(timerState.totalSeconds || 0);
        workoutTimer.pausedTime = Math.floor(timerState.pausedTime || 0);
        workoutTimer.pausedAt = timerState.pausedAt ? new Date(timerState.pausedAt) : null;
        
        if (timerState.isActive && !workoutTimer.endTime) {
            // ✅ Timer was active - resume it WITHOUT adding refresh time as pause
            workoutTimer.isActive = true;
            workoutTimer.pausedAt = null; // ✅ CLEAR any pausedAt from refresh
            
            workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
            resetInactivityTimeout();
            showTimerDisplay();
            $('.timer-icon-clickable').addClass('active');
            $('.stop-timer-btn').html('<i class="fas fa-pause"></i> Keskeytä');
            console.log('🟢 Timer restored and resumed');
            return true;
        } else if (!timerState.isActive && !workoutTimer.endTime && workoutTimer.startTime) {
            // Timer was paused - show as paused
            workoutTimer.isActive = false;
            showTimerDisplay();
            updateTimerDisplay();
            $('.timer-icon-clickable').removeClass('active');
            $('.stop-timer-btn').html('<i class="fas fa-play"></i> Jatka');
            console.log('⏸️ Timer restored in paused state');
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('Error loading timer state:', error);
        clearTimerState();
        return false;
    }
}

// Clear timer state from localStorage
function clearTimerState() {
    localStorage.removeItem(TIMER_STORAGE_KEY);
    localStorage.removeItem(TIMER_DATE_KEY);
    console.log('🗑️ Timer state cleared');
}

// Resume timer after page load
function resumeTimer() {
    if (!workoutTimer.isActive || !workoutTimer.startTime) return;
    
    // Start the display update interval
    workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
    
    // Reset inactivity timeout
    resetInactivityTimeout();
    
    // Show timer display
    showTimerDisplay();
    
    console.log('▶️ Timer resumed');
}
// Start workout timer when first activity occurs
function startWorkoutTimer() {
    if (workoutTimer.isActive) {
        updateLastActivity();
        return;
    }
    
    console.log('🟢 Starting workout timer');
    workoutTimer.startTime = new Date();
    workoutTimer.isActive = true;
    workoutTimer.lastActivity = new Date();
    workoutTimer.endTime = null;
    
    saveTimerState();
    
    workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
    resetInactivityTimeout();
    
    // Show timer with active animation
    showTimerDisplay();
    $('.timer-icon-clickable').addClass('active');
}

// ✅ NEW: Separate resume function for when resuming from pause
function resumeWorkoutTimer() {
    console.log('▶️ Resuming workout timer');
    
    // Calculate and add paused duration
    if (workoutTimer.pausedAt) {
        const pauseDuration = Math.floor((new Date() - workoutTimer.pausedAt) / 1000);
        workoutTimer.pausedTime = Math.floor(workoutTimer.pausedTime + pauseDuration);
        workoutTimer.pausedAt = null;
        console.log(`Added ${pauseDuration}s to paused time. Total paused: ${workoutTimer.pausedTime}s`);
    }
    
    workoutTimer.isActive = true;
    workoutTimer.lastActivity = new Date();
    
    // Restart interval
    workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
    resetInactivityTimeout();
    
    // Save resumed state
    saveTimerState();
    
    // Update animation classes for active state
    $('.timer-icon-clickable')
        .removeClass('paused')
        .addClass('active');
    
    // Update button text
    $('.stop-timer-btn').html('<i class="fas fa-pause"></i> Keskeytä');
}

// ✅ FIXED: Pause function (keep timer state)
function pauseWorkoutTimer() {
    console.log('⏸️ Pausing workout timer');
    
    workoutTimer.isActive = false;
    workoutTimer.pausedAt = new Date();
    
    // Clear intervals but keep the timer state
    if (workoutTimer.intervalId) {
        clearInterval(workoutTimer.intervalId);
        workoutTimer.intervalId = null;
    }
    
    if (workoutTimer.inactivityTimeout) {
        clearTimeout(workoutTimer.inactivityTimeout);
        workoutTimer.inactivityTimeout = null;
    }
    
    // Save paused state to localStorage
    saveTimerState();
    
    // Update animation classes for paused state
    $('.timer-icon-clickable')
        .removeClass('active')
        .addClass('paused');
    
    // Update button text
    $('.stop-timer-btn').html('<i class="fas fa-play"></i> Jatka');
}

// ✅ UPDATED: Toggle function (this is what your button calls)
function toggleWorkoutTimer() {
    if (!workoutTimer.isActive && !workoutTimer.startTime) {
        // First time starting - use startWorkoutTimer
        startWorkoutTimer();
        $('.stop-timer-btn').html('<i class="fas fa-pause"></i> Keskeytä');
    } else if (!workoutTimer.isActive && workoutTimer.startTime) {
        // Resume from pause
        resumeWorkoutTimer();
    } else {
        // Pause active timer
        pauseWorkoutTimer();
    }
}

// ✅ KEEP: Stop function for complete termination (used when switching dates)
function stopWorkoutTimer(saveToHistory = false) {
    if (!workoutTimer.startTime) return;
    
    console.log('🔴 Stopping workout timer');
    workoutTimer.endTime = new Date();
    workoutTimer.isActive = false;
    
    // Clear intervals and timeouts
    if (workoutTimer.intervalId) {
        clearInterval(workoutTimer.intervalId);
        workoutTimer.intervalId = null;
    }
    if (workoutTimer.inactivityTimeout) {
        clearTimeout(workoutTimer.inactivityTimeout);
        workoutTimer.inactivityTimeout = null;
    }
    
    // Calculate total workout time
    if (workoutTimer.startTime && workoutTimer.endTime) {
        workoutTimer.totalSeconds = Math.floor((workoutTimer.endTime - workoutTimer.startTime) / 1000);
    }
    
    if (saveToHistory) {
        saveTimerState();
    } else {
        clearTimerState(); // Clear completely when switching dates
    }
    
    hideTimerDisplay();
}

// Update last activity time and reset inactivity timeout
function updateLastActivity() {
    workoutTimer.lastActivity = new Date();
    resetInactivityTimeout();
}

// Reset the 20-minute inactivity timeout
function resetInactivityTimeout() {
    if (workoutTimer.inactivityTimeout) {
        clearTimeout(workoutTimer.inactivityTimeout);
    }
    
    workoutTimer.inactivityTimeout = setTimeout(() => {
        console.log('⏰ Ajastin pysäytetty 30 min inaktiivisuuden takia');
        stopWorkoutTimer();
    }, 30 * 60 * 1000); // 30 minutes in milliseconds
}

// Update timer display in UI
function updateTimerDisplay() {
    if (!workoutTimer.startTime) return;
    
    const now = new Date();
    let elapsed;
    
    if (workoutTimer.isActive) {
        // ✅ Floor both calculations to avoid decimals
        elapsed = Math.floor((now - workoutTimer.startTime) / 1000) - Math.floor(workoutTimer.pausedTime);
    } else {
        // ✅ When paused, show time up to pause point
        const pauseTime = workoutTimer.pausedAt || now;
        elapsed = Math.floor((pauseTime - workoutTimer.startTime) / 1000) - Math.floor(workoutTimer.pausedTime);
    }
    
    // ✅ Ensure elapsed is never negative and is a whole number
    elapsed = Math.max(0, Math.floor(elapsed));
    
    const timeStr = formatTime(elapsed);
    
    // Update dropdown display
    $('.timer-display-text').text(timeStr);
    
    workoutTimer.totalSeconds = elapsed;
    if (workoutTimer.isActive) {
        saveTimerState();
    }
}
$(document).ready(function() {
    // Toggle timer dropdown
    $(document).on('click', '.timer-icon-clickable', function(e) {
        e.stopPropagation();
        $('#timer-dropdown').toggleClass('d-none');
    });
    
    // Close dropdown when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#workout-timer-icon').length) {
            $('#timer-dropdown').addClass('d-none');
        }
    });
    
    // Prevent dropdown from closing when clicking inside it
    $(document).on('click', '#timer-dropdown', function(e) {
        e.stopPropagation();
    });
});

// Show timer display
function showTimerDisplay() {
    const timerIcon = $('#workout-timer-icon');
    
    if (timerIcon.length) {
        // ✅ Just remove d-none class - no fadeIn needed
        timerIcon.removeClass('d-none');
        
        // Add active animation
        $('.timer-icon-clickable').addClass('active');
        
        console.log('Timer icon displayed');
    } else {
        console.error('Timer icon container not found');
    }
}
function showTimerStartAnimation() {
    console.log('🎬 Starting timer animation');
    
    const overlay = $('#timer-animation-overlay');
    
    // Force display and trigger reflow
    overlay.removeClass('d-none');
    overlay.css('display', 'flex');
    
    // Force a reflow to ensure the element is rendered
    overlay[0].offsetHeight;
    
    // Hide overlay after animation completes
    setTimeout(() => {
        overlay.addClass('d-none');
        overlay.css('display', 'none');
        console.log('🎬 Timer animation completed');
    }, 1500);
}
// Hide timer display
function hideTimerDisplay() {
    const timerIcon = $('#workout-timer-icon');
    
    timerIcon.addClass('d-none');
    $('.timer-icon-clickable')
        .removeClass('active')
        .removeClass('paused');
    $('#timer-dropdown').addClass('d-none');
    
    console.log('Timer icon hidden');
}

// Calculate calories burned for weights (4 METs)
function calculateWeightCalories() {
    if (!workoutTimer.totalSeconds || workoutTimer.totalSeconds === 0) return 0;
    
    const durationHours = workoutTimer.totalSeconds / 3600; // Convert seconds to hours
    const metValue = 4.0; // Weight training MET value
    const calories = metValue * userWeight * durationHours;
    
    console.log(`Weight training calories: ${calories.toFixed(1)} (${durationHours.toFixed(2)}h × 4 METs × ${userWeight}kg)`);
    return Math.max(0, calories);
}

// Get workout timer data for saving
function getWorkoutTimerData() {
    return {
        startTime: workoutTimer.startTime,
        endTime: workoutTimer.endTime || new Date(),
        totalSeconds: workoutTimer.totalSeconds || (workoutTimer.isActive && workoutTimer.startTime ? 
            Math.floor((new Date() - workoutTimer.startTime) / 1000) : 0),
        calories: calculateWeightCalories()
    };
}
function initializeTimer() {
    console.log('🔧 Initializing timer system...');
    
    // Try to restore timer state
    const restored = loadTimerState();
    
    if (restored) {
        console.log('🟢 Timer restored and active');
        handleServerReconnection(); // Ensure display is working
    } else {
        console.log('ℹ️ No active timer to restore');
    }
}

// Clean up on page unload
function cleanupTimer() {
    if (workoutTimer.isActive) {
        // Update last activity before leaving
        workoutTimer.lastActivity = new Date();
        saveTimerState();
        console.log('💾 Timer state saved before page unload');
    }
}
// Function to ensure timer persists after DOM changes
function ensureTimerPersistence() {
    if (typeof workoutTimer !== 'undefined' && workoutTimer.isActive) {
        // Check if timer display exists
        if (!document.getElementById('workout-timer-container')) {
            console.log('Timer active but display missing, recreating...');
            if (typeof showTimerDisplay === 'function') {
                showTimerDisplay();
            }
        }
        
        // Ensure interval is running
        if (!workoutTimer.intervalId && typeof updateTimerDisplay === 'function') {
            workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
            console.log('Timer interval restarted');
        }
    }
}

// Call this after any DOM manipulation that might affect the timer
function refreshTimerAfterDOMChange() {
    if (workoutTimer.isActive) {
        setTimeout(ensureTimerDisplay, 100);
    }
}
function handleServerReconnection() {
    // Check if we have an active timer but server session expired
    if (workoutTimer.isActive && workoutTimer.startTime) {
        console.log('🔄 Server session expired, but timer is still active');
        
        // Try to restore timer display if missing
        if (!document.getElementById('workout-timer-container')) {
            showTimerDisplay();
        }
        
        // Update the display immediately
        updateTimerDisplay();
        
        // Restart the interval if it stopped
        if (!workoutTimer.intervalId) {
            workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
            console.log('Timer interval restarted after server reconnection');
        }
        
        return true;
    }
    
    return false;
}
// Detect when server session is restored
function detectServerReconnection() {
    // This runs on any successful AJAX call after a timeout
    $(document).ajaxSuccess(function(event, xhr, settings) {
        // If we have an active timer, ensure it's still displayed
        if (workoutTimer.isActive) {
            handleServerReconnection();
        }
    });
}
document.addEventListener('DOMContentLoaded', function() {
    detectServerReconnection();
});
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
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":"&#39;",'/':'&#x2F;','`':'&#x60;','=':'&#x3D;'
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
    
    // ✅ Define today and isCurrentDay ONCE at the top
    const today = new Date().toISOString().split('T')[0];
    const isCurrentDay = currentDate === today;
    
    if (!collapseState.groups[currentDate]) collapseState.groups[currentDate] = {};
    if (!collapseState.exercises[currentDate]) collapseState.exercises[currentDate] = {};

    // Group exercises by muscle group
    const groups = {};
    exercises.forEach(exercise => {
        const group = exercise.muscle_group;
        if (!groups[group]) groups[group] = { exercises: [], totalSets: 0, totalVolume: 0 };

        const uniqueSets = Array.isArray(exercise.sets) ? [...exercise.sets] : [];
        const exerciseVolume = uniqueSets.reduce((sum, set) => {
            const reps = Number(set.reps) || 0;
            const weight = Number(set.weight) || 0;
            const volume = reps * weight;
            set.volume = volume;
            return sum + volume;
        }, 0);
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

        // ✅ FIXED: Group collapse initialization with today check
        // Ensure collapse state exists - default to collapsed (true)
        if (!collapseState.groups[currentDate][groupName]) {
            collapseState.groups[currentDate][groupName] = { collapsed: true };
        }

        // For non-current days, always force collapsed
        // For current day, keep whatever state is in localStorage
        if (!isCurrentDay) {
            collapseState.groups[currentDate][groupName].collapsed = true;
        }

        // Get the collapse state (will be from localStorage for current day)
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
            // ✅ FIXED: Exercise collapse initialization (no duplicate today/isCurrentDay)
            // Default to collapsed (true) for all exercises
            // For current day: use saved state (or default to true if first time)
            // For other days: always force collapsed (true)
            let exerciseCollapsed;
            if (isCurrentDay) {
                // Current day: use saved state, default to collapsed if not set
                exerciseCollapsed = collapseState.exercises[currentDate][exercise.id] !== undefined 
                    ? collapseState.exercises[currentDate][exercise.id] 
                    : true;
            } else {
                // Other days: always collapsed
                exerciseCollapsed = true;
            }
            
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

    // ✅ Group toggle handler
    $(".toggle-group").off("click").on("click", function() {
        const $group = $(this).closest(".workout-group");
        const groupName = $group.data("group");
        const groupItems = $group.find(".group-items");
        const isExpanded = groupItems.is(":visible");

        groupItems.toggle(!isExpanded);
        $(this).html(`<i class="fas fa-${isExpanded ? 'plus' : 'minus'}"></i>`);
        $(this).attr('title', isExpanded ? 'Expand' : 'Collapse');

        // Only save state for current day
        if (isCurrentDay) {
            collapseState.groups[currentDate][groupName].collapsed = isExpanded;
            saveCollapseState();
        }
    });

    // ✅ Exercise toggle handler
    $(".toggle-exercise").off("click").on("click", function() {
        const $exercise = $(this).closest(".exercise");
        const exerciseId = $exercise.data("exercise-id");
        const exerciseSets = $exercise.find(".exercise-sets");
        const isExpanded = exerciseSets.is(":visible");

        exerciseSets.toggle(!isExpanded);
        $(this).html(`<i class="fas fa-${isExpanded ? 'plus' : 'minus'}"></i>`);
        $(this).attr('title', isExpanded ? 'Expand' : 'Collapse');
        $exercise.find(".exercise-header").toggleClass("expanded", !isExpanded);

        // Only save state for current day
        if (isCurrentDay) {
            collapseState.exercises[currentDate][exerciseId] = isExpanded;
            saveCollapseState();
        }
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
// XP Display Functions
function showXPSummary(xpData, workoutData) {
    console.log('📊 Displaying XP summary:', xpData);
    
    const { gained, sources, levels_gained, level_before, level_after, current_xp, xp_to_next_level } = xpData;
        if (levels_gained > 0) {
        if (window.SoundManager) {
            window.SoundManager.playLevelup();
        }
    }
    
    // Create XP overlay
    const overlay = $(`
        <div class="xp-overlay" id="xp-summary-overlay">
            <div class="xp-card">
                <div class="xp-particles" id="xp-particles"></div>
                
                ${levels_gained > 0 ? `
                    <div class="level-up-banner">
                        🎉 Level Up! 🎉
                        <div style="font-size: 16px; margin-top: 5px;">
                            Level ${level_before} → ${level_after}
                        </div>
                    </div>
                    <div class="level-celebration">✨</div>
                ` : `
                    <h3 style="color: #6dc0d5; margin-bottom: 20px;">
                        <i class="fas fa-star"></i> Suoritus Valmis!
                    </h3>
                `}
                
                <div class="xp-gained-display">
                    +${gained} XP
                </div>
                
                <div class="xp-sources">
                    <h4 style="color: #fff; margin-bottom: 15px;">XP Jakauma</h4>
                    ${Object.entries(sources).map(([source, value]) => {
                        if (value <= 0) return '';
                        const labels = {
                            'cardio_duration': '🏃 Cardion Kesto',
                            'cardio_calories': '🔥 Cardion Kalorit',
                            'weights_volume': '💪 Treenin Volyymi',
                            'new_exercises': '🆕 Uudet Liikkeet',
                            'personal_bests': '🏆 Ennätykset'
                        };
                        return `
                            <div class="xp-source-item">
                                <span class="xp-source-label">${labels[source] || source}</span>
                                <span class="xp-source-value">+${value}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <div class="level-progress">
                    <div class="level-info">
                        <span>Level ${level_after}</span>
                        <span>${current_xp}/${xp_to_next_level} XP</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" id="xp-progress-bar" 
                             style="width: ${(current_xp / xp_to_next_level) * 100}%">
                        </div>
                    </div>
                </div>
                
                <button class="continue-btn" onclick="hideXPSummary()">
                    Jatka tilastoihin
                </button>
            </div>
        </div>
    `);
    
    $('body').append(overlay);
    
    // Show with animation
    setTimeout(() => {
        overlay.addClass('show');
        animateXPElements(levels_gained > 0);
    }, 100);
    
    // Store workout data for next step
    window.pendingWorkoutResults = workoutData;
}

function animateXPElements(isLevelUp) {
    // Animate progress bar
    setTimeout(() => {
        const progressBar = $('#xp-progress-bar');
        const currentWidth = progressBar.css('width');
        progressBar.css('width', '0%').animate({'width': currentWidth}, 1000);
    }, 800);
    
    // Create floating particles if level up
    if (isLevelUp) {
        createXPParticles();
        
        // CRITICAL: Remove level celebration star after animation
        setTimeout(() => {
            $('.level-celebration').remove();
        }, 3000); // 3s animation duration
    }
    
    // Animate XP sources with stagger
    $('.xp-source-item').each((index, element) => {
        setTimeout(() => {
            $(element).css({
                'opacity': '0',
                'transform': 'translateX(-20px)'
            }).animate({
                'opacity': '1'
            }, 300).css('transform', 'translateX(0)');
        }, index * 100);
    });
}

function createXPParticles() {
    const container = $('#xp-particles');
    const particleCount = 15;
    
    // Clear any existing particles first
    container.empty();
    
    for (let i = 0; i < particleCount; i++) {
        setTimeout(() => {
            const particle = $('<div class="xp-particle"></div>');
            particle.css({
                'left': Math.random() * 100 + '%',
                'animation-delay': Math.random() * 0.5 + 's'
            });
            container.append(particle);
            
            // CRITICAL: Remove particle after animation completes
            setTimeout(() => {
                particle.remove();
            }, 5500); // 5s animation + 500ms buffer
        }, i * 100);
    }
    
    // Optional: Clear entire container after all animations
    setTimeout(() => {
        container.empty();
    }, 6000);
}

function hideXPSummary() {
    const overlay = $('#xp-summary-overlay');
    overlay.removeClass('show');
    
    setTimeout(() => {
        overlay.remove();
        
        // Show achievements/results if available
        if (window.pendingWorkoutResults) {
            showWorkoutResults(
                window.pendingWorkoutResults.comparisonData,
                window.pendingWorkoutResults.achievements
            );
            delete window.pendingWorkoutResults;
        }
    }, 400);
}
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

// Format duration helper
function formatDuration(seconds) {
    if (!seconds) return '0m';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    let result = '';
    if (hours > 0) result += `${hours}h `;
    if (minutes > 0) result += `${minutes}m`;
    if (!hours && !minutes && secs > 0) result = `${secs}s`;
    
    return result.trim() || '0m';
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
    const newExercises = achievements.newExercises || 0;
    const volumeImprovements = achievements.volumeImprovements || 0;
    const setsImprovements = achievements.setsImprovements || 0;
    const meaningfulPRs = personalRecords.filter(pr => pr.previousBest && (pr.previousBest.weight > 0 || pr.previousBest.reps > 0));
    const prCount = meaningfulPRs.length;
    const improvementCount = improvements.length;
    
    // GET TIMER AND CARDIO DATA
    const timerData = getWorkoutTimerData();
    const weightDuration = timerData.totalSeconds || 0;
    const weightCalories = timerData.calories || 0;
    
    // Get cardio data from DOM
    let cardioDuration = 0;
    let cardioCalories = 0;
    $('.workout-group.cardio .exercise').each(function() {
        const durationText = $(this).find('.set-details').text();
        const caloriesText = $(this).find('.volume-display').text();
        
        // Extract duration in minutes
        const durationMatch = durationText.match(/(\d+)\s*min/);
        if (durationMatch) {
            cardioDuration += parseInt(durationMatch[1]) * 60; // Convert to seconds
        }
        
        // Extract calories
        const caloriesMatch = caloriesText.match(/(\d+)\s*cal/);
        if (caloriesMatch) {
            cardioCalories += parseInt(caloriesMatch[1]);
        }
    });
    
    const totalDuration = weightDuration + cardioDuration;
    const totalCalories = weightCalories + cardioCalories;
    
    // Dynamic PR messages based on count
    function getPRMessage(count) {
        if (count === 0) return '';
        
        const messages = {
            1: ['solid', 'notbad', 'takeit'],
            2: ['incredible', 'onfire', 'majestic'], 
            3: ['incredible', 'onfire', 'majestic'],
            4: ['incredible', 'onfire', 'majestic'],
            5: ['woah', 'holdup', 'winner', 'king']
        };
        
        let messageGroup;
        if (count === 1) messageGroup = messages[1];
        else if (count >= 2 && count <= 4) messageGroup = messages[2];
        else messageGroup = messages[5];
        
        const randomIndex = Math.floor(Math.random() * messageGroup.length);
        return t(messageGroup[randomIndex]);
    }
    
    // Dynamic improvement messages based on count
    function getImprovementMessage(count) {
        if (count === 0) return '';
        
        const messages = {
            1: ['keepup', 'pushing'],
            2: ['thereitis', 'resultspeak', 'motivated'],
            3: ['thereitis', 'resultspeak', 'motivated'],
            4: ['thereitis', 'resultspeak', 'motivated'],
            5: ['whatinthe']
        };
        
        let messageGroup;
        if (count === 1) messageGroup = messages[1];
        else if (count >= 2 && count <= 4) messageGroup = messages[2];
        else messageGroup = messages[5];
        
        const randomIndex = Math.floor(Math.random() * messageGroup.length);
        return t(messageGroup[randomIndex]);
    }

    let resultsHTML = `
        <div class="workout-results-modal style-glass" id="workout-results">
            <div class="results-header">
                <h2 class="results-title">${t('workoutComplete')}</h2>
                <div class="results-subtitle">${t('performanceAnalysis')}</div>
            </div>
            <div class="results-body">
    `;
    
    // Show new exercises toast instead of meaningless PRs
    if (newExercises > 0) {
        console.log("DEBUG Toast: Adding toast to HTML");
        resultsHTML += `
            <div class="new-exercises-toast">
                <div class="toast-icon">🔍</div>
                <div class="toast-text">${newExercises} ${t('newExercisesDetected')}</div>
                <div class="toast-subtext">${t('greatJobTryingNew')}</div>
            </div>`;
    }
    
    // Show PR celebrations only for meaningful PRs (not first-time 0kg comparisons)
    if (personalRecords.length > 0) {
        personalRecords.forEach(pr => {
            // Only show PRs where previousBest is meaningful (not 0)
            if (pr.previousBest.weight > 0 || pr.previousBest.reps > 0) {
                if (pr.type === 'bestSet') {
                    resultsHTML += `
                        <div class="pr-celebration">
                            <div class="pr-trophy"><img src="static/images/gold-medal.png"></div>
                            <div class="pr-text">${t('newBestSet')}</div>
                            <div class="pr-details">${pr.exercise}: ${pr.weight}kg x ${pr.reps} toistoa</div>
                            <div class="pr-details">${t('previousBest')}: ${pr.previousBest.weight}kg x ${pr.previousBest.reps} toistoa</div>
                        </div>`;
                } else if (pr.type === 'heaviestWeight') {
                    resultsHTML += `
                        <div class="pr-celebration">
                            <div class="pr-trophy"><img src="static/images/trophy1.png"></div>
                            <div class="pr-text">${t('heaviestWeight')}</div>
                            <div class="pr-details">${pr.exercise}: ${pr.weight}kg</div>
                            <div class="pr-details">${t('previousBest')}: ${pr.previousBest.weight}kg</div>
                        </div>`;
                }
            }
        });
    }
    
    // Achievement cards
    resultsHTML += `
    <div class="achievement-grid glass">
        <div class="achievement-card glass">
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
                <div class="achievement-note">${t('comparedSameFocusType')}</div>
            </div>
            
         <div class="achievement-card">
                <div class="achievement-icon">⚡</div>
                <div class="achievement-title">${t('personalRecords')}</div>
                <div class="achievement-value">${prCount}</div>
                <div class="achievement-change improvement">
                    <i class="fas fa-star"></i>
                    ${getPRMessage(prCount)}
                </div>
            </div>
            
            <div class="achievement-card">
                <div class="achievement-icon">📈</div>
                <div class="achievement-title">${t('improvements')}</div>
                <div class="achievement-value">${improvementCount}</div>
                <div class="achievement-change improvement">
                    <i class="fas fa-trending-up"></i>
                    <div class="improvement-details">
                        ${volumeImprovements > 0 ? `<div class="improvement-bullet">• ${t('volumeImproved')} (${volumeImprovements})</div>` : ''}
                        ${setsImprovements > 0 ? `<div class="improvement-bullet">• ${t('setsImproved')} (${setsImprovements})</div>` : ''}
                        ${newExercises > 0 ? `<div class="improvement-bullet">• ${t('newExercises')} (${newExercises})</div>` : ''}
                        <div class="improvement-header">${getImprovementMessage(improvementCount)}</div>
                    </div>
                </div>
            </div>
            
            <div class="achievement-card glass">
                <div class="achievement-icon"><img src="static/images/timer_icon.png" width=45></div>
                <div class="achievement-title">Treenin Aika</div>
                <div class="achievement-value">${formatDuration(totalDuration)}</div>
                <div class="achievement-change neutral">
                    <div class="time-breakdown">
                        ${weightDuration > 0 ? `<div class="time-item">💪 Puntti: ${formatDuration(weightDuration)}</div>` : ''}
                        ${cardioDuration > 0 ? `<div class="time-item">❤️ Cardio: ${formatDuration(cardioDuration)}</div>` : ''}
                    </div>
                </div>
            </div>
            
            <div class="achievement-card glass">
                <div class="achievement-icon">🔥</div>
                <div class="achievement-title">Kaloreita Poltettu</div>
                <div class="achievement-value">${Math.round(totalCalories)} cal</div>
                <div class="achievement-change neutral">
                    <div class="calories-breakdown">
                        ${weightCalories > 0 ? `<div class="calories-item">💪 Puntti: ${Math.round(weightCalories)} cal</div>` : ''}
                        ${cardioCalories > 0 ? `<div class="calories-item">❤️ Cardio: ${Math.round(cardioCalories)} cal</div>` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    
    // Close button
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
    
    // Auto-hide after 45 seconds if user doesn't interact
    setTimeout(() => {
        if ($('#workout-results').is(':visible')) {
            hideWorkoutResults();
        }
    }, 155000);
}

// Update set rows with progress indicators
function updateSetRowsWithProgress(comparisonData) {
    if (!comparisonData || !comparisonData.setComparisons) return;
    
    comparisonData.setComparisons.forEach(comparison => {
        const $setRow = $(`.set-row[data-set-id="${comparison.setId}"]`);
        if ($setRow.length === 0) return;
        
        // Handle first-time exercises differently
        if (comparison.noPrevious) {
            $setRow.find('.set-progress-indicator').remove();
            const indicator = $(`<div class="set-progress-indicator first-session">${t('firstSession')}</div>`);
            $setRow.find('.volume-display').css('position', 'relative').append(indicator);
            return;
        }
        
        // Add progress indicator for exercises with previous data
        const progressClass = comparison.volumeChange > 0 ? 'progress-up' : 
                             comparison.volumeChange < 0 ? 'progress-down' : 'progress-equal';
        const changeText = comparison.volumeChange > 0 ? `+${comparison.volumeChange.toFixed(1)}kg` :
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

// Hide workout results
function hideWorkoutResults() {
    $('#workout-results').fadeOut(300, function() {
        $(this).remove();
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

function displayCardioSessions(cardioSessions, containerOverride = null) {
    if (!cardioSessions || cardioSessions.length === 0) {
        return;
    }

    // Find the container - use override or default
    const container = containerOverride || document.getElementById('workout-session-container');
    if (!container) {
        console.error('Could not find workout session container');
        return;
    }

    // Remove existing cardio groups to prevent duplicates
    const existingCardioGroup = container.querySelector('.workout-group.cardio');
    if (existingCardioGroup) {
        existingCardioGroup.remove();
    }

    // Deduplicate sessions by ID
    const uniqueSessions = [];
    const seenIds = new Set();
    
    cardioSessions.forEach(session => {
        if (!seenIds.has(session.id)) {
            seenIds.add(session.id);
            uniqueSessions.push(session);
        }
    });

    if (uniqueSessions.length === 0) {
        console.warn('No unique cardio sessions to display');
        return;
    }

    console.log('Displaying', uniqueSessions.length, 'unique cardio sessions');

    // Create cardio group header
    const cardioGroupDiv = document.createElement('div');
    cardioGroupDiv.className = 'workout-group cardio';
    
    // Calculate total calories
    const totalCalories = uniqueSessions.reduce((sum, session) => sum + session.calories_burned, 0);
    
    cardioGroupDiv.innerHTML = `
        <div class="group-header">
            <div class="group-header-content">
                <div class="group-icon">
                    <i class="fas fa-heart"></i>
                </div>
                <div class="group-title">Cardio</div>
            </div>
            <div class="group-summary">
                <span class="summary-item">${uniqueSessions.length} Harjoitus${uniqueSessions.length !== 1 ? 'ta' : ''}</span>
                <span class="summary-item">${Math.round(totalCalories)} cal</span>
            </div>
        </div>
    `;

    const groupItemsDiv = document.createElement('div');
    groupItemsDiv.className = 'group-items';

    // Display each unique cardio session
    uniqueSessions.forEach(session => {
        const exerciseDiv = document.createElement('div');
        exerciseDiv.className = 'exercise';
        exerciseDiv.setAttribute('data-cardio-id', session.id);

        let sessionDetails = `${session.duration_minutes} min`;
        if (session.distance_km) sessionDetails += `, ${session.distance_km} km`;
        if (session.avg_pace_min_per_km) sessionDetails += `, ${session.avg_pace_min_per_km} min/km`;
        if (session.avg_heart_rate) sessionDetails += `, ${session.avg_heart_rate} bpm`;
        if (session.watts) sessionDetails += `, ${session.watts}W`;

        exerciseDiv.innerHTML = `
            <div class="exercise-header">
                <div class="exercise-header-content">
                    <div class="exercise-title">${session.exercise_name}</div>
                </div>
                <div class="exercise-info">
                    <div class="set-details">${sessionDetails}</div>
                    <div class="volume-display">${Math.round(session.calories_burned)} cal</div>
                    <div class="actions-cell">
                        <button class="delete-item cardio-delete-btn" data-session-id="${session.id}" title="Delete cardio session">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
            ${session.notes ? `<div class="exercise-notes" style="padding: 4px 8px; font-size: 11px; color: #aaa; font-style: italic;">${session.notes}</div>` : ''}
        `;

        groupItemsDiv.appendChild(exerciseDiv);
    });

    cardioGroupDiv.appendChild(groupItemsDiv);
    
    // ✅ ENSURE APPEND HAPPENS AFTER DOM IS READY
    container.appendChild(cardioGroupDiv);
    
    console.log('Successfully displayed cardio sessions with data attributes');
}

// ✅ UTILITY: Show toast messages
function showToast(message, type = 'info') {
    // Create toast if it doesn't exist
    let toast = document.getElementById('cardio-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'cardio-toast';
        toast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            padding: 12px 20px; border-radius: 6px; color: white;
            font-weight: bold; opacity: 0; transition: opacity 0.3s;
        `;
        document.body.appendChild(toast);
    }
    
    // Set color based on type
    const colors = {
        success: '#4CAF50',
        error: '#F44336', 
        warning: '#FF9800',
        info: '#2196F3'
    };
    
    toast.style.backgroundColor = colors[type] || colors.info;
    toast.textContent = message;
    toast.style.opacity = '1';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
    }, 3000);
}

function displayWorkoutData(workoutData) {
    const container = document.getElementById('workout-session-container');

    if (!workoutData.success || !workoutData.session) {
        container.innerHTML = "<p>Tälle päivälle ei löytynyt harjoitus dataa</p>";
        return;
    }

    const session = workoutData.session;
    const exercises = workoutData.exercises || [];

    const sessionTitle = document.createElement("h3");
    sessionTitle.textContent = session.name || "Workout Session";
    container.appendChild(sessionTitle);

    exercises.forEach(ex => {
        const exDiv = document.createElement("div");
        exDiv.classList.add("exercise");

        const exName = document.createElement("h4");
        exName.textContent = ex.name;
        exDiv.appendChild(exName);

        ex.sets.forEach(set => {
            const setDiv = document.createElement("div");
            setDiv.textContent = `Reps: ${set.reps}, Weight: ${set.weight || 0}kg`;
            exDiv.appendChild(setDiv);
        });

        container.appendChild(exDiv);
    });
}

function updateCardioGroupSummary(cardioGroup, remainingSessions) {
    const summaryItems = cardioGroup.querySelectorAll('.summary-item');
    const sessionCount = remainingSessions.length;
    
    // Calculate total calories from remaining sessions
    let totalCalories = 0;
    remainingSessions.forEach(session => {
        const volumeDisplay = session.querySelector('.volume-display');
        if (volumeDisplay) {
            const calories = parseInt(volumeDisplay.textContent.replace(' cal', '')) || 0;
            totalCalories += calories;
        }
    });
    
    // Update summary items
    if (summaryItems[0]) {
        summaryItems[0].textContent = `${sessionCount} session${sessionCount > 1 ? 's' : ''}`;
    }
    if (summaryItems[1]) {
        summaryItems[1].textContent = `${totalCalories} cal`;
    }
    
    console.log(`Updated cardio summary: ${sessionCount} sessions, ${totalCalories} calories`);
}

// Add function to delete cardio session
async function deleteCardioSession(sessionId) {
    if (!sessionId) {
        console.error('No session ID provided for deletion');
        return;
    }
    
    if (!confirm) {
        return;
    }
    
    console.log('Deleting cardio session:', sessionId);
    
    try {
        const response = await fetch(`/workout/cardio-sessions/${sessionId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Cardio session deleted successfully:', result);
            
            // ✅ INVALIDATE CACHE for current date
            if (typeof invalidateCache === 'function' && typeof CACHE_KEYS !== 'undefined') {
                const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                if (cachedSessions[currentSelectedDate]) {
                    delete cachedSessions[currentSelectedDate];
                    setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
                }
            }
            
            // ✅ Remove the specific session element from DOM
            const sessionElement = document.querySelector(`[data-cardio-id="${sessionId}"]`) || 
                                  document.querySelector(`button[onclick*="${sessionId}"]`)?.closest('.exercise');
            
            if (sessionElement) {
                sessionElement.style.transition = 'all 0.3s ease';
                sessionElement.style.transform = 'scale(0.95)';
                sessionElement.style.opacity = '0';
                
                setTimeout(() => {
                    sessionElement.remove();
                    
                    // Check if this was the last cardio session
                    const cardioGroup = document.querySelector('.workout-group.cardio');
                    if (cardioGroup) {
                        const remainingSessions = cardioGroup.querySelectorAll('[data-cardio-id]') || 
                                                cardioGroup.querySelectorAll('.exercise');
                        
                        if (remainingSessions.length === 0) {
                            // Remove the entire cardio group if no sessions left
                            cardioGroup.style.transition = 'all 0.3s ease';
                            cardioGroup.style.opacity = '0';
                            setTimeout(() => {
                                cardioGroup.remove();
                            }, 300);
                        } else {
                            // ✅ Update the summary with remaining count (using the fixed function)
                            updateCardioGroupSummary(cardioGroup, remainingSessions);
                        }
                    }
                }, 300);
                
            } else {
                console.warn('Could not find cardio session element in DOM, refreshing data');
                // Fallback: refresh the workout data
                await loadWorkoutData(currentSelectedDate);
            }
            
        } else {
            console.error('Failed to delete cardio session:', result);
            alert(result.error || 'Ongelma poistaa cardio harjoitus');
        }
    } catch (error) {
        console.error('Error deleting cardio session:', error);
        alert('Ongelma poistaa cardio harjoitus');
    }
}

// ✅ Helper function to update cardio group summary
function updateCardioSummary(cardioGroup, remainingSessions) {
    const summaryItems = cardioGroup.querySelectorAll('.summary-item');
    const sessionCount = remainingSessions.length;
    
    // Calculate total calories from remaining sessions
    let totalCalories = 0;
    remainingSessions.forEach(session => {
        const volumeDisplay = session.querySelector('.volume-display');
        if (volumeDisplay) {
            const calories = parseInt(volumeDisplay.textContent.replace(' cal', '')) || 0;
            totalCalories += calories;
        }
    });
    
    // Update summary items
    if (summaryItems[0]) {
        summaryItems[0].textContent = `${sessionCount} session${sessionCount > 1 ? 's' : ''}`;
    }
    if (summaryItems[1]) {
        summaryItems[1].textContent = `${totalCalories} cal`;
    }
    
    console.log(`Updated cardio summary: ${sessionCount} sessions, ${totalCalories} calories`);
}

// ✅ Fallback function to refresh only cardio data (not entire workout)
async function refreshCardioDataOnly(date) {
    try {
        // Load only cardio sessions
        const cardioResponse = await fetch(`/workout/cardio-sessions/${date}`);
        const cardioData = await cardioResponse.json();
        
        // Remove existing cardio group
        const existingCardioGroup = document.querySelector('.workout-group.cardio');
        if (existingCardioGroup) {
            existingCardioGroup.remove();
        }
        
        // Add updated cardio data if any exists
        if (cardioData.cardio_sessions && cardioData.cardio_sessions.length > 0) {
            const container = document.getElementById('workout-session-container');
            displayCardioSessions(cardioData.cardio_sessions, container);
        }
        
        console.log('Refreshed cardio data only');
    } catch (error) {
        console.error('Error refreshing cardio data:', error);
        // Last resort: full refresh
        await loadWorkoutData(date);
    }
}

async function loadWorkoutData(date, callback) {
    // VALIDATE DATE PARAMETER
    if (!date || date === 'undefined' || date === undefined) {
        console.error('loadWorkoutData called with invalid date:', date);
        
        // Try to use currentSelectedDate as fallback
        if (currentSelectedDate) {
            console.log('Using currentSelectedDate as fallback:', currentSelectedDate);
            date = currentSelectedDate;
        } else {
            console.error('No valid date available, cannot load workout data');
            const container = document.getElementById('workout-session-container');
            container.innerHTML = `<div class='alert alert-danger'>Error: Päivämäärää ei valittu</div>`;
            return;
        }
    }
    
    try {
        console.log('Loading workout data for date:', date);
        
        // ENSURE DATE IS IN CORRECT FORMAT (YYYY-MM-DD)
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        if (!dateRegex.test(date)) {
            throw new Error(`Invalid date format: ${date}. Expected YYYY-MM-DD format.`);
        }
        
        // Use the caching system for combined data
        getSessionWithCache(date, callback);
        
    } catch (error) {
        console.error('Error loading workout data:', error);
        const container = document.getElementById('workout-session-container');
        container.innerHTML = `<div class='alert alert-danger'>Error loading workout data: ${error.message}</div>`;
        if (callback) callback();
    }
}

// Make sure displayCardioSessions is available when needed
document.addEventListener('DOMContentLoaded', function() {
    // Initialize cache
    initCache();
    
    // Load cardio exercises data
    if (typeof loadCardioExercises === 'function') {
        loadCardioExercises();
    }
    
    // Setup event handlers
    if (typeof setupCardioEventListeners === 'function') {
        setupCardioEventListeners();
    }
    
    console.log('Cardio functionality initialized');
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
