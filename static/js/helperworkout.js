console.log("helperworkout.js loaded");
// File: helpers.js
// ===== HELPER FUNCTIONS ===== //

function generateDateOptionsForTemplate() {
    const dates = [];
    const today = new Date();
    
    // Generate options for next 7 days
    for (let i = 1; i <= 7; i++) {
        const date = new Date();
        date.setDate(today.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        dates.push({
            date: dateStr,
            formatted: formatDateForDisplay(dateStr)
        });
    }
    return dates;
}

// format date for display
function formatDateForDisplay(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fi-FI', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
    });
}

function resetSetForm(isMobile = false) {
    if (isMobile) {
        $("#sets-input-mobile").val("1");
        $("#reps-input-mobile").val("");
        $("#weight-input-mobile").val("");
        $("#rir-input-mobile").val("");
        $("#comments-input-mobile").val("");
    } else {
        $("#sets-input").val("1");
        $("#reps-input").val("");
        $("#weight-input").val("");
        $("#rir-input").val("");
        $("#comments-input").val("");
    }
}

function restoreFocus() {
    if (lastFocusedSetId && lastFocusedInputType) {
        setTimeout(function() {
            const selector = `.set-row[data-set-id="${lastFocusedSetId}"] .set-${lastFocusedInputType}`;
            const $input = $(selector);
            if ($input.length) {
                $input.focus();
                // Also select the text for easy editing
                $input.select();
            }
            // Reset the focus tracking
            lastFocusedSetId = null;
            lastFocusedInputType = null;
        }, 100);
    }
}
        
function resetExerciseForm() {
    $("#new-exercise-name").val("");
    $("#new-exercise-desc").val("");
}
function getCardioSessionsFromUI() {
    const cardioSessions = [];
    
    // Find all cardio sessions in the current workout
    $('.workout-group.cardio .exercise').each(function() {
        const $cardioExercise = $(this);
        const sessionId = $cardioExercise.data('cardio-id');
        
        if (sessionId) {
            // Extract session data from DOM
            const exerciseName = $cardioExercise.find('.exercise-title').text().trim();
            const caloriesText = $cardioExercise.find('.volume-display').text();
            const calories = parseInt(caloriesText.replace(' cal', '')) || 0;
            
            cardioSessions.push({
                id: sessionId,
                exercise_name: exerciseName,
                calories: calories
            });
        }
    });
    
    return cardioSessions;
}
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

function getWeekDates(date) {
    const dates = [];
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // adjust when Sunday
    const monday = new Date(d.setDate(diff));
    
    for (let i = 0; i < 7; i++) {
        const newDate = new Date(monday);
        newDate.setDate(monday.getDate() + i);
        dates.push(newDate.toISOString().split('T')[0]);
    }
    return dates;
}

function formatDate(date) {
    return date.toLocaleDateString(currentLang === "fi" ? "fi-FI" : "en-US", { 
        month: 'short', 
        day: 'numeric' 
    });
}

function getWeekNumber(date) {
    const tempDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = tempDate.getUTCDay() || 7; // Sunday -> 7
    tempDate.setUTCDate(tempDate.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tempDate.getUTCFullYear(), 0, 1));
    return Math.ceil((((tempDate - yearStart) / 86400000) + 1) / 7);
}

function saveScrollPosition() {
    savedScrollPosition = {
        desktop: $('#workout-session-container').scrollTop()
    };
}

function restoreScrollPosition() {
    // Desktop restoration
    if ($('#workout-session-container').is(':visible')) {
        $('#workout-session-container').scrollTop(savedScrollPosition.desktop);
    }
}

function generateDateOptions(centerDate) {
    const dates = [];
    const center = new Date(centerDate);
    
    // Generate -3 to +3 days from center date
    for (let i = -3; i <= 3; i++) {
        const date = new Date(center);
        date.setDate(center.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        dates.push({
            date: dateStr,
            formatted: formatDateForSelector(date)
        });
    }
    return dates;
}
function ymd(y,m,d){ 
    // Ensure proper UTC date handling
    const date = new Date(Date.UTC(y, m-1, d));
    return date.toISOString().split('T')[0];
}
function formatDateForSelector(date) {
    const today = new Date();
    today.setHours(0,0,0,0);

    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);

    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    // Locale for numeric date
    const locale = currentLang === "fi" ? "fi-FI" : "en-GB";

    // Get numeric date string (day.month)
    const numericDate = date.toLocaleDateString(locale, { 
        day: 'numeric', 
        month: 'numeric' 
    });

    if (date.toDateString() === today.toDateString()) {
        return `${t('today')} ${numericDate}`;
    } else if (date.toDateString() === yesterday.toDateString()) {
        return `${t('yesterday')} ${numericDate}`;
    } else if (date.toDateString() === tomorrow.toDateString()) {
        return `${t('tomorrow')} ${numericDate}`;
    } else {
        // Map JS weekday index to translation keys
        const weekdays = [
            t('sunday'),
            t('monday'),
            t('tuesday'),
            t('wednesday'),
            t('thursday'),
            t('friday'),
            t('saturday')
        ];
        const weekday = weekdays[date.getDay()];
        return `${weekday} ${numericDate}`;
    }
}

function collectWorkoutData() {
  let data = {
    date: currentSelectedDate,
    name: $("#workout-name").val() || "Nimetön Treeni",
    exercises: []
  };

  $("#workout-session-container .exercise-item").each(function() {
    let exerciseId = $(this).data("id");
    let exerciseName = $(this).find(".exercise-name").text();
    let sets = [];

    $(this).find(".set-row").each(function() {
      sets.push({
        setNumber: $(this).data("set"),
        reps: parseInt($(this).find(".reps-input").val()) || 0,
        weight: parseFloat($(this).find(".weight-input").val()) || 0
      });
    });

    data.exercises.push({
      id: exerciseId,
      name: exerciseName,
      sets: sets
    });
  });

  return data;
}

// COMPARSION LAYOUT LOADING
function showComparisonLoading(duration = 3500, callback) {
    // Add backdrop overlay
    if ($("#comparison-backdrop").length === 0) {
        $("body").append('<div id="comparison-backdrop" class="comparison-backdrop"></div>');
    }
    $("#comparison-backdrop").addClass("show");

    $("#comparison-loading").fadeIn(200);
    setTimeout(() => {
        $("#comparison-loading").fadeOut(200, () => {
            if (callback) callback();
        });
    }, duration);
}
document.addEventListener('DOMContentLoaded', function() {
    // Function to ensure calendar stays above everything
    function ensureCalendarAboveAll() {
        const calendarModal = document.getElementById('copyWorkoutModal');
        const calendarBackdrop = document.querySelector('.modal-backdrop');
        
        if (calendarModal) {
            // Set higher z-index than comparison overlay (9999)
            calendarModal.style.zIndex = '10000';
        }
        
        if (calendarBackdrop) {
            // Set backdrop above comparison overlay too
            calendarBackdrop.style.zIndex = '9998';
        }
    }
    
    // Run when calendar modal is shown
    $('#copyWorkoutModal').on('shown.bs.modal', function() {
        ensureCalendarAboveAll();
    });
    
    // Also run on initial load in case modal is already open
    ensureCalendarAboveAll();
});
$('#saveWorkoutModal').on('show.bs.modal', function(){
    const date = $(".workout-date.active").data("date") || new Date().toISOString().split("T");
    const key = getWorkoutNameKey(date);
    const autosuggest = localStorage.getItem(key) || "Nimetön Treeni";
    $("#workout-name-input").val(autosuggest);
});
function selectDate(dateString) {
    // Check if timer is active
    const currentTimerDate = localStorage.getItem(TIMER_DATE_KEY);
    
    if (currentTimerDate && currentTimerDate !== dateString && workoutTimer.isActive) {
        if (confirm("Ajastin on päällä nykyisessä treenissä, keskeytetäänkö ajastin?")) {
            // ✅ PROPERLY STOP AND CLEAR TIMER
            stopWorkoutTimer();
            clearTimerState(); // This was missing!
            
            console.log('🔴 Timer stopped and cleared when switching dates');
        } else {
            // User cancelled, don't switch dates
            return;
        }
    }
    
    // Update global state
    currentSelectedDate = dateString;
    
    // Update visual indicators
    $('.workout-date').removeClass('active');
    $(`.workout-date[data-date="${dateString}"]`).addClass('active');
    
    // Load session for the selected date
    getSessionWithCache(dateString, function(data) {
        renderWorkoutSession(data.session, data.exercises);
    });
}
// Format time helper (if not already exists)
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// Update restoration to use new UI
function restoreTimerDisplay() {
    if (workoutTimer.isActive) {
        showTimerDisplay();
        updateTimerDisplay();
    }
}
console.log("helperworkout.js loaded");
// File: helpers.js
// ===== HELPER FUNCTIONS ===== //

function generateDateOptionsForTemplate() {
    const dates = [];
    const today = new Date();
    
    // Generate options for next 7 days
    for (let i = 1; i <= 7; i++) {
        const date = new Date();
        date.setDate(today.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        dates.push({
            date: dateStr,
            formatted: formatDateForDisplay(dateStr)
        });
    }
    return dates;
}

// format date for display
function formatDateForDisplay(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fi-FI', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
    });
}

function resetSetForm(isMobile = false) {
    if (isMobile) {
        $("#sets-input-mobile").val("1");
        $("#reps-input-mobile").val("");
        $("#weight-input-mobile").val("");
        $("#rir-input-mobile").val("");
        $("#comments-input-mobile").val("");
    } else {
        $("#sets-input").val("1");
        $("#reps-input").val("");
        $("#weight-input").val("");
        $("#rir-input").val("");
        $("#comments-input").val("");
    }
}

function restoreFocus() {
    if (lastFocusedSetId && lastFocusedInputType) {
        setTimeout(function() {
            const selector = `.set-row[data-set-id="${lastFocusedSetId}"] .set-${lastFocusedInputType}`;
            const $input = $(selector);
            if ($input.length) {
                $input.focus();
                // Also select the text for easy editing
                $input.select();
            }
            // Reset the focus tracking
            lastFocusedSetId = null;
            lastFocusedInputType = null;
        }, 100);
    }
}
        
function resetExerciseForm() {
    $("#new-exercise-name").val("");
    $("#new-exercise-desc").val("");
}
function getCardioSessionsFromUI() {
    const cardioSessions = [];
    
    // Find all cardio sessions in the current workout
    $('.workout-group.cardio .exercise').each(function() {
        const $cardioExercise = $(this);
        const sessionId = $cardioExercise.data('cardio-id');
        
        if (sessionId) {
            // Extract session data from DOM
            const exerciseName = $cardioExercise.find('.exercise-title').text().trim();
            const caloriesText = $cardioExercise.find('.volume-display').text();
            const calories = parseInt(caloriesText.replace(' cal', '')) || 0;
            
            cardioSessions.push({
                id: sessionId,
                exercise_name: exerciseName,
                calories: calories
            });
        }
    });
    
    return cardioSessions;
}
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

function getWeekDates(date) {
    const dates = [];
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // adjust when Sunday
    const monday = new Date(d.setDate(diff));
    
    for (let i = 0; i < 7; i++) {
        const newDate = new Date(monday);
        newDate.setDate(monday.getDate() + i);
        dates.push(newDate.toISOString().split('T')[0]);
    }
    return dates;
}

function formatDate(date) {
    return date.toLocaleDateString(currentLang === "fi" ? "fi-FI" : "en-US", { 
        month: 'short', 
        day: 'numeric' 
    });
}

function getWeekNumber(date) {
    const tempDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = tempDate.getUTCDay() || 7; // Sunday -> 7
    tempDate.setUTCDate(tempDate.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tempDate.getUTCFullYear(), 0, 1));
    return Math.ceil((((tempDate - yearStart) / 86400000) + 1) / 7);
}

function saveScrollPosition() {
    savedScrollPosition = {
        desktop: $('#workout-session-container').scrollTop()
    };
}

function restoreScrollPosition() {
    // Desktop restoration
    if ($('#workout-session-container').is(':visible')) {
        $('#workout-session-container').scrollTop(savedScrollPosition.desktop);
    }
}

function generateDateOptions(centerDate) {
    const dates = [];
    const center = new Date(centerDate);
    
    // Generate -3 to +3 days from center date
    for (let i = -3; i <= 3; i++) {
        const date = new Date(center);
        date.setDate(center.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        dates.push({
            date: dateStr,
            formatted: formatDateForSelector(date)
        });
    }
    return dates;
}
function ymd(y,m,d){ 
    // Ensure proper UTC date handling
    const date = new Date(Date.UTC(y, m-1, d));
    return date.toISOString().split('T')[0];
}
function formatDateForSelector(date) {
    const today = new Date();
    today.setHours(0,0,0,0);

    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);

    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    // Locale for numeric date
    const locale = currentLang === "fi" ? "fi-FI" : "en-GB";

    // Get numeric date string (day.month)
    const numericDate = date.toLocaleDateString(locale, { 
        day: 'numeric', 
        month: 'numeric' 
    });

    if (date.toDateString() === today.toDateString()) {
        return `${t('today')} ${numericDate}`;
    } else if (date.toDateString() === yesterday.toDateString()) {
        return `${t('yesterday')} ${numericDate}`;
    } else if (date.toDateString() === tomorrow.toDateString()) {
        return `${t('tomorrow')} ${numericDate}`;
    } else {
        // Map JS weekday index to translation keys
        const weekdays = [
            t('sunday'),
            t('monday'),
            t('tuesday'),
            t('wednesday'),
            t('thursday'),
            t('friday'),
            t('saturday')
        ];
        const weekday = weekdays[date.getDay()];
        return `${weekday} ${numericDate}`;
    }
}

function collectWorkoutData() {
  let data = {
    date: currentSelectedDate,
    name: $("#workout-name").val() || "Nimetön Treeni",
    exercises: []
  };

  $("#workout-session-container .exercise-item").each(function() {
    let exerciseId = $(this).data("id");
    let exerciseName = $(this).find(".exercise-name").text();
    let sets = [];

    $(this).find(".set-row").each(function() {
      sets.push({
        setNumber: $(this).data("set"),
        reps: parseInt($(this).find(".reps-input").val()) || 0,
        weight: parseFloat($(this).find(".weight-input").val()) || 0
      });
    });

    data.exercises.push({
      id: exerciseId,
      name: exerciseName,
      sets: sets
    });
  });

  return data;
}

// COMPARSION LAYOUT LOADING
function showComparisonLoading(duration = 3500, callback) {
    // Add backdrop overlay
    if ($("#comparison-backdrop").length === 0) {
        $("body").append('<div id="comparison-backdrop" class="comparison-backdrop"></div>');
    }
    $("#comparison-backdrop").addClass("show");

    $("#comparison-loading").fadeIn(200);
    setTimeout(() => {
        $("#comparison-loading").fadeOut(200, () => {
            if (callback) callback();
        });
    }, duration);
}
document.addEventListener('DOMContentLoaded', function() {
    // Function to ensure calendar stays above everything
    function ensureCalendarAboveAll() {
        const calendarModal = document.getElementById('copyWorkoutModal');
        const calendarBackdrop = document.querySelector('.modal-backdrop');
        
        if (calendarModal) {
            // Set higher z-index than comparison overlay (9999)
            calendarModal.style.zIndex = '10000';
        }
        
        if (calendarBackdrop) {
            // Set backdrop above comparison overlay too
            calendarBackdrop.style.zIndex = '9998';
        }
    }
    
    // Run when calendar modal is shown
    $('#copyWorkoutModal').on('shown.bs.modal', function() {
        ensureCalendarAboveAll();
    });
    
    // Also run on initial load in case modal is already open
    ensureCalendarAboveAll();
});
$('#saveWorkoutModal').on('show.bs.modal', function(){
    const date = $(".workout-date.active").data("date") || new Date().toISOString().split("T");
    const key = getWorkoutNameKey(date);
    const autosuggest = localStorage.getItem(key) || "Nimetön Treeni";
    $("#workout-name-input").val(autosuggest);
});
function selectDate(dateString) {
    // Check if timer is active
    const currentTimerDate = localStorage.getItem(TIMER_DATE_KEY);
    
    if (currentTimerDate && currentTimerDate !== dateString && workoutTimer.isActive) {
        if (confirm("Ajastin on päällä nykyisessä treenissä, keskeytetäänkö ajastin?")) {
            // ✅ PROPERLY STOP AND CLEAR TIMER
            stopWorkoutTimer();
            clearTimerState(); // This was missing!
            
            console.log('🔴 Timer stopped and cleared when switching dates');
        } else {
            // User cancelled, don't switch dates
            return;
        }
    }
    
    // Update global state
    currentSelectedDate = dateString;
    
    // Update visual indicators
    $('.workout-date').removeClass('active');
    $(`.workout-date[data-date="${dateString}"]`).addClass('active');
    
    // Load session for the selected date
    getSessionWithCache(dateString, function(data) {
        renderWorkoutSession(data.session, data.exercises);
    });
}
// Format time helper (if not already exists)
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// Update restoration to use new UI
function restoreTimerDisplay() {
    if (workoutTimer.isActive) {
        showTimerDisplay();
        updateTimerDisplay();
    }
}
function formatFinnishDate(isoDate) {
    const [year, month, day] = isoDate.split('-');
    return `${day}.${month}.${year}`;
}
