console.log("initworkout.js started");
// File: init.js
// Initialize workout page
$(document).ready(function() {
    initializeTimer();
    
    // Initialize cache first
    initCache();
    
    loadCollapseState();
    loadCurrentWeek();
    // Use cached version of exercises loading
    getExercisesWithCache(function() {
        // Ensure exercises are loaded before rendering options
        console.log("Exercises loaded:", window.exercises.length);
        renderExerciseOptions();
        // Setup event listeners after exercises are loaded
        setupEventListeners();
    });
    initTooltips();
    // Use cached version of templates loading
    getTemplatesWithCache();
    setupMobileDateSelector();
    populateMobileDateSelector(new Date().toISOString().split('T')[0]);
    
    // Set initial date display
    const weekDates = getWeekDates(new Date());
    renderWeekDates(weekDates);
    getSessionWithCache(currentSelectedDate, function(data) {
        renderWorkoutSession(data.session, data.exercises);
    });
    // Setup RiR and comment functionality
    setupRirDropdowns();
    setupCommentTooltips();
    // Setup exercise completion functionality
    setupExerciseCompletion();
});
// Initialize calendar state
    window.calendarState = {
        currentMonth: new Date(Date.UTC(new Date().getFullYear(), new Date().getMonth(), 1)),
        selectedDate: null
    };
    
    // Set up calendar event handlers
    setupCalendarEvents();
    refreshTimerAfterDOMChange();
// ===== INITIALIZATION FUNCTIONS =====
function loadCollapseState() {
    const savedState = localStorage.getItem('workoutCollapseState');
    if (savedState) {
        collapseState = JSON.parse(savedState);
    }
    
    // Load completed exercises state
    const savedCompleted = localStorage.getItem('completedExercises');
    if (savedCompleted) {
        completedExercises = JSON.parse(savedCompleted);
    }
}

function saveCollapseState() {
    localStorage.setItem('workoutCollapseState', JSON.stringify(collapseState));
    localStorage.setItem('completedExercises', JSON.stringify(completedExercises));
}

function initTooltips() {
    // Initialize Bootstrap tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Mobile-specific tooltip tap handling
    $('body').on('touchstart', '.comment-icon', function(e) {
        e.stopPropagation();
        e.preventDefault();

        // Hide all others first
        $('.comment-icon').not(this).tooltip('hide');
        $(this).tooltip('show');

        // Auto-hide after 10s
        setTimeout(() => {
            $(this).tooltip('hide');
        }, 10000);
    });

    // Hide tooltips when clicking/tapping elsewhere
    $(document).on('touchstart click', function(e) {
        if (!$(e.target).hasClass('comment-icon') && 
            !$(e.target).closest('.tooltip').length) {
            $('.comment-icon').tooltip('hide');
        }
    });
}
function initCalendar() {
    // Set up calendar event handlers if not already set
    setupCalendarEvents();
    
    // FIXED: Always render with current state, ensure it shows dates initially
    if (window.calendarState.currentMonth) {
        window.renderCalendar(window.calendarState.currentMonth);
    } else {
        // If no state, initialize to current month
        const today = new Date();
        window.calendarState.currentMonth = new Date(Date.UTC(today.getFullYear(), today.getMonth(), 1));
        window.renderCalendar(window.calendarState.currentMonth);
    }
}
function setupMobileDateSelector() {
    // ✅ IMPROVED: Wait for currentSelectedDate to be set
    const initDate = currentSelectedDate || new Date().toISOString().split('T')[0];
    populateMobileDateSelector(initDate);
    
    $("#mobile-date-selector").change(function() {
        const selectedDate = $(this).val();
        selectDate(selectedDate);
        // Use cached version of session loading
        getSessionWithCache(selectedDate, function(data) {
            renderWorkoutSession(data.session, data.exercises);
        });
        
        // Regenerate options with new center
        populateMobileDateSelector(selectedDate);
    });
}
// ===============================
// Auto-move dropdowns to <body>
// ===============================
// ===============================
// Auto-move dropdowns to <body> with dynamic repositioning
// ===============================
    function positionDropdown($dropdown, $toggle) {
    const offset = $toggle.offset();

    $dropdown.css({
        position: 'absolute',
        top: offset.top + $toggle.outerHeight(),
        left: offset.left,
        zIndex: 2100,
        minWidth: $toggle.outerWidth()
    });
}

// Show event
$('.dropdown').on('show.bs.dropdown', function() {
    const $toggle = $(this).find('[data-bs-toggle="dropdown"]');
    const $dropdown = $(this).find('.dropdown-menu');

    // Save original styles
    $dropdown.data('original-style', $dropdown.attr('style') || '');

    // Append dropdown to body for mobile & desktop
    $dropdown.appendTo('body');

    // Position it
    positionDropdown($dropdown, $toggle);

    // Reposition on scroll/resize
    $(window).on('scroll.dropdown resize.dropdown', function() {
        if ($toggle.parent().hasClass('show')) positionDropdown($dropdown, $toggle);
    });
});

// Hide event
$('.dropdown').on('hide.bs.dropdown', function() {
    const $dropdown = $(this).find('.dropdown-menu');

    // Return to original parent
    $dropdown.appendTo($(this));

    // Reset inline styles
    $dropdown.attr('style', $dropdown.data('original-style'));

    // Remove scroll/resize handlers
    $(window).off('scroll.dropdown resize.dropdown');
});

// Close when clicking outside
$(document).on('click', function(e) {
    $('.dropdown.show').each(function() {
        const $dropdown = $(this).find('.dropdown-menu');
        if (!$(this).is($(e.target)) && !$.contains(this, e.target)) {
            $(this).removeClass('show');
            $dropdown.appendTo($(this));
            $dropdown.attr('style', $dropdown.data('original-style'));
            $(window).off('scroll.dropdown resize.dropdown');
        }
    });
});
function getWorkoutNameKey(date) {
    return "workoutName_" + date;
}

function checkAndApplyPulseAnimation(date) {
    const $display = $(".workout-name-display");
    const name = localStorage.getItem(getWorkoutNameKey(date)) || "Nimetön Treeni";
    
    // Keep pulsing as long as the name is the default
    if (name === "Nimetön Treeni") {
        $display.addClass("pulse-animation");
    } else {
        $display.removeClass("pulse-animation");
    }
}

function renderWorkoutName(date) {
    const name = localStorage.getItem(getWorkoutNameKey(date)) || "Nimetön Treeni";
    $(".workout-name-display").text(name).show();
    $(".workout-name-input").val(name).hide();
    checkAndApplyPulseAnimation(date);
}

$(document).on("click", ".workout-name-display", function() {
    $(this).removeClass("pulse-animation");
    $(this).hide();
    $(".workout-name-input").val($(this).text()).removeClass("d-none").show().focus().select();
});

$(document).on("blur", ".workout-name-input", saveEditWorkoutName);

$(document).on("keydown", ".workout-name-input", function(e){
    if(e.key === "Enter") $(this).blur();
});

function saveEditWorkoutName() {
    const $input = $(".workout-name-input");
    const date = $(".workout-date.active").data("date") || new Date().toISOString().split("T")[0];
    let val = $input.val().trim() || "Nimeä/Lataa Treeni";
    localStorage.setItem(getWorkoutNameKey(date), val);
    $(".workout-name-display").text(val).removeClass("pulse-animation").show();
    $input.hide();
}

$(document).on("workoutContentChanged", function() {
    const date = $(".workout-date.active").data("date") || new Date().toISOString().split("T")[0];
    renderWorkoutName(date);
});

$(document).on('click', '.workout-date', function() {
    const selectedDate = $(this).data('date');
    renderWorkoutName(selectedDate);
});

$(document).ready(function(){
    const date = $(".workout-date.active").data("date") || currentSelectedDate || new Date().toISOString().split("T")[0];
    renderWorkoutName(date);
});

$(window).on('beforeunload', function() {
    cleanupTimer();
});
