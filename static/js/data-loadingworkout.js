console.log("data-loadingworkout.js started");
// File: data-loading.js
// ===== DATA LOADING FUNCTIONS =====
function loadCurrentWeek() {
    $.get("/workout/get_current_week", function(data) {
        currentSelectedDate = data.current_date;

        // Only call renderWeekDates if the function exists
        if (typeof renderWeekDates === "function") {
            renderWeekDates(data.dates);  // Array from server
        } else {
            console.warn("renderWeekDates function not loaded yet.");
        }

        // ✅ FIXED: Only call getSessionWithCache - it now handles both strength + cardio
        getSessionWithCache(currentSelectedDate, function(sessionData) {
            console.log('✅ Initial workout data loaded for', currentSelectedDate);
        });
    });
}

function loadWorkoutSession(date) {
    saveScrollPosition(); // Save before loading new data
    
    $("#workout-session-container").html(
        '<div class="text-center py-4"><i class="fas fa-spinner fa-spin fa-2x"></i></div>'
    );
    
    // ✅ FIXED: Use getSessionWithCache which 
    // now loads both strength + cardio
    getSessionWithCache(date, function(data) {
        console.log('✅ Complete workout session (strength + cardio) loaded for', date);
        initTooltips();
        
        // Restore scroll position after rendering
        setTimeout(restoreScrollPosition, 100);
        // Restore focus after rendering
        restoreFocus();
    });
}
