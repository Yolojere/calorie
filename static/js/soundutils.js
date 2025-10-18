const SoundManager = {
    // Sound cache to prevent recreating Audio objects
    sounds: {},
    
    // Default volume (0.0 to 1.0)
    defaultVolume: 0.5,
    
    // User preference for sound enabled/disabled
    enabled: true,
    
    /**
     * Initialize the sound manager
     */
    init: function() {
        // Load user preference from localStorage
        const soundPref = localStorage.getItem('soundEnabled');
        if (soundPref !== null) {
            this.enabled = soundPref === 'true';
        }
        
        // Preload common sounds
        this.preload('success', '/static/sounds/successclick.mp3');
        this.preload('successtwo', '/static/sounds/successclicktwo.mp3');
        this.preload('delete', '/static/sounds/delete.mp3');
        this.preload('levelup', '/static/sounds/levelup.mp3');
        
        console.log('Sound Manager initialized');
    },
    
    /**
     * Preload a sound file
     * @param {string} name - Identifier for the sound
     * @param {string} path - Path to the audio file
     */
    preload: function(name, path) {
        if (!this.sounds[name]) {
            const audio = new Audio(path);
            audio.volume = this.defaultVolume;
            audio.preload = 'auto';
            this.sounds[name] = audio;
        }
    },
    
    /**
     * Play a sound
     * @param {string} name - Identifier of the sound to play
     * @param {number} volume - Optional volume override (0.0 to 1.0)
     */
    play: function(name, volume = null) {
        if (!this.enabled) return;
        
        const sound = this.sounds[name];
        if (!sound) {
            console.warn(`Sound "${name}" not found. Please preload it first.`);
            return;
        }
        
        try {
            // Clone the audio to allow overlapping sounds
            const soundClone = sound.cloneNode();
            soundClone.volume = volume !== null ? volume : this.defaultVolume;
            
            // Play and clean up
            const playPromise = soundClone.play();
            
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        // Playback started successfully
                    })
                    .catch(error => {
                        console.warn('Sound playback failed:', error);
                    });
            }
            
            // Clean up after playing
            soundClone.addEventListener('ended', function() {
                this.remove();
            });
            
        } catch (error) {
            console.error('Error playing sound:', error);
        }
    },
    
    /**
     * Play the success sound
     */
    playSuccess: function() {
        this.play('success');
    },
        playSuccesstwo: function() {
        this.play('successtwo');
    },
        playDelete: function() {
        this.play('delete');
    },
    playLevelup: function() {
        this.play('levelup');
    },

    
    /**
     * Set volume for all sounds
     * @param {number} volume - Volume level (0.0 to 1.0)
     */
    setVolume: function(volume) {
        this.defaultVolume = Math.max(0, Math.min(1, volume));
        Object.values(this.sounds).forEach(sound => {
            sound.volume = this.defaultVolume;
        });
    },
    
    /**
     * Enable/disable all sounds
     * @param {boolean} enabled
     */
    setEnabled: function(enabled) {
        this.enabled = enabled;
        localStorage.setItem('soundEnabled', enabled.toString());
    },
    
    /**
     * Register a new sound
     * @param {string} name - Identifier for the sound
     * @param {string} path - Path to the audio file
     */
    register: function(name, path) {
        this.preload(name, path);
    }
};

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        SoundManager.init();
    });
} else {
    SoundManager.init();
}

// Make available globally
window.SoundManager = SoundManager;