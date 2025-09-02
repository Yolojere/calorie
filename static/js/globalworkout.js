console.log("globalworkout.js loaded");
// File: globals.js
// Global variables
let collapseGroups = false;
let activeCommentIcon = null;
let lastFocusedInputType = null; // 'reps' or 'weight'
let selectedFocusType = null;
let lastFocusedSetId = null;
let isCopiedWorkout = false;
let isCopyingWorkout = false;
let isApplyingTemplate = false;
let currentSelectedDate = new Date().toISOString().split('T')[0];
let currentDate = new Date();
let exercises = [];
let collapseState = {
    groups: {},
    exercises: {}
};
let savedScrollPosition = { desktop: 0, mobile: 0 };
let currentCommentSetId = null;
// Store completed exercises state
let completedExercises = {};
$(document).ready(function() {
    // Append comparison loading overlay once
    if (!$('#comparison-loading').length) {
    $('body').append(`
        <div id="comparison-loading" class="comparison-overlay" style="display:none;">
            <div class="comparison-spinner">
                <i class="fas fa-dumbbell fa-3x fa-spin"></i>
                <p>Comparing to previous lifts...</p>
            </div>
        </div>
    `);
}
});
