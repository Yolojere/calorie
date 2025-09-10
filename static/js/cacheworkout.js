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

// Get session from cache or server
function getSessionWithCache(date, callback) {
    const cachedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};

    if (cachedSessions[date] && cachedSessions[date].timestamp) {
        const isDataFresh = (Date.now() - cachedSessions[date].timestamp) < CACHE_EXPIRATION.SESSIONS;
        if (isDataFresh) {
            console.log('Using cached session data for', date);
            callback(cachedSessions[date]);
        }

        // Still fetch from server in background
        setTimeout(() => {
            $.post("/workout/get_session", { date: date }, function (data) {
                const updatedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
                updatedSessions[date] = data;
                setCachedData(CACHE_KEYS.SESSIONS, updatedSessions);

                if (typeof currentSelectedDate !== "undefined" && date === currentSelectedDate) {
                    renderWorkoutSession(data.session, data.exercises);
                }
            });
        }, 1000);
    } else {
        // Not in cache, fetch from server
        $.post("/workout/get_session", { date: date }, function (data) {
            const updatedSessions = getCachedData(CACHE_KEYS.SESSIONS, CACHE_EXPIRATION.SESSIONS) || {};
            updatedSessions[date] = data;
            setCachedData(CACHE_KEYS.SESSIONS, updatedSessions);

            callback(data);
        });
    }
}

// Get exercises from cache or server
function getExercisesWithCache(callback) {
    console.log("Fetching exercises...");

    const cachedExercises = getCachedData(CACHE_KEYS.EXERCISES, CACHE_EXPIRATION.EXERCISES);

    if (cachedExercises && cachedExercises.length > 0) {
        console.log('Using cached exercises:', cachedExercises);
        window.exercises = cachedExercises;

        // ✅ render after data is set
        renderExerciseOptions();

        if (typeof callback === "function") callback();

    } else {
        console.log('No cached exercises, fetching from server');

        $.get("/workout/exercises", function (data) {
            console.log('Server response:', data);

            if (data.exercises && data.exercises.length > 0) {
                window.exercises = data.exercises;
                setCachedData(CACHE_KEYS.EXERCISES, window.exercises);

                // ✅ render after fetching
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
    cachedSessions[date] = data;
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
