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
    function positionDropdown($dropdown, $toggle) {
    const offset = $toggle.offset();
    const scrollTop = $(window).scrollTop();
    const scrollLeft = $(window).scrollLeft();

    if ($(window).width() >= 992) { // desktop
        // dropdown under the button
        $dropdown.css({
            position: 'absolute',
            top: offset.top + $toggle.outerHeight(),
            left: offset.left,
            zIndex: 2100,
            minWidth: $toggle.outerWidth() // match button width if you want
        });
    } else {
        // mobile: keep relative inside parent
        $dropdown.css({
            position: '',
            top: '',
            left: '',
            zIndex: ''
        });
    }
}

$('.dropdown').on('show.bs.dropdown', function() {
    const $toggle = $(this).find('[data-bs-toggle="dropdown"]');
    const $dropdown = $(this).find('.dropdown-menu');

    // save original CSS
    $dropdown.data('original-style', $dropdown.attr('style') || '');

    if ($(window).width() >= 992) {
        // append to body for desktop
        $dropdown.appendTo('body');
        positionDropdown($dropdown, $toggle);

        // reposition on scroll/resize
        $(window).on('scroll.dropdown resize.dropdown', function() {
            if ($toggle.parent().hasClass('show')) positionDropdown($dropdown, $toggle);
        });
    }
});

$('.dropdown').on('hide.bs.dropdown', function() {
    const $dropdown = $(this).find('.dropdown-menu');

    // return to original parent
    $dropdown.appendTo($(this));

    // reset inline styles
    $dropdown.attr('style', $dropdown.data('original-style'));

    // remove scroll/resize handler
    $(window).off('scroll.dropdown resize.dropdown');
});

// click outside to close
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
