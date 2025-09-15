// translations.js
const translations = {
  en: {
    // Existing translations
    home: "Home",
    workouts: "Workouts",
    add_food: "Add Food",
    history: "History",
    activity: "Activity",
    settings: "Settings",
    save_workout: "Save W.O.",
    cancel: "Cancel",
    save_workout_header: "Save Workout",
    workout_name_placeholder: "e.g. Push Day, Chest Volume, etc.",
    tooltip_home: "Go to home page",
    tooltip_workouts: "View your workouts",
    tooltip_add_food: "Add a new food item",
    tooltip_history: "View your history",
    tooltip_activity: "View your activity",
    tooltip_settings: "View your settings",
    profile: "Profile",
    logout: "Logout",
    kcal: "kcal",

    // NEW TRANSLATIONS FOR ACTIVITY PAGE
    app_title: "TrackYou Activity",
    track_you: "Track You",
    track_measure_repeat: "- Track, measure, repeat -",
    beta: "BETA",
    
    // Activity & TDEE Calculator
    activity_tdee_calculator: "Activity & TDEE Calculator",
    calculate_bmr_tdee_description: "Calculate your Basal Metabolic Rate (BMR) and Total Daily Energy Expenditure (TDEE)",
    
    // Personal Information
    personal_information: "Personal Information",
    male: "Male",
    female: "Female",
    age_years: "Age (years)",
    enter_age: "Enter age",
    weight_kg: "Weight (kg)",
    enter_weight: "Enter weight",
    height_cm: "Height (cm)",
    enter_height: "Enter height",
    
    // Activity Tracking
    daily_activity_tracking: "Daily Activity Tracking",
    sleep: "Sleep",
    hours: "Hours",
    minutes: "Minutes",
    hr: "hr",
    min: "min",
    intense_exercise: "Intense Exercise",
    moderate_exercise: "Moderate Exercise",
    light_exercise: "Light Exercise",
    standing_walking: "Standing/Walking",
    steps_future: "Steps (Future)",
    steps: "Steps",
    coming_soon: "Coming soon",
    
    // Buttons
    terms: "Terms of Service",
    privacy: "Privacy Policy",
    calculate_tdee: "Calculate TDEE",
    save_tdee: "Save TDEE",
    save_metrics: "Save Metrics",
    saved: "Saved!",
    remember_me: "Remember me",
    login: "Login",
    login_failed: "Login Unsuccessful. Please check email and password",
    register_error: "Username or email already exists",
    email_error: "Email already registered. Please use a different email.",
    username_error: "Username already taken. Please choose a different one.",
    username_required: "Username is required",
    username_length: "Username must be between 3 and 20 characters",
    username_invalid: "Username can only contain letters, numbers, and underscores",
    email_required: "Email is required",
    email_invalid: "Email is not valid",
    password_required: "Password is required",
    password_length: "Password must be at least 8 characters",
    confirm_required: "Password confirmation is required",
    password_must_match: "Passwords must match",
    register: "Register",
    create_account: "Create Account",
    password_hint: "Use atleast 8 letters , including big letters, numbers and symbols.",
    register_success: "Account created! you can now login to the page",



    
    
    // Results
    energy_expenditure_results: "Energy Expenditure Results",
    basal_metabolic_rate_bmr: "Basal Metabolic Rate (BMR)",
    bmr_description: "How much your body needs calories at rest.",
    bmr_function_description: "(function of organs, heart, brain - breathing, temperature and so on..)",
    total_daily_energy_expenditure_tdee: "Total Daily Energy Expenditure (TDEE)",
    total_calories_burned_per_day: "Total calories burned per day",
    
    // Energy Breakdown
    energy_breakdown: "Energy Breakdown",
    bmr_short: "BMR",
    other_fidgeting: "Other (Fidgeting, passive moving etc.)",
    
    // Loading messages
    analyzing: "Analyzing...",
    calculating_energy_expenditure: "Calculating your energy expenditure",
    
    // Error messages
    fill_all_personal_info: "Please fill in all personal information fields",
    error_in_calculation: "Error in calculation:",
    error_saving_console: "Error saving. Please check console for details.",
    error_saving: "Error saving:",
    unknown_error: "Unknown error",
    personal_information: "Personal Information",

    // Nutrition
    bigserving: "Big Serving",
    favourite: "Favourite",
    bigserving_g: "Big Serving (g)",
    add_custom_food: "Add Custom Food",
    scan_label: "Scan Label (Incoming)",
    ean_barcode: "EAN/Barcode",
    calories_per: "Calories (per 100g)",
    not_required: "not required",
    fats_g: "Fats (g)",
    saturated_g: "Saturated (g)",
    carbs_g: "Carbohydrates (g)",
    sugars_g: "Sugars (g)",
    fiber_g: "Fiber (g)",
    proteins_g: "Proteins (g)",
    salt_g: "Salt (g)",
    serving_g: "Serving Size (g)",
    half_g: "Half Package (g)",
    entire_g: "Entire Package (g)",
    per_grams: "Per (grams)",
    food_success: "Food added successfully!",
    required: "required",
    calories: "Calories",
    proteins: "Proteins",
    carbs: "Carbs",
    fats: "Fats",
    saturated: "Saturated",
    sugars: "Sugars",
    fiber: "Fiber",
    salt: "Salt",
    c: "C",
    f: "F",
    p: "P",

    // Food log
    today: "Today",
    move: "Move",
    save: "Save",
    apply: "Apply",
    clear: "Clear",
    food_log: "Food Log",
    serving: "Serving",
    half: "Half",
    entire: "Entire",
    breakfast: "Breakfast",
    lunch: "Lunch",
    dinner: "Dinner",
    snack: "Snack",
    other: "Other",
    totals: "Totals",
    no_food_message: "no food logged yet",
    ean_not_found: "EAN",
    in_data_base: "not found in database",
    create_new_food: "Create New Food",
    no_results_found: "No results found",

    // Days
    monday: "Monday",
    tuesday: "Tuesday",
    wednesday: "Wednesday",
    thursday: "Thursday",
    friday: "Friday",
    saturday: "Saturday",
    sunday: "Sunday",
    sun: "Sun",
    mon: "Mon",
    tue: "Tue",
    wed: "Wed",
    thu: "Thu",
    fri: "Fri",
    sat: "Sat",

    grams: "g",

    // Workouts
    strength: "Strength",
    hypertrophy: "Hypertrophy",
    focus_type_comp: "Focus (comparing vs last workout of that focus)",
    workout_name_input: "e.g. Legs, Chest Volume, etc.",
    workout_name: "Workout Name",
    save_exercise: "Save Exercise",
    description: "Description",
    loading_workout_data: "Loading workout data...",
    workout_log: "Workout Log",
    copy_this_workout: "Copy This Workout",
    comments: "Comments",
    rir_reps: "RiR (Reps in Reserve)",
    weight: "Weight",
    muscle_group: "Muscle Group",
    add_exercise: "Add Exercise",
    set: "Set",
    sets: "Sets",
    reps: "Reps",
    volume: "Volume",
    delete: "Delete",
    chest: "Chest",
    back: "Back",
    legs: "Legs",
    shoulders: "Shoulders",
    arms: "Arms",
    core: "Core",
    workout_tracker: "Workout Tracker",
    prev: "Prev",
    loading: "Loading...",
    next: "Next",
    add_new_set: "Add New Set",

    // Modals & buttons
    close: "Close",
    confirm: "Confirm",
    add: "Add",
    edit: "Edit",
    remove: "Remove",
    update: "Update",
    ok: "OK",
    yes: "Yes",
    no: "No",
    are_you_sure: "Are you sure?",
    maintaining: "Maintaining",
    calories_over: "Calories over",
    calories_left: "Calories left",
    copy: "Copy",
    select_date: "Select date",
    scan_barcode: "Scan Barcode",
    position_barcode_in_the_scan_area: "POSITION BARCODE IN THE SCAN AREA",
    save_food_template: "Save Food Template",
    copy_current_workout: "Copy current workout to:",
    apply_template: "Apply Template",
    apply_food_template: "Apply food template",
    select_template: "Select template",
    template_name: "Template Name",
    template_preview: "Template Preview",
    select_meal_group: "Select meal group",
    meal_group: "Meal Group",
    move_or_copy_items: "Move or Copy Items",
    confirm_clear_session: "Are you sure you want to clear all items?",
    error_apply_template: "Error: Failed to apply template",
    failed_to_apply_template: "Failed to apply template",
    failed_to_apply_template_retry: "Failed to apply template. Please try again.",
    loading_templates: "Loading templates...",
    no_template_available: "No templates available",
    error_loading_template: "Error loading templates",
    applying: "Applying",
    adding: "Adding",

    // Progress bars - NEW
    proteins_upper: "PROTEINS",
    carbs_upper: "CARBS", 
    fats_upper: "FATS",
    saturated_upper: "SATURATED",
    sugars_upper: "SUGARS",
    fiber_upper: "FIBER",
    salt_upper: "SALT",

    // Placeholders - NEW
    search_food_placeholder: "Search food or scan EAN...",
    insert_yourself: "Insert Yourself",
    enter_template_name: "Enter template name",
    enter_recipe_name: "Enter recipe name",
    optional_notes: "Optional notes about the set",
    enter_your: "Enter your username",

    // Food modal
    add_food_item: "Add Food Item",
    food_name: "Name",
    amount: "Amount",
    nutrition: "Nutrition",
    save_food: "Save Food",
    search: "Search...",

    // History modal
    workout_history: "Workout History",
    session: "Session",
    date: "Date",
    exercises: "Exercises",
    duration: "Duration",
    exercise: "Exercise",

    // Empty states
    no_workout_message: "No workout recorded for this day. Add your first set below!",
    no_data: "No data available",
    
    // Additional status messages
    action: "Action",
     // Account page translations
    account: "Account",
    account_profile: "Your Account Profile",
    account_type: "Account Type",
    general_info: "General Information",
    full_name: "Full Name",
    full_name_placeholder: "John Doe",
    main_sport: "Main Sport / Activity",
    main_sport_placeholder: "e.g. Weightlifting, Running",
    social_media: "Social Media",
    update_profile: "Update Profile",
    updating: "Updating",
    daily_activity_tracking: "Daily Activity Tracking",
    health_metrics: "Health Metrics",
    current_weight: "Current Weight",
    daily_energy: "Daily Energy Expenditure",
    last_updated: "Last updated from activity calculator",
    based_on_activity: "Based on your activity level",
    activity_tdee_calculator: "Activity & TDEE Calculator",
    update_metrics: "Update Metrics",
    request_password_reset: "Request Password Reset",
    reset_password: "Reset Password",
    signIn: "Sign In",
    sendPasswordReset: "Send Password Reset Link",
    weSendPasswordReset: "We'll send you an email with a link to reset your password.",
    secure: "Secure",
    encrypted: "Encrypted",
    protected: "Protected",
    verified: "Verified",
    choose_avatar: "Choose Your Avatar",
    select_from_options: "Select from our options",
    upload_image: "Upload Your Own Image",
    max_file_size: "Max file size: 2MB (JPG, PNG)",
    change_avatar: "Change Avatar",
    avatar_updated: "Avatar updated successfully!",
    select_image: "Please select an image file (JPG, PNG).",
    image_too_large: "Please select an image smaller than 2MB.",
    platform: "Platform",
    and: "and",
    enter_handle: "Enter your handle",
    handle_instructions: "Enter your username without @ symbol",
    add_social: "Add social media",
    username: "username",
    athlete_id: "athlete ID",
    enter_valid_handle: "Please enter a valid handle",
    invalid_handle: "Invalid handle or already exists",
    added_successfully: "added successfully!",
    removed: "removed",
    no_socials: "No social media accounts added",
    visit: "Visit",
    on: "on",
    remove_social: "Remove this social link",
    not_set: "Not set",
    not_calculated: "Not calculated"
  },
  fi: {
    // Existing Finnish translations
    home: "Koti",
    workouts: "Harjoitukset", 
    add_food: "Lisää Ruoka",
    history: "Historia",
    activity: "Aktiivisuus",
    settings: "Asetukset",
    save_workout: "Tallenna W.O.",
    save_workout_header: "Tallenna Treeni",
    cancel: "Peruuta",
    workout_name_placeholder: "esim. Punnerruspäivä, Rintalihas Volyymi, jne.",
    tooltip_home: "Siirry kotisivulle",
    tooltip_workouts: "Katso harjoituksesi",
    tooltip_add_food: "Lisää uusi ruoka",
    tooltip_history: "Näytä historia",
    tooltip_activity: "Näytä aktiviteetti",
    tooltip_settings: "Asetukset",
    profile: "Profiili",
    logout: "Kirjaudu Ulos",
    kcal: "kcal",

    // NEW FINNISH TRANSLATIONS FOR ACTIVITY PAGE
    app_title: "TrackYou Aktiivisuus",
    track_you: "Track You",
    track_measure_repeat: "- Seuraa, mittaa, toista -",
    beta: "BETA",
    
    // Activity & TDEE Calculator
    activity_tdee_calculator: "Aktiivisuus & TDEE Laskin",
    calculate_bmr_tdee_description: "Laske perusaineenvaihdunta (BMR) ja kokonaisenergiankulutus (TDEE)",
    
    // Personal Information
    personal_information: "Henkilötiedot",
    male: "Mies",
    female: "Nainen",
    age_years: "Ikä (vuotta)",
    enter_age: "Syötä ikä",
    weight_kg: "Paino (kg)",
    enter_weight: "Syötä paino",
    height_cm: "Pituus (cm)",
    enter_height: "Syötä pituus",
    
    // Activity Tracking
    daily_activity_tracking: "Päivittäinen Aktiivisuusseuranta",
    sleep: "Uni",
    hours: "Tunnit",
    minutes: "Minuutit",
    hr: "t",
    min: "min",
    intense_exercise: "Intensiivinen Liikunta",
    moderate_exercise: "Kohtalainen Liikunta",
    light_exercise: "Kevyt Liikunta",
    standing_walking: "Seisominen/Kävely",
    steps_future: "Askeleet (Tulossa)",
    steps: "Askelta",
    coming_soon: "Tulossa pian",
    
    // Buttons
    terms: "Käyttöehdot",
    privacy: "Tietosuojakäytäntö",
    calculate_tdee: "Laske TDEE",
    save_tdee: "Tallenna TDEE",
    save_metrics: "Tallenna Mittaukset",
    saved: "Tallennettu!",
    remember_me: "Muista minut",
    login: "Kirjaudu Sisään",
    login_failed: "Kirjautuminen epäonnistui. Tarkista sähköposti ja salasana",
    register_error: "Sähköposti tai käyttäjänimi on jo käytössä",
    email_error: "Sähköposti on jo käytössä. Valitse toinen",
    username_error: "Käyttäjänimi on jo käytössä. Valitse toinen",
    username_required: "Käyttäjänimi on pakollinen",
    username_length: "Käyttäjänimen on oltava 3–20 merkkiä",
    username_invalid: "Virheellinen käyttäjänimi",
    email_required: "Sähköpostiosoite on pakollinen",
    email_invalid: "Virheellinen sähköpostiosoite",
    password_required: "Salasana on pakollinen",
    password_length: "Salasanan on oltava vähintään 6 merkkiä",
    confirm_required: "Salasanan vahvistus on pakollinen",
    password_must_match: "Salasanan on oltava sama",
    register: "Rekisteröidy",
    create_account: "Luo uusi tili",
    password_hint: "Käytä vähintään 8 merkkiä, mukaan lukien isoja kirjaimia, numeroita ja erikoismerkkejä.",
    register_success: "Tili luotu! Voit nyt kirjautua sisään",

    
    // Results
    energy_expenditure_results: "Energiankulutus Tulokset",
    basal_metabolic_rate_bmr: "Perusaineenvaihdunta (BMR)",
    bmr_description: "Kuinka paljon kehosi tarvitsee kaloreita levossa.",
    bmr_function_description: "(elimien, sydämen, aivojen toiminta - hengitys, lämpötila jne..)",
    total_daily_energy_expenditure_tdee: "Kokonaisenergiankulutus (TDEE)",
    total_calories_burned_per_day: "Yhteensä poltettuja kaloreita päivässä",
    
    // Energy Breakdown
    energy_breakdown: "Energian Jakautuminen",
    bmr_short: "BMR",
    other_fidgeting: "Muu (Liikkuminen, passiivinen liike jne.)",
    
    // Loading messages
    analyzing: "Analysoidaan...",
    calculating_energy_expenditure: "Lasketaan energiankulutusta",
    
    // Error messages
    fill_all_personal_info: "Täytä kaikki henkilötiedot",
    error_in_calculation: "Virhe laskennassa:",
    error_saving_console: "Virhe tallennuksessa. Tarkista konsoli.",
    error_saving: "Virhe tallennuksessa:",
    unknown_error: "Tuntematon virhe",
    personal_information: "Henkilötiedot",

    // Nutrition
    favourite: "Suosikki",
    bigserving: "Iso Annos",
    bigserving_g: "Iso Annos (g)",
    add_custom_food: "Lisää uusi ruoka",
    scan_label: "Skannaa Ravintoarvot (Tulossa)",
    ean_barcode: "EAN/Viivakoodi",
    calories_per: "Kalorit (per 100g)",
    not_required: "ei vaadita",
    required: "pakollinen",
    fats_g: "Rasvat (g)",
    saturated_g: "Tyydyttyneet (g)",
    carbs_g: "Hiilihydraatit (g)",
    sugars_g: "Sokeri (g)",
    fiber_g: "Kuitu (g)",
    proteins_g: "Proteiini (g)",
    salt_g: "Suola (g)",
    serving_g: "kpl/annos (g)",
    half_g: "Puoli PKT (g)",
    entire_g: "Koko Paska (g)",
    per_grams: "Per (grams)",
    food_success: "Lisätty tietokantaan!",    
    calories: "Kalorit",
    proteins: "Proteiini",
    carbs: "Hiilari",
    fats: "Rasva",
    saturated: "Tyydyttynyt",
    sugars: "Sokeri",
    fiber: "Kuitu",
    salt: "Suola",
    // Nutrition abbreviations
    c: "HH",
    f: "R", 
    p: "P",

    // Food log
    today: "Tänään",
    move: "Siirrä",
    save: "Tallenna",
    apply: "Pohja",
    clear: "Tyhjennä",
    food_log: "Ruokapäiväkirja",
    serving: "kpl/annos",
    half: "Puoli Pakkausta",
    entire: "Koko Paska",
    OTHER: "MUU",
    breakfast: "Aamiainen",
    lunch: "Lounas",
    dinner: "Päivälllinen",
    snack: "Välipala",
    other: "Muu",
    BREAKFAST: "AAMIAINEN",
    LUNCH: "LOUNAS",
    DINNER: "PÄIVÄLLINEN",
    SNACK: "VÄLIPALA",
    OTHER: "MUU",
    totals: "Yhteenveto",
    ean_not_found: "Viivakoodia",
    in_data_base: "ei löydetty tietokannasta",
    create_new_food: "Luo Uusi Ruoka",
    no_results_found: "Ei tuloksia",

    // Days
    monday: "Maanantai",
    tuesday: "Tiistai",
    wednesday: "Keskiviikko",
    thursday: "Torstai",
    friday: "Perjantai",
    saturday: "Lauantai",
    sunday: "Sunnuntai",
    mon: "Ma",
    tue: "Ti",
    wed: "Ke",
    thu: "To",
    fri: "Pe",
    sat: "La",
    sun: "Su",

    grams: "g",

    // Workouts
    hypertrophy: "Hypertrofia",
    strength: "Voima",
    focus_type_comp: "Focus (Verrataan viimeiseen saman fokuksen treeniin)",
    workout_name_input: "esim. Jalat, Rintalihas Volyymi, jne.",
    workout_name: "Treenin Nimi",
    save_exercise: "Tallenna Liike",
    description: "Kuvaus",
    loading_workout_data: "Ladataan treenitietoja...",
    workout_log: "Treeni Päiväkirja",
    copy_this_workout: "Kopioi Tämä Treeni",
    comments: "Kommentit",
    rir_reps: "RiR (Toistoa Jäljellä)",
    weight: "Paino",
    muscle_group: "Lihasryhmä",
    add_exercise: "Lisää Liike",
    set: "Sarja",
    sets: "Sarjaa",
    reps: "Toistoa",
    volume: "Volyymi",
    delete: "Poista",
    chest: "Rinta",
    back: "Selkä",
    legs: "Jalat",
    shoulders: "Olkapäät",
    arms: "Kädet",
    core: "Vatsa",
    workout_tracker: "Treeni Seuranta",
    prev: "Edellinen",
    loading: "Ladataan...",
    next: "Seuraava",
    add_new_set: "Lisää Uusi Sarja",

    // Modals & buttons
    close: "Sulje",
    confirm: "Vahvista",
    add: "Lisää",
    edit: "Muokkaa",
    remove: "Poista",
    update: "Päivitä",
    ok: "OK",
    yes: "Kyllä",
    no: "Ei",
    are_you_sure: "Oletko varma?",
    maintaining: "Ylläpito",
    calories_over: "Yli kulutuksen", 
    calories_left: "Kaloria jäljellä",
    meal_group: "Ateria ryhmä",
    select_meal_group: "Valitse ateria ryhmä",
    copy: "Kopioi",
    select_date: "Valitse päivä",
    scan_barcode: "Skannaa viivakoodi",
    position_barcode_in_the_scan_area: "Laita viivakoodi skannaus alueelle",
    save_food_template: "Tallenna pohja",
    copy_current_workout: "Kopioi nykyinen treeni päivämäärään:",
    apply_template: "Käytä pohja",
    apply_food_template: "Käytä ruoka pohja",
    select_template: "Valitse pohja",
    template_name: "Pohjan nimi",
    template_preview: "Pohjan esikatselu",
    move_or_copy_items: "Siirrä tai Kopioi kohteet",
    confirm_clear_session: "Oletko varma, että haluat tyhjentää kaikki kohteet?",
    error_apply_template: "Virhe: epäonnistui soveltaa pohjaa",
    failed_to_apply_template: "Epäonnistui soveltaa pohjaa",
    failed_to_apply_template_retry: "Pohjan soveltaminen epäonnistui. Yritä uudelleen.",
    loading_templates: "Ladataan pohjia...",
    no_template_available: "Ei pohjia saatavilla",
    error_loading_template: "Virhe ladattaessa pohjia",
    applying: "Sovelletaan",
    adding: "Lisätään",

    // Progress bars - NEW (Finnish translations)
    proteins_upper: "PROTEIINI",
    carbs_upper: "HIILARI", 
    fats_upper: "RASVA",
    saturated_upper: "TYYDYTTYNYT",
    sugars_upper: "SOKERI",
    fiber_upper: "KUITU",
    salt_upper: "SUOLA",

    // Placeholders - NEW
    search_food_placeholder: "Hae ruokaa tai skannaa viivakoodi...",
    insert_yourself: "Syötä itse",
    enter_template_name: "Syötä pohjan nimi",
    enter_recipe_name: "Syötä reseptin nimi",
    optional_notes: "Muistiinpanoja, kone säädöt yms.",

    // Food modal
    add_food_item: "Lisää Ruoka",
    food_name: "Nimi",
    amount: "Määrä",
    nutrition: "Ravintoarvot",
    save_food: "Tallenna Ruoka",
    search: "Hae...",
    no_food_message: "Ei kirjattua ruokaa vielä",

    // History modal
    workout_history: "Harjoitushistoria",
    session: "Harjoitus",
    date: "Päivämäärä",
    exercises: "Liikkeet",
    duration: "Kesto",
    exercise: "Liike",

    // Empty states
    no_workout_message: "Tälle päivälle ei ole tallennettu harjoitusta. Lisää ensimmäinen sarja alla!",
    no_data: "Ei tietoja saatavilla",
    
    // Additional status messages
    action: "Toiminto",
      account: "Tili",
    account_profile: "Tilisi Profiili",
    account_type: "Tilin Tyyppi",
    general_info: "Yleiset Tiedot",
    full_name: "Koko Nimi",
    full_name_placeholder: "Matti Meikäläinen",
    main_sport: "Pääurheilu / Aktiviteetti",
    main_sport_placeholder: "esim. Painonnosto, Juoksu",
    social_media: "Sosiaalinen Media",
    update_profile: "Päivitä Profiili",
    updating: "Päivitetään",
    daily_activity_tracking: "Päivittäinen Aktiivisuusseuranta",
    health_metrics: "Terveysmittarit",
    current_weight: "Nykyinen Paino",
    daily_energy: "Päivittäinen Energiankulutus",
    last_updated: "Päivitetty viimeksi aktiviteettilaskurista",
    based_on_activity: "Perustuu aktiivisuustasoosi",
    activity_tdee_calculator: "Aktiivisuus & TDEE Laskin",
    update_metrics: "Päivitä Mittaukset",
    request_password_reset: "Pyydä Salasanan Nollaus",
    reset_password: "Nollaa Salasana",
    signIn: "Kirjaudu Sisään",
    sendPasswordReset: "Lähetä Nollauslinkki",
    weSendPasswordReset: "Lähetämme sinulle sähköpostin, jossa on linkki salasanan nollaamiseen.",
    secure: "Turvallinen",
    encrypted: "Salattu",
    protected: "Suojattu",
    verified: "Varmennettu",
    choose_avatar: "Valitse Avatarisi",
    select_from_options: "Valitse vaihtoehdoistamme",
    upload_image: "Lataa Oma Kuva",
    max_file_size: "Maksimi tiedostokoko: 2MB (JPG, PNG)",
    change_avatar: "Vaihda Avataria",
    avatar_updated: "Avatar päivitetty onnistuneesti!",
    select_image: "Valitse kuva tiedosto (JPG, PNG).",
    image_too_large: "Valitse alle 2MB kokoinen kuva.",
    platform: "Alusta",
    and: "ja",
    enter_handle: "Syötä",
    handle_instructions: "Syötä käyttäjänimesi ilman @-merkkiä",
    add_social: "Lisää sosiaalinen media",
    username: "Käyttäjätunnus",
    athlete_id: "urheilijan ID",
    enter_valid_handle: "Syötä kelvollinen käyttäjätunnus",
    invalid_handle: "Virheellinen käyttäjätunnus tai on jo olemassa",
    added_successfully: "lisätty onnistuneesti!",
    removed: "poistettu",
    no_socials: "Ei sosiaalisen median tilejä lisätty",
    visit: "Vieraile",
    on: "-sivustolla",
    remove_social: "Poista tämä sosiaalinen linkki",
    not_set: "Ei asetettu",
    not_calculated: "Ei laskettu",
    enter_your: "Syötä"
  }
};

// current language
let currentLang = localStorage.getItem("lang") || "fi";

// helper
function t(key) {
  return translations[currentLang][key] || key;
}
    function updateMealGroupTranslations() {
    // Update meal group names in the select dropdown
    $('#meal-group option[value="breakfast"]').text(t('breakfast'));
    $('#meal-group option[value="lunch"]').text(t('lunch'));
    $('#meal-group option[value="dinner"]').text(t('dinner'));
    $('#meal-group option[value="snack"]').text(t('snack'));
    $('#meal-group option[value="other"]').text(t('other'));
    
    // Update existing meal group headers
    $('.food-group').each(function() {
        const group = $(this).data('group');
        const headerText = t(group.toUpperCase());
        $(this).find('.group-title').text(headerText);
    });
}
function updateNutritionAbbreviations() {
    // Update all nutrition value abbreviations dynamically
    $('.nutrition-value-xxs span').each(function() {
        let text = $(this).text();
        
        if (currentLang === 'fi') {
            // Replace C with HH and F with R for Finnish
            text = text.replace(/(\d+\.?\d*)\s*g\s*C/, `$1${t("grams")} ${t("c")}`);
            text = text.replace(/(\d+\.?\d*)\s*g\s*F/, `$1${t("grams")} ${t("f")}`);
            text = text.replace(/(\d+\.?\d*)\s*g\s*P/, `$1${t("grams")} ${t("p")}`);
            // Also update kcal
            text = text.replace(/(\d+\.?\d*)\s*kcal/, `$1 ${t("kcal")}`);
        } else {
            // English - ensure proper format
            text = text.replace(/(\d+\.?\d*)\s*g\s*HH/, `$1${t("grams")} ${t("c")}`);
            text = text.replace(/(\d+\.?\d*)\s*g\s*R/, `$1${t("grams")} ${t("f")}`);
            text = text.replace(/(\d+\.?\d*)\s*g\s*P/, `$1${t("grams")} ${t("p")}`);
        }
        
        $(this).text(text);
    });

    // Update real-time breakdown abbreviations
    $('#rt-breakdown-container .rtb-label').each(function() {
        const key = $(this).attr('data-i18n');
        if (key) {
            $(this).text(t(key));
        }
    });
}
// Enhanced apply translations function
function applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        const text = t(key);

        if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
            if (el.hasAttribute("placeholder")) {
                el.placeholder = text;
            }
        } else if (el.hasAttribute("title")) {
            el.setAttribute("title", text);
        } else {
            // Only replace text if the element has no children (to avoid nuking icons)
            if (el.children.length === 0) {
                el.textContent = text;
            }
        }
    });

    // Fix meal group translations
    updateMealGroupTranslations();
    
    // Update nutrition abbreviations
    updateNutritionAbbreviations();
    
    // Update portion buttons if we have current food
    if (typeof currentFood !== 'undefined' && currentFood) {
        updatePortionButtons(currentFood);
    }
}


document.addEventListener("DOMContentLoaded", applyTranslations);
