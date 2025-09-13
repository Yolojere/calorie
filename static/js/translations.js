// translations.js
const translations = {
  en: {
    home: "Home",
    workouts: "Workouts",
    add_food: "Add Food",
    history: "History",
    activity: "Activity",
    settings: "Settings",
    save_workout: "Save Workout",
    cancel: "Cancel",
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

    // Nutrition
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
    totals: "Yhteenveto",
    no_food_message: "no food logged yet",

    // Days
    monday: "Monday",
    tuesday: "Tuesday",
    wednesday: "Wednesday",
    thursday: "Thursday",
    friday: "Friday",
    saturday: "Saturday",
    sunday: "Sunday",

    grams: "g",

    // Workouts
    add_exercise: "Add Exercise",
    set: "Set",
    sets: "Sets",
    reps: "Reps",
    volume: "Volume",
    delete: "Delete",
    chest: "Chest",
    back: "Back",
    shoulders: "Shoulders",
    arms: "Arms",
    core: "Core",

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
    apply_template: "Apply Template",
    apply_food_template: "Apply food template",
    select_template: "Select template",
    template_name: "Template Name",
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

    // Empty states
    no_workout_message: "No workout recorded for this day. Add your first set below!",
    no_data: "No data available",
    
    // Additional status messages
    action: "Action"
  },
  fi: {
    home: "Koti",
    workouts: "Harjoitukset", 
    add_food: "Lisää Ruoka",
    history: "Historia",
    activity: "Aktiivisuus",
    settings: "Asetukset",
    save_workout: "Tallenna Harjoitus",
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

    // Nutrition
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
    half: "Puoli Pakettia",
    entire: "Koko Paketti",
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

    // Days
    monday: "Maanantai",
    tuesday: "Tiistai",
    wednesday: "Keskiviikko",
    thursday: "Torstai",
    friday: "Perjantai",
    saturday: "Lauantai",
    sunday: "Sunnuntai",

    grams: "g",

    // Workouts
    add_exercise: "Lisää Liike",
    set: "Sarja",
    sets: "Sarjaa",
    reps: "Toistoa",
    volume: "Volyymi",
    delete: "Poista",
    chest: "Rinta",
    back: "Selkä",
    shoulders: "Olkapäät",
    arms: "Kädet",
    core: "Vatsat",

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
    apply_template: "Käytä pohja",
    apply_food_template: "Käytä ruoka pohja",
    select_template: "Valitse pohja",
    template_name: "Pohjan nimi",
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

    // Empty states
    no_workout_message: "Tälle päivälle ei ole tallennettu harjoitusta. Lisää ensimmäinen sarja alla!",
    no_data: "Ei tietoja saatavilla",
    
    // Additional status messages
    action: "Toiminto"
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
    
    // Fix navbar icons
    initializeIcons();
    
    // Update nutrition abbreviations
    updateNutritionAbbreviations();
    
    // Update portion buttons if we have current food
    if (typeof currentFood !== 'undefined' && currentFood) {
        updatePortionButtons(currentFood);
    }
}


document.addEventListener("DOMContentLoaded", applyTranslations);
