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
    return date.toLocaleDateString('en-GB', { 
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
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getWeekNumber(date) {
    const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
    const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
    return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
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

function formatDateForSelector(date) {
    const today = new Date();
    today.setHours(0,0,0,0);
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    let dateString = date.toLocaleDateString('en-GB', { 
        weekday: 'short', 
        month: 'numeric', 
        day: 'numeric' 
    });

    if (date.toDateString() === today.toDateString()) {
        return "Today - " + dateString;
    } else if (date.toDateString() === yesterday.toDateString()) {
        return "Yesterday - " + dateString;
    } else if (date.toDateString() === tomorrow.toDateString()) {
        return "Tomorrow - " + dateString;
    } else {
        return dateString;
    }
}
