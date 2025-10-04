console.log("cacheworkout.js loaded");

// ===== CACHING IMPLEMENTATION =====
const CACHE_KEYS = {
    EXERCISES: 'cached_exercises',
    SESSIONS: 'cached_sessions',
    TEMPLATES: 'cached_templates',
    TIMESTAMPS: 'cache_timestamps'
};

// Cache expiration times (in milliseconds)
const CACHE_EXPIRATION = {
    EXERCISES: 24 * 60 * 60 * 1000, // 24 hours
    SESSIONS: 60 * 60 * 1000,       // 1 hour
    TEMPLATES: 24 * 60 * 60 * 1000  // 24 hours
};

// Initialize cache
function initCache() {
    if (!localStorage.getItem(CACHE_KEYS.TIMESTAMPS)) {
        localStorage.setItem(CACHE_KEYS.TIMESTAMPS, JSON.stringify({}));
    }
    if (!localStorage.getItem(CACHE_KEYS.SESSIONS)) {
        localStorage.setItem(CACHE_KEYS.SESSIONS, JSON.stringify({}));
    }
    if (!localStorage.getItem(CACHE_KEYS.EXERCISES)) {
        localStorage.setItem(CACHE_KEYS.EXERCISES, JSON.stringify([]));
    }
    if (!localStorage.getItem(CACHE_KEYS.TEMPLATES)) {
        localStorage.setItem(CACHE_KEYS.TEMPLATES, JSON.stringify([]));
    }
}

// Get cached data with expiration check
function getCachedData(key, expirationTime) {
    try {
        const timestamps = JSON.parse(localStorage.getItem(CACHE_KEYS.TIMESTAMPS) || '{}');
        const cachedData = localStorage.getItem(key);

        if (!cachedData) return null;

        // Check if cache has expired
        if (timestamps[key] && (Date.now() - timestamps[key] > expirationTime)) {
            return null; // Cache expired
        }

        return JSON.parse(cachedData);
    } catch (e) {
        console.error('Error reading cache:', e);
        return null;
    }
}

// Set data in cache with timestamp
function setCachedData(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));

        // Update timestamp
        const timestamps = JSON.parse(localStorage.getItem(CACHE_KEYS.TIMESTAMPS) || '{}');
        timestamps[key] = Date.now();
        localStorage.setItem(CACHE_KEYS.TIMESTAMPS, JSON.stringify(timestamps));
    } catch (e) {
        console.error('Error writing to cache:', e);
    }
}

// Invalidate specific cache
function invalidateCache(key) {
    try {
        const timestamps = JSON.parse(localStorage.getItem(CACHE_KEYS.TIMESTAMPS) || '{}');
        delete timestamps[key];
        localStorage.setItem(CACHE_KEYS.TIMESTAMPS, JSON.stringify(timestamps));
        localStorage.removeItem(key);
    } catch (e) {
        console.error('Error invalidating cache:', e);
    }
}

// Invalidate session cache for a specific date
function invalidateDateCache(date) {
    try {
        const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
        if (cachedSessions[date]) {
            delete cachedSessions[date];
            setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
        }
        console.log('Cache invalidated for date:', date);
    } catch (e) {
        console.error('Error invalidating date cache:', e);
    }
}

// Invalidate all cache
function invalidateAllCache() {
    try {
        localStorage.setItem(CACHE_KEYS.TIMESTAMPS, JSON.stringify({}));
        Object.values(CACHE_KEYS).forEach(key => {
            if (key !== CACHE_KEYS.TIMESTAMPS) {
                localStorage.removeItem(key);
            }
        });
    } catch (e) {
        console.error('Error invalidating cache:', e);
    }
}

// Get session from cache or server WITH CARDIO DATA (using single backend call)
function getSessionWithCache(date, callback) {
    console.log('🔄 Loading workout data for date:', date);
    
    const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
    const hasSessionCache = cachedSessions[date] && cachedSessions[date].timestamp;
    
    // Check if session cache is fresh
    const isSessionCacheFresh = hasSessionCache && 
        (Date.now() - cachedSessions[date].timestamp) < CACHE_EXPIRATION.SESSIONS;

    // If cache is fresh, use cached data
    if (isSessionCacheFresh) {
        console.log('✅ Using cached session + cardio data for', date);
        
        const sessionData = cachedSessions[date];
        
        // Render combined data (session + cardio)
        renderCombinedWorkoutData(sessionData);
        
        if (callback) callback(sessionData);
        
        // Still fetch from server in background for freshness
        fetchAndUpdateBackground(date);
        return;
    }

    // If no fresh cache available, fetch from server
    console.log('⚡ No fresh cache, fetching session + cardio from server for', date);
    
    fetchCombinedSessionData(date).then(sessionData => {
        // Update cache with combined data
        const updatedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
        updatedSessions[date] = { ...sessionData, timestamp: Date.now() };
        setCachedData(CACHE_KEYS.SESSIONS, updatedSessions);
        
        // Render combined data
        renderCombinedWorkoutData(sessionData);
        
        if (callback) callback(sessionData);
        
    }).catch(error => {
        console.error('Error fetching workout data:', error);
        
        // Try to use any available cache as fallback
        if (hasSessionCache) {
            console.log('Using stale session cache as fallback');
            const sessionData = cachedSessions[date];
            renderCombinedWorkoutData(sessionData);
            if (callback) callback(sessionData);
        } else {
            // Show error state
            const container = document.getElementById('workout-session-container');
            if (container) {
                container.innerHTML = `<div class='alert alert-danger'>Error loading workout data. Please refresh the page.</div>`;
            }
            if (callback) callback({ success: false, error: 'Failed to load data' });
        }
    });
}

// Helper function to fetch combined session data (including cardio)
function fetchCombinedSessionData(date) {
    return new Promise((resolve, reject) => {
        $.post("/workout/get_session", { 
            date: date,
            csrf_token: $('meta[name=csrf-token]').attr('content')
        })
        .done(data => resolve(data))
        .fail((xhr, status, error) => reject(new Error(`Combined session fetch failed: ${error}`)));
    });
}

// Background fetch for cache updates
function fetchAndUpdateBackground(date) {
    setTimeout(() => {
        fetchCombinedSessionData(date).then(sessionData => {
            // Update cache
            const updatedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
            updatedSessions[date] = { ...sessionData, timestamp: Date.now() };
            setCachedData(CACHE_KEYS.SESSIONS, updatedSessions);
            
            console.log('🔄 Background cache update completed for', date);
        }).catch(error => {
            console.error('Background update failed:', error);
        });
    }, 1000);
}

// Render combined workout data (session + cardio from single response)
function renderCombinedWorkoutData(sessionData) {
    const container = document.getElementById('workout-session-container');
    if (!container) {
        console.error('workout-session-container not found');
        return;
    }
    
    // ✅ CHECK FOR ACTIVE TIMER BEFORE CLEARING DOM
    let timerWasRunning = false;
    let timerDisplay = null;
    
    if (typeof workoutTimer !== 'undefined' && workoutTimer.isActive) {
        timerWasRunning = true;
        timerDisplay = container.querySelector('#workout-timer-container');
        console.log('Timer is active, preserving display');
    }
    
    // Clear container
    container.innerHTML = '';
    
    // ✅ RESTORE TIMER DISPLAY IF IT WAS RUNNING
    if (timerWasRunning && timerDisplay) {
        container.appendChild(timerDisplay.cloneNode(true));
        console.log('Timer display restored after DOM clear');
    }
    
    // Check if we have any data to display
    const hasWorkoutData = sessionData.success && sessionData.session;
    const hasCardioData = sessionData.cardio_sessions && sessionData.cardio_sessions.length > 0;
    
    if (!hasWorkoutData && !hasCardioData) {
        container.insertAdjacentHTML('beforeend', `<div class='alert alert-info'><span data-i18n="noworkoutmessage">No workout session found for this date.</span></div>`);
        return;
    }
    
    // Render strength training data first
    if (hasWorkoutData) {
        console.log('📋 Rendering strength training data');
        if (typeof renderWorkoutSession === "function") {
            renderWorkoutSession(sessionData.session, sessionData.exercises);
        }
    }
    
    // Render cardio data with delay to ensure DOM is ready
    if (hasCardioData) {
        console.log('❤️ Rendering cardio data for', sessionData.cardio_sessions.length, 'sessions');
        
        setTimeout(() => {
            if (typeof displayCardioSessions === "function") {
                displayCardioSessions(sessionData.cardio_sessions);
            } else {
                console.warn('displayCardioSessions function not available');
            }
        }, 50);
    }
    
    // ✅ ENSURE TIMER KEEPS RUNNING AFTER DOM CHANGES
    if (timerWasRunning && typeof workoutTimer !== 'undefined' && workoutTimer.isActive) {
        // Make sure the timer interval is still running
        if (!workoutTimer.intervalId && typeof updateTimerDisplay === 'function') {
            workoutTimer.intervalId = setInterval(updateTimerDisplay, 1000);
            console.log('Timer interval restarted after DOM update');
        }
        
        // Update the display immediately
        if (typeof updateTimerDisplay === 'function') {
            updateTimerDisplay();
        }
    }
    
    console.log('✅ Combined workout data rendered successfully');
}
// Get exercises from cache or server
function getExercisesWithCache(callback) {
    console.log("Fetching exercises...");

    const cachedExercises = getCachedData(CACHE_KEYS.EXERCISES, CACHE_EXPIRATION.EXERCISES);

    if (cachedExercises && cachedExercises.length > 0) {
        console.log('Using cached exercises:', cachedExercises);
        window.exercises = cachedExercises;

        // render after data is set
        renderExerciseOptions();

        if (typeof callback === "function") callback();

    } else {
        console.log('No cached exercises, fetching from server');

        $.get("/workout/exercises", function (data) {
            console.log('Server response:', data);

            if (data.exercises && data.exercises.length > 0) {
                window.exercises = data.exercises;
                setCachedData(CACHE_KEYS.EXERCISES, window.exercises);

                // render after fetching
                renderExerciseOptions();

                if (typeof callback === "function") callback();
            } else {
                console.error('No exercises in response');
            }

        }).fail(function(xhr, status, error) {
            console.error('Failed to fetch exercises:', status, error, xhr.responseText);
        });
    }
}

// Get templates from cache or server
function getTemplatesWithCache() {
    const cachedTemplates = getCachedData(CACHE_KEYS.TEMPLATES, CACHE_EXPIRATION.TEMPLATES);

    if (cachedTemplates && cachedTemplates.length > 0) {
        console.log('Using cached templates');
        renderTemplates(cachedTemplates);

        setTimeout(() => {
            $.get("/workout/templates", function (data) {
                setCachedData(CACHE_KEYS.TEMPLATES, data.templates || []);
            });
        }, 1000);
    } else {
        $.get("/workout/templates", function (data) {
            const templates = data.templates || [];
            setCachedData(CACHE_KEYS.TEMPLATES, templates);
            renderTemplates(templates);
        }).fail(function () {
            const errorItem = '<li><a class="dropdown-item" href="#">Error loading templates</a></li>';
            $("#template-list-desktop").html(errorItem);
            $("#template-list-mobile").html(errorItem);
        });
    }
}

// Update cache after modifying data
function updateSessionCache(date, data) {
    const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
    cachedSessions[date] = { ...data, timestamp: Date.now() };
    setCachedData(CACHE_KEYS.SESSIONS, cachedSessions);
}

// Cleanup stale cache entries
function cleanupStaleCache() {
    const timestamps = JSON.parse(localStorage.getItem(CACHE_KEYS.TIMESTAMPS) || '{}');
    const now = Date.now();

    Object.keys(timestamps).forEach(key => {
        if (now - timestamps[key] > CACHE_EXPIRATION.SESSIONS * 2) {
            localStorage.removeItem(key);
            delete timestamps[key];
        }
    });

    localStorage.setItem(CACHE_KEYS.TIMESTAMPS, JSON.stringify(timestamps));
}
