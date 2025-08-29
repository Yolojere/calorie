console.log("globalworkout.js loaded");
// File: globals.js
// Global variables
let activeCommentIcon = null;
let lastFocusedInputType = null; // 'reps' or 'weight'
let lastFocusedSetId = null;
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