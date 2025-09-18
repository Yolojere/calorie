// translations.js
const translations = {
  en: {
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

    // Food log
    today: "Today",
    move: "Move",
    save: "Save",
    apply: "Apply",
    clear: "Clear",
    no_food_message: "no food logged yet",
    in_data_base: "not found in database",
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
    sun: "Sun",

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
    weight: "Weight (kg)",
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
    copy: "Copy",
    select_date: "Select date",
    copy_current_workout: "Copy current workout to:",
    apply_template: "Apply Template",
    apply_food_template: "Apply food template",
    select_template: "Select template",
    template_name: "Template Name",
    template_preview: "Template Preview: ",
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

    amount: "Amount",
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
        weekDisplay: "Week",
    selectExercise: "Select Exercise",
    noTemplatesFound: "No templates found",
    analyzingWorkout: "Analyzing Your Workout",
    comparingSessions: "Comparing with previous sessions...",
    detectingPRs: "Detecting personal records...",
    calculatingTrends: "Calculating volume trends...",
    finalizingAnalysis: "Finalizing analysis...",
    workoutComplete: "Workout Complete! 🎉",
    performanceAnalysis: "Here's your performance analysis",
    newBestSet: "New Best Set!",
    heaviestWeight: "Heaviest Weight Ever!",
    previousBest: "Previous best",
    totalVolume: "Total Volume",
    setsCompleted: "Sets Completed",
    personalRecords: "Personal Records",
    improvements: "Improvements",
    fromLastWorkout: "from last workout",
    newRecordsToday: "New records today!",
    keepPushing: "Keep pushing!",
    setsImproved: "Sets improved from last time",
    greatEffort: "Great effort today!",
    close: "Close",
    shareResults: "Share Results",
    firstSession: "First session of this focus type!",
    expand: "Expand",
    collapse: "Collapse",
    valmis: "Complete",
    hylkaa: "Discard",
    lisaaSarja: "Add Set"
  },
  
  fi: {
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

    // Food log
    today: "Tänään",
    move: "Siirrä",
    save: "Tallenna",
    apply: "Pohja",
    clear: "Tyhjennä",
    in_data_base: "ei löydetty tietokannasta",
    no_results_found: "Ei tuloksia",

    // Days
    monday: "Maanantai",
    yesterday: "Eilen",
    tomorrow: "Huomenna",
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
    workout_log: "Treenipäiväkirja",
    copy_this_workout: "Kopioi tämä treeni",
    copy: "Kopioi",
    comments: "Kommentit",
    rir_reps: "RiR (Toistoa Jäljellä)",
    weight: "Paino (kg)",
    muscle_group: "Lihasryhmä",
    add_exercise: "Lisää Liike",
    set: "Sarja",
    sets: "Sarjat",
    reps: "Toistot",
    volume: "Volyymi",
    delete: "Poista",
    chest: "Rinta",
    back: "Selkä",
    legs: "Jalat",
    shoulders: "Olkapäät",
    arms: "Kädet",
    core: "Vatsa",
    workout_tracker: "Treenin Seuranta",
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
    select_date: "Valitse päivä",
    scan_barcode: "Skannaa viivakoodi",
    position_barcode_in_the_scan_area: "Laita viivakoodi skannaus alueelle",
    save_food_template: "Tallenna pohja",
    copy_current_workout: "Kopioi nykyinen treeni päivämäärään:",
    apply_template: "Käytä pohja",
    apply_food_template: "Käytä ruoka pohja",
    select_template: "Valitse pohja",
    template_name: "Pohjan nimi",
    template_preview: "Pohjan esikatselu: ",
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
    weekDisplay: "Viikko",
    selectExercise: "Valitse liike",
    noTemplatesFound: "Ei pohjia saatavilla",
    analyzingWorkout: "Analysoidaan treeniäsi",
    comparingSessions: "Verrataan aiempiin sessioihin...",
    detectingPRs: "Etsitään henkilökohtaisia ennätyksiä...",
    calculatingTrends: "Lasketaan volyymikehitystä...",
    finalizingAnalysis: "Viimeistellään analyysiä...",
    workoutComplete: "Harjoitus suoritettu! 🎉",
    performanceAnalysis: "Tässä suoritusanalyysisi",
    newBestSet: "Uusi paras sarja!",
    heaviestWeight: "Raskain paino ikinä!",
    previousBest: "Aiempi paras",
    totalVolume: "Kokonaisvolyymi",
    setsCompleted: "Suoritetut sarjat",
    personalRecords: "Henkilökohtaiset ennätykset",
    improvements: "Parannukset",
    fromLastWorkout: "viime treenistä",
    newRecordsToday: "Uusia ennätyksiä tänään!",
    keepPushing: "Jatka ponnistelua!",
    setsImproved: "Sarjat edistynyt viime kerrasta",
    greatEffort: "Mahtavaa työtä tänään!",
    close: "Sulje",
    shareResults: "Jaa tulokset",
    firstSession: "Ensimmäinen kerta tällä fokuksella!",
    expand: "Laajenna",
    collapse: "Kutista",
    valmis: "Valmis",
    hylkaa: "Hylkää",
    lisaaSarja: "Lisää Sarja",
    applying: "Sovelletaan",
    template_applied_success: "Pohja sovellettu onnistuneesti!",
    error: "Virhe",
    error_loading_template: "Virhe ladattaessa pohjaa",
     // Exercises (static + dynamic ready)
     // CHEST
    "Bench press": "Penkkipunnerrus",
    "Bench press (Barbell)": "Penkkipunnerrus (Levytanko)",
    "Bench press (Dumbell)": "Penkkipunnerrus (Käsipainot)",
    "Bench press (Incline)": "Vinopenkkipunnerrus",
    "Bench press (Machine)": "Penkkipunnerrus (Laite)",
    "Bench press (Smith)": "Penkkipunnerrus (Smith)",
    "Cable cross over": "Ristikkäistalja",
    "Dip (Regular)": "Dippi (Normaali)",
    "Dip (Wide)": "Dippi (Leveä)",
    "Fly (Dumbell)": "Fly (käsipainot)",
    "Fly (Incline)": "Fly (Vinopenkki)",
    "Fly (Machine)": "Fly (Laite)",
    // BACK
    "Back extension": "Selän ojennus",
    "Bent over row (Barbell)": "Kulmasoutu (Levytanko)",
    "Cable pulldown": "Ylätalja",
    "Deadlift (Conventional)": "Maastaveto (Perinteinen)",
    "Deadlift (Sumo)": "Maastaveto (Sumo)",
    "Deadlift (Trap)": "Maastaveto (Trap)",
    "Dumbell row": "Käsipainosoutu",
    "Pull up": "Leuanveto",
    "Pulldown (Machine)": "Ylätalja (Laite)",
    "Row (Machine)": "Soutu (Laite)",
    "Row (T-bar)": "Tankosoutu",
    "Seated cable row": "Soutu taljassa",
    // LEEEEGS
    "Calf (Seated)": "Pohkeet (Istuen)",
    "Calf (Standing)": "Pohkeet (Seisten)",
    "Leg curl (Lying)": "Reiden koukistus (Maaten)",
    "Leg curl (Seated)": "Reiden koukistus (Istuen)",
    "Deadlift (RDL)": "Maastaveto (RDL)",
    "Deadlift (Straight leg)": "Maastaveto (Suorin jaloin)",
    "Hip abduction": "Lonkan loitonnus",
    "Hip adduction": "Lonkan lähennys",
    "Leg extension": "Reiden ojennus",
    "Squat (Barbell)": "Kyykky (Levytanko)",
    "Squat (Dumbbell)": "Kyykky (Käsipainot)",
    "Squat (Goblet)": "Kyykky (Goblet)",
    "Squat (Belt)": "Kyykky (Vyö)",
    "Squat (Hack)": "Kyykky (Hack)",
    "Squat (Machine)": "Kyykky (laite)",
    "Squat (Safebar)": "Kyykky (Safebar)",
    "Squat (Smith)": "Kyykky (Smith)",
    "Hip thrust (Barbell)": "Lantionnosto",
    "Hip thrust (Machine)": "Lantionnosto (Laite)",
    "Leg press": "Jalkaprässi",
    // SHOULDERS
    "Front raise": "Vipunosto eteen",
    "Overhead press (Arnold)": "Pystypunnerrus (Arnold)",
    "Overhead press (Barbell)": "Pystypunnerrus (Levytanko)",
    "Overhead press (Dumbell)": "Pystypunnerrus (Käsipainot)",
    "Overhead press (Machine)": "Pystypunnerrus (Laite)",
    "Rear delt raise": "Vipunosto taakse",
    "Shrug": "Olankohautus",
    "Side lateral raise": "Vipunosto sivulle",
    // ARMS
    "Bayesian curl": "Bayesian kääntö",
    "Bench press (Narrow)": "Penkkipunnerrus (Kapea)",
    "Bicep curl (Barbell)": "Hauiskääntö (Levytanko)",
    "Bicep curl (Cable)": "Hauiskääntö (Talja)",
    "Bicep curl (Dumbell)": "Hauiskääntö (Käsipainot)",
    "Bicep curl (Machine)": "Hauiskääntö (Laite)",
    "Bicep curl (Preacher)": "Hauiskääntö (Preacher)",
    "Bicep curl (Spider)": "Hauiskääntö (Spider)",
    "Concentration curl": "Keskittynyt hauiskääntö",
    "Dip (Narrow)": "Dippi (Kapea)",
    "Hammer (Dumbell)": "Hammer (Käsipainot)",
    "Hammer (Rope)": "Hammer (Köysi)",
    "Overhead tricep extension": "Ojentajapunnerrus pään yli",
    "Tricep extension (Dumbell)": "Ojentajapunnerrus (Käsipainot)",
    "Tricep extension (Barbell)": "Ojentajapunnerrus (Levytanko)",
    "Tricep extension (Cable)": "Ojentajapunnerrus (Talja)",
    "Tricep pushdown": "Ojentajapunnerrus taljassa",
    "Tricep pushdown (Rope)": "Ojentajapunnerrus taljassa (Köysi)",
    "Push down (Machine)": "Punnerrus taljassa (Laite)",
    // CORE
    "Bicycle crunch": "Polkupyörä vatsalihas",
    "Crunch (Machine)": "Vatsarutistus (laite)",
    "Crunch (Regular)": "Vatsarutistus (Normaali)",
    "Leg raise": "Jalkojen nosto",
    "Reverse crunch": "Käänteinen vatsarutistus",
    "Sit up": "Istumaannousu",
    "Static hold": "Staattinen pito",
    
  }
};
// Function to add dynamic exercises from DB
function addDynamicExercisesToTranslations(dbExercises) {
  dbExercises.forEach(exercise => {
    if (!translations.fi[exercise.name]) {
      translations.fi[exercise.name] = exercise.translation || exercise.name;
    }
  });
}
// current language
let currentLang = localStorage.getItem("lang") || "fi";

// helper
function t(key) {
    // First check exact match
    if (translations[currentLang][key]) {
        return translations[currentLang][key];
    }
    
    // Then check case-insensitive match
    const lowerKey = key.toLowerCase();
    for (const [transKey, transValue] of Object.entries(translations[currentLang])) {
        if (transKey.toLowerCase() === lowerKey) {
            return transValue;
        }
    }
    
    // Finally, return the key itself if no translation found
    return key;
}
// Enhanced apply translations function
function applyTranslations() {
    console.log("Applying translations, current language:", currentLang);
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
 }


document.addEventListener("DOMContentLoaded", applyTranslations);
