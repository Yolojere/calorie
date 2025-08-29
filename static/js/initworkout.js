console.log("initworkout.js started");
// File: init.js
// Initialize workout page
$(document).ready(function() {
    // Initialize cache first
    initCache();
    
    loadCollapseState();
    loadCurrentWeek();
    // Use cached version of exercises loading
    getExercisesWithCache(function() {
        renderExerciseOptions();
    });
    setupEventListeners();
    initTooltips();
    // Use cached version of templates loading
    getTemplatesWithCache();
    setupMobileDateSelector();
    populateMobileDateSelector(new Date().toISOString().split('T')[0]);
    
    // Set initial date display
    const weekDates = getWeekDates(new Date());
    renderWeekDates(weekDates);
    // Use cached version of session loading
    getSessionWithCache(currentSelectedDate, function(data) {
        renderWorkoutSession(data.session, data.exercises);
    });
    
    // Setup RiR and comment functionality
    setupRirDropdowns();
    setupCommentTooltips();
    // Setup exercise completion functionality
    setupExerciseCompletion();
    attachTemplateEventHandlers();
});

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

function setupMobileDateSelector() {
    // Initialize with today
    populateMobileDateSelector(currentSelectedDate);
    
    $("#mobile-date-selector").change(function() {
        const selectedDate = $(this).val();
        currentSelectedDate = selectedDate;
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
    function isDesktop() {
        return $(window).width() >= 992; // Bootstrap lg breakpoint
    }

    function positionSettingsDropdown($dropdown, $button) {
        const offset = $button.offset();
        const buttonWidth = $button.outerWidth();
        const dropdownWidth = $dropdown.outerWidth();

        $dropdown.css({
            position: 'absolute',
            top: offset.top + $button.outerHeight(),
            left: offset.left + buttonWidth - dropdownWidth,
            zIndex: 2100
        });
    }

    $('.mobile-settings-btn').on('click', function(e) {
        const $button = $(this);
        const $dropdown = $button.next('.dropdown-menu');

        if (isDesktop()) {
            e.preventDefault(); // prevent default Bootstrap mobile behavior
            if (!$dropdown.hasClass('show')) {
                $dropdown.appendTo('body'); // float on desktop
                positionSettingsDropdown($dropdown, $button);
                $dropdown.addClass('show');
            } else {
                $dropdown.removeClass('show').appendTo($button.parent());
                $dropdown.css({ top: '', left: '', position: '' });
            }
        }
        // else: mobile uses default dropdown (Bootstrap handles it)
    });

    // Hide dropdown when clicking outside
    $(document).on('click', function(e) {
        if (!isDesktop()) return; // skip on mobile
        $('.mobile-settings-btn').each(function() {
            const $button = $(this);
            const $dropdown = $button.next('.dropdown-menu');
            if ($dropdown.hasClass('show') && !$.contains($button[0], e.target) && e.target !== $button[0]) {
                $dropdown.removeClass('show').appendTo($button.parent());
                $dropdown.css({ top: '', left: '', position: '' });
            }
        });
    });

    // Reposition on window resize
    $(window).on('resize', function() {
        if (!isDesktop()) return;
        $('.mobile-settings-btn').each(function() {
            const $button = $(this);
            const $dropdown = $button.next('.dropdown-menu');
            if ($dropdown.hasClass('show')) {
                positionSettingsDropdown($dropdown, $button);
            }
        });
    });