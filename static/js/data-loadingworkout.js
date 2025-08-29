// File: data-loading.js
// ===== DATA LOADING FUNCTIONS =====
function loadCurrentWeek() {
    $.get("/workout/get_current_week", function(data) {
        currentSelectedDate = data.current_date;
        renderWeekDates(data.dates);
        // Use cached version of session loading
        getSessionWithCache(currentSelectedDate, function(data) {
            renderWorkoutSession(data.session, data.exercises);
        });
    });
}

function loadWorkoutSession(date) {
    saveScrollPosition(); // Save before loading new data
    
    $("#workout-session-container").html(
        '<div class="text-center py-4"><i class="fas fa-spinner fa-spin fa-2x"></i></div>'
    );
    
    // Use cached version of session loading
    getSessionWithCache(date, function(data) {
        renderWorkoutSession(data.session, data.exercises);
        initTooltips();
        
        // Restore scroll position after rendering
        setTimeout(restoreScrollPosition, 100);
        // Restore focus after rendering
        restoreFocus();
    });
}