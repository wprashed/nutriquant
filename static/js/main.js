// NutriQuant Client-side Controller

document.addEventListener('DOMContentLoaded', () => {
    // Initialise Lucide Icons
    lucide.createIcons();

    // -------------------------------------------------------------
    // Session State Management (Bootstrapped from Server)
    // -------------------------------------------------------------
    let session = {
        isLoggedIn: window.bootstrapSession ? window.bootstrapSession.isLoggedIn : false,
        username: window.bootstrapSession ? window.bootstrapSession.username : null,
        userId: window.bootstrapSession ? window.bootstrapSession.userId : null,
        isAdmin: window.bootstrapSession ? window.bootstrapSession.isAdmin : false
    };

    let weightChartInstance = null;
    let adminChartInstance = null;
    let goalChartInstance = null;
    let activityChartInstance = null;
    let opsChartInstance = null;
    let selectedClientIdForAdmin = null;
    let predefinedFoods = [];
    let foodLoggingMode = 'select'; // 'select' or 'custom'
    let selectedAutocompleteFood = null;
    let currentUserWeight = 70.0;
    let currentDashboardData = null;

    // SaaS Admin Console caching & pagination state
    let allUsersData = [];
    let allPredefinedFoods = [];
    let currentFoodPage = 1;
    const foodItemsPerPage = 10;
    let systemHealthInterval = null;


    // DOM Elements
    const form = document.getElementById('nutrition-form');
    const unitMetric = document.getElementById('unit-metric');
    const unitImperial = document.getElementById('unit-imperial');
    const metricOnlyElems = document.querySelectorAll('.metric-only');
    const imperialOnlyElems = document.querySelectorAll('.imperial-only');

    // Input elements
    const ageInput = document.getElementById('age-input');
    const ageNumber = document.getElementById('age-number');
    const ageVal = document.getElementById('age-val');

    const heightMetric = document.getElementById('height-metric');
    const heightMetricNumber = document.getElementById('height-metric-number');
    const heightFt = document.getElementById('height-ft');
    const heightIn = document.getElementById('height-in');
    const heightDisplay = document.getElementById('height-display');

    const weightMetric = document.getElementById('weight-metric');
    const weightMetricNumber = document.getElementById('weight-metric-number');
    const weightImperial = document.getElementById('weight-imperial');
    const weightImperialNumber = document.getElementById('weight-imperial-number');
    const weightDisplay = document.getElementById('weight-display');
    const autoEstimateWeight = document.getElementById('auto-estimate-weight');

    const activityOptions = document.querySelectorAll('.activity-option');
    const activityInput = document.getElementById('activity-input');

    // Output panel elements
    const outputSection = document.getElementById('output-section');
    const emptyStateView = document.getElementById('empty-state-view');
    const loadingView = document.getElementById('loading-view');
    const dashboardView = document.getElementById('dashboard-view');

    // Output displays
    const valIdealWeight = document.getElementById('val-ideal-weight');
    const valBmr = document.getElementById('val-bmr');
    const valTdee = document.getElementById('val-tdee');
    const valTargetCalories = document.getElementById('val-target-calories');
    const valWater = document.getElementById('val-water');
    const valWaterCups = document.getElementById('val-water-cups');

    const valProteinG = document.getElementById('val-protein-g');
    const valProteinCal = document.getElementById('val-protein-cal');
    const valProteinPct = document.getElementById('val-protein-pct');
    const barProtein = document.getElementById('bar-protein');

    const valCarbsG = document.getElementById('val-carbs-g');
    const valCarbsCal = document.getElementById('val-carbs-cal');
    const valCarbsPct = document.getElementById('val-carbs-pct');
    const barCarbs = document.getElementById('bar-carbs');

    const valFatsG = document.getElementById('val-fats-g');
    const valFatsCal = document.getElementById('val-fats-cal');
    const valFatsPct = document.getElementById('val-fats-pct');
    const barFats = document.getElementById('bar-fats');

    const valFiberG = document.getElementById('val-fiber-g');
    const barFiber = document.getElementById('bar-fiber');

    const calorieProgressCircle = document.getElementById('calorie-progress-circle');
    const waterLiquidFill = document.getElementById('water-liquid-fill');
    const microsContainer = document.getElementById('micros-container');

    // Auth Modal elements
    const authModal = document.getElementById('auth-modal');
    const btnShowAuth = document.getElementById('btn-show-auth');
    const btnCloseAuth = document.getElementById('btn-close-auth');
    const loginSide = document.getElementById('login-side');
    const registerSide = document.getElementById('register-side');
    const linkToRegister = document.getElementById('link-to-register');
    const linkToLogin = document.getElementById('link-to-login');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const userGreeting = document.getElementById('user-greeting');
    const displayUsername = document.getElementById('display-username');
    const btnLogout = document.getElementById('btn-logout');
    const tabHistory = document.getElementById('tab-history');
    const tabAdmin = document.getElementById('tab-admin');
    const tabDashboard = document.getElementById('tab-dashboard');
    const tabCalculator = document.getElementById('tab-calculator');

    // Mobile Bottom Tab Navigation Elements
    const mobileDashboard = document.querySelector('.mobile-nav-tab[data-tab="dashboard"]');
    const mobileCalculator = document.querySelector('.mobile-nav-tab[data-tab="calculator"]');
    const mobileHistory = document.querySelector('.mobile-nav-tab[data-tab="history"]');
    const mobileAdmin = document.getElementById('mobile-tab-admin');

    // User Dashboard DOM Elements
    const userDashboardGreeting = document.getElementById('user-dashboard-greeting');
    const userCalorieRing = document.getElementById('user-calorie-ring');
    const userDashboardCalRemaining = document.getElementById('user-dashboard-cal-remaining');
    const userDashboardCalTarget = document.getElementById('user-dashboard-cal-target');
    const userDashboardCalConsumed = document.getElementById('user-dashboard-cal-consumed');
    
    const userDashProteinProgress = document.getElementById('user-dash-protein-progress');
    const userDashProteinBar = document.getElementById('user-dash-protein-bar');
    const userDashCarbsProgress = document.getElementById('user-dash-carbs-progress');
    const userDashCarbsBar = document.getElementById('user-dash-carbs-bar');
    const userDashFatsProgress = document.getElementById('user-dash-fats-progress');
    const userDashFatsBar = document.getElementById('user-dash-fats-bar');
    
    const userDashWaterTotal = document.getElementById('user-dash-water-total');
    const userDashWaterTarget = document.getElementById('user-dash-water-target');
    const btnQuickAddWater = document.getElementById('btn-quick-add-water');
    
    const userDashFoodForm = document.getElementById('user-dash-food-form');
    const foodLogCalories = document.getElementById('food-log-calories');
    const foodLogProtein = document.getElementById('food-log-protein');
    const foodLogCarbs = document.getElementById('food-log-carbs');
    const foodLogFat = document.getElementById('food-log-fat');
    
    // Daily Exercise Logger Elements
    const userDashExerciseForm = document.getElementById('user-dash-exercise-form');
    const exerciseSelect = document.getElementById('exercise-select');
    const exerciseNameGroup = document.getElementById('exercise-name-group');
    const exerciseNameInput = document.getElementById('exercise-name-input');
    const exerciseDuration = document.getElementById('exercise-duration');
    const exerciseCaloriesGroup = document.getElementById('exercise-calories-group');
    const exerciseCalories = document.getElementById('exercise-calories');
    const exerciseLivePreview = document.getElementById('exercise-live-preview');
    const exercisePreviewCal = document.getElementById('exercise-preview-cal');
    const exerciseJournalTable = document.getElementById('exercise-journal-table');
    const exerciseJournalTbody = document.getElementById('exercise-journal-tbody');
    const exerciseJournalEmptyState = document.getElementById('exercise-journal-empty-state');
    const userDashboardCalBurned = document.getElementById('user-dashboard-cal-burned');
    
    const userDashboardChecklist = document.getElementById('user-dashboard-checklist');
    const userCoachingNotesList = document.getElementById('user-coaching-notes-list');
    
    const dashWeightStart = document.getElementById('dash-weight-start');
    const dashWeightCurrent = document.getElementById('dash-weight-current');
    const dashWeightTarget = document.getElementById('dash-weight-target');
    const userDashWeightProgressBar = document.getElementById('user-dash-weight-progress-bar');
    const userDashWeightGoalText = document.getElementById('user-dash-weight-goal-text');

    // Admin Console Extra Elements (Subtabs, charts, forms)
    const btnAdminSubOverview = document.getElementById('btn-admin-sub-overview');
    const btnAdminSubRegistry = document.getElementById('btn-admin-sub-registry');
    const btnAdminSubFoods = document.getElementById('btn-admin-sub-foods');
    const btnAdminSubSystem = document.getElementById('btn-admin-sub-system');
    const adminPanelOverview = document.getElementById('admin-panel-overview');
    const adminPanelRegistry = document.getElementById('admin-panel-registry');
    const adminPanelFoods = document.getElementById('admin-panel-foods');
    const adminPanelSystem = document.getElementById('admin-panel-system');

    // Admin Stats & Filters Elements
    const adminValActiveWeek = document.getElementById('admin-val-active-week');
    const adminValCheckinsWeek = document.getElementById('admin-val-checkins-week');
    const adminValOnboardingComplete = document.getElementById('admin-val-onboarding-complete');
    const adminValTotalFoods = document.getElementById('admin-val-total-foods');
    const adminValTotalLogs = document.getElementById('admin-val-total-logs');
    
    const adminUserSearch = document.getElementById('admin-user-search');
    const adminUserCoachFilter = document.getElementById('admin-user-coach-filter');
    const adminUserGoalFilter = document.getElementById('admin-user-goal-filter');
    const adminClientCoachingStatus = document.getElementById('admin-client-coaching-status');

    // Predefined Food DB elements
    const adminFoodsTbody = document.getElementById('admin-foods-tbody');
    const adminFoodSearch = document.getElementById('admin-food-search');
    const btnShowAddFoodForm = document.getElementById('btn-show-add-food-form');
    const adminFoodFormContainer = document.getElementById('admin-food-form-container');
    const adminFoodForm = document.getElementById('admin-food-form');
    const adminFoodFormId = document.getElementById('admin-food-form-id');
    const adminFoodFormName = document.getElementById('admin-food-form-name');
    const adminFoodFormCal = document.getElementById('admin-food-form-cal');
    const adminFoodFormPro = document.getElementById('admin-food-form-pro');
    const adminFoodFormCarb = document.getElementById('admin-food-form-carb');
    const adminFoodFormFat = document.getElementById('admin-food-form-fat');
    const btnSaveFood = document.getElementById('btn-save-food');
    const btnSaveFoodText = document.getElementById('btn-save-food-text');
    const btnCancelFood = document.getElementById('btn-cancel-food');
    const adminFoodStatus = document.getElementById('admin-food-status');
    const btnFoodPrev = document.getElementById('btn-food-prev');
    const btnFoodNext = document.getElementById('btn-food-next');
    const foodPageInfo = document.getElementById('food-page-info');

    // System Monitor & Audit Logs elements
    const adminLogsTbody = document.getElementById('admin-logs-tbody');
    const systemValCpu = document.getElementById('system-val-cpu');
    const systemValMem = document.getElementById('system-val-mem');
    const systemValDb = document.getElementById('system-val-db');
    const systemValLatency = document.getElementById('system-val-latency');
    const systemBarCpu = document.getElementById('system-bar-cpu');
    const systemBarMem = document.getElementById('system-bar-mem');
    const systemBarDb = document.getElementById('system-bar-db');
    const systemBarLatency = document.getElementById('system-bar-latency');
    const cpuHealthDot = document.getElementById('cpu-health-dot');
    const memHealthDot = document.getElementById('mem-health-dot');
    const dbHealthDot = document.getElementById('db-health-dot');
    const latencyHealthDot = document.getElementById('latency-health-dot');
    
    const adminAnnouncementForm = document.getElementById('admin-announcement-form');
    const adminAnnouncementMsg = document.getElementById('admin-announcement-msg');
    const adminAnnouncementStatus = document.getElementById('admin-announcement-status');
    
    const adminOverrideForm = document.getElementById('admin-override-form');
    const overrideCal = document.getElementById('override-cal');
    const overridePro = document.getElementById('override-pro');
    const overrideCarb = document.getElementById('override-carb');
    const overrideFat = document.getElementById('override-fat');
    const btnClearOverride = document.getElementById('btn-clear-override');
    const adminOverrideStatus = document.getElementById('admin-override-status');
    
    const adminMessageForm = document.getElementById('admin-message-form');
    const adminClientMsg = document.getElementById('admin-client-msg');
    const adminMessageStatus = document.getElementById('admin-message-status');

    // Weight Tracker Elements
    const logWeightMetric = document.getElementById('log-weight-metric');
    const logWeightMetricNumber = document.getElementById('log-weight-metric-number');
    const logWeightImperial = document.getElementById('log-weight-imperial');
    const logWeightImperialNumber = document.getElementById('log-weight-imperial-number');
    const logWeightDisplay = document.getElementById('log-weight-display');
    const logDateInput = document.getElementById('log-date');
    const weightLogForm = document.getElementById('weight-log-form');
    const weightLogsTbody = document.getElementById('weight-logs-tbody');

    // Admin Console Elements
    const adminValTotalUsers = document.getElementById('admin-val-total-users');
    const adminValAvgAge = document.getElementById('admin-val-avg-age');
    const adminValAvgWeight = document.getElementById('admin-val-avg-weight');
    const adminUsersTbody = document.getElementById('admin-users-tbody');
    const adminUserDetailsPanel = document.getElementById('admin-user-details-panel');
    const adminDetailsEmptyState = document.getElementById('admin-details-empty-state');
    const adminDetailsDisplay = document.getElementById('admin-details-display');
    const adminDisplayClientName = document.getElementById('admin-display-client-name');
    const adminDisplayJoinDate = document.getElementById('admin-display-join-date');
    const btnAdminDeleteUser = document.getElementById('btn-admin-delete-user');
    const adminClientAge = document.getElementById('admin-client-age');
    const adminClientHeight = document.getElementById('admin-client-height');
    const adminClientWeight = document.getElementById('admin-client-weight');
    const adminClientGoal = document.getElementById('admin-client-goal');
    const adminClientTargetCalories = document.getElementById('admin-client-target-calories');
    const adminClientActivity = document.getElementById('admin-client-activity');
    const adminClientProtein = document.getElementById('admin-client-protein');
    const adminClientCarbs = document.getElementById('admin-client-carbs');
    const adminClientFats = document.getElementById('admin-client-fats');

    // -------------------------------------------------------------
    // Unit Toggling Handler
    // -------------------------------------------------------------
    function updateUnitSystem() {
        const isMetric = unitMetric.checked;

        if (isMetric) {
            metricOnlyElems.forEach(el => el.classList.remove('hidden'));
            imperialOnlyElems.forEach(el => el.classList.add('hidden'));
            
            if (!autoEstimateWeight.checked) {
                weightDisplay.textContent = `${weightMetric.value} kg`;
            }
            logWeightDisplay.textContent = `${logWeightMetric.value} kg`;
            updateHeightDisplay();
        } else {
            metricOnlyElems.forEach(el => el.classList.add('hidden'));
            imperialOnlyElems.forEach(el => el.classList.remove('hidden'));
            
            if (!autoEstimateWeight.checked) {
                weightDisplay.textContent = `${weightImperial.value} lbs`;
            }
            logWeightDisplay.textContent = `${logWeightImperial.value} lbs`;
            updateHeightDisplay();
        }
    }

    unitMetric.addEventListener('change', updateUnitSystem);
    unitImperial.addEventListener('change', updateUnitSystem);

    // -------------------------------------------------------------
    // Input Syncing & Display Updates
    // -------------------------------------------------------------
    // Age Sync
    function syncAge(val) {
        ageInput.value = val;
        ageNumber.value = val;
        ageVal.textContent = val;
    }
    ageInput.addEventListener('input', (e) => syncAge(e.target.value));
    ageNumber.addEventListener('change', (e) => {
        let val = parseInt(e.target.value);
        if (isNaN(val)) val = 25;
        val = Math.max(1, Math.min(120, val));
        syncAge(val);
    });

    // Height Sync
    function updateHeightDisplay() {
        if (unitMetric.checked) {
            heightDisplay.textContent = `${heightMetric.value} cm`;
        } else {
            const ft = parseInt(heightFt.value) || 5;
            const inch = parseInt(heightIn.value) || 0;
            heightDisplay.textContent = `${ft} ft ${inch} in`;
        }
    }

    heightMetric.addEventListener('input', (e) => {
        heightMetricNumber.value = e.target.value;
        updateHeightDisplay();
    });
    heightMetricNumber.addEventListener('change', (e) => {
        let val = parseInt(e.target.value);
        if (isNaN(val)) val = 170;
        val = Math.max(50, Math.min(230, val));
        heightMetric.value = val;
        heightMetricNumber.value = val;
        updateHeightDisplay();
    });

    heightFt.addEventListener('change', () => {
        let val = parseInt(heightFt.value);
        if (isNaN(val)) val = 5;
        heightFt.value = Math.max(1, Math.min(8, val));
        updateHeightDisplay();
    });
    heightIn.addEventListener('change', () => {
        let val = parseInt(heightIn.value);
        if (isNaN(val)) val = 0;
        heightIn.value = Math.max(0, Math.min(11, val));
        updateHeightDisplay();
    });

    // Weight Sync (Calculator Form)
    function syncWeightMetric(val) {
        weightMetric.value = val;
        weightMetricNumber.value = val;
        if (unitMetric.checked) {
            weightDisplay.textContent = `${val} kg`;
        }
        logWeightMetric.value = val;
        logWeightMetricNumber.value = val;
    }
    weightMetric.addEventListener('input', (e) => syncWeightMetric(e.target.value));
    weightMetricNumber.addEventListener('change', (e) => {
        let val = parseInt(e.target.value);
        if (isNaN(val)) val = 70;
        val = Math.max(10, Math.min(250, val));
        syncWeightMetric(val);
    });

    function syncWeightImperial(val) {
        weightImperial.value = val;
        weightImperialNumber.value = val;
        if (!unitMetric.checked) {
            weightDisplay.textContent = `${val} lbs`;
        }
        logWeightImperial.value = val;
        logWeightImperialNumber.value = val;
    }
    weightImperial.addEventListener('input', (e) => syncWeightImperial(e.target.value));
    weightImperialNumber.addEventListener('change', (e) => {
        let val = parseInt(e.target.value);
        if (isNaN(val)) val = 154;
        val = Math.max(20, Math.min(550, val));
        syncWeightImperial(val);
    });

    // Weight Sync (Weight Logger)
    function syncLogWeightMetric(val) {
        logWeightMetric.value = val;
        logWeightMetricNumber.value = val;
        if (unitMetric.checked) {
            logWeightDisplay.textContent = `${val} kg`;
        }
    }
    logWeightMetric.addEventListener('input', (e) => syncLogWeightMetric(e.target.value));
    logWeightMetricNumber.addEventListener('change', (e) => {
        let val = parseInt(e.target.value);
        if (isNaN(val)) val = 70;
        val = Math.max(10, Math.min(250, val));
        syncLogWeightMetric(val);
    });

    function syncLogWeightImperial(val) {
        logWeightImperial.value = val;
        logWeightImperialNumber.value = val;
        if (!unitMetric.checked) {
            logWeightDisplay.textContent = `${val} lbs`;
        }
    }
    logWeightImperial.addEventListener('input', (e) => syncLogWeightImperial(e.target.value));
    logWeightImperialNumber.addEventListener('change', (e) => {
        let val = parseInt(e.target.value);
        if (isNaN(val)) val = 154;
        val = Math.max(20, Math.min(550, val));
        syncLogWeightImperial(val);
    });

    // Auto Estimate Weight Checkbox
    autoEstimateWeight.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        const metricWeightInputs = document.querySelector('.weight-input-row.metric-only');
        const imperialWeightInputs = document.querySelector('.weight-input-row.imperial-only');

        if (isChecked) {
            weightDisplay.textContent = "Auto-Estimated";
            if (metricWeightInputs) metricWeightInputs.classList.add('hidden');
            if (imperialWeightInputs) imperialWeightInputs.classList.add('hidden');
        } else {
            if (metricWeightInputs) metricWeightInputs.classList.toggle('hidden', !unitMetric.checked);
            if (imperialWeightInputs) imperialWeightInputs.classList.toggle('hidden', unitMetric.checked);
            
            if (unitMetric.checked) {
                weightDisplay.textContent = `${weightMetric.value} kg`;
            } else {
                weightDisplay.textContent = `${weightImperial.value} lbs`;
            }
        }
    });

    // Wire up gender card triggers
    const genderCards = document.querySelectorAll('.gender-card');
    genderCards.forEach(card => {
        const input = card.querySelector('input');
        card.addEventListener('click', (e) => {
            if (e.target.tagName === 'INPUT') return;
            genderCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            input.checked = true;
        });
    });

    // Activity Card Selector
    activityOptions.forEach(option => {
        option.addEventListener('click', () => {
            activityOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
            activityInput.value = option.dataset.value;
        });
    });

    if (logDateInput) {
        logDateInput.valueAsDate = new Date();
    }

    // -------------------------------------------------------------
    // Tab Switching Routing Logic
    // -------------------------------------------------------------
    const tabs = document.querySelectorAll('.nav-tab');
    const panels = document.querySelectorAll('.tab-content-panel');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            if (tab.classList.contains('hidden')) return;
            tabs.forEach(t => t.classList.remove('active'));
            panels.forEach(p => {
                p.classList.remove('active');
                p.classList.add('hidden');
            });
            
            tab.classList.add('active');

            // Sync mobile bottom tab active classes
            const mobTabs = document.querySelectorAll('.mobile-nav-tab');
            mobTabs.forEach(m => {
                if (m.dataset.tab === tab.dataset.tab) {
                    m.classList.add('active');
                } else {
                    m.classList.remove('active');
                }
            });
            const targetPanel = document.getElementById(`panel-${tab.dataset.tab}`);
            if (targetPanel) {
                targetPanel.classList.add('active');
                targetPanel.classList.remove('hidden');
            }

            // Route action callbacks
            if (tab.dataset.tab === 'dashboard') {
                loadUserDashboard();
            } else if (tab.dataset.tab === 'history') {
                fetchWeightHistory();
            } else if (tab.dataset.tab === 'admin') {
                loadAdminDashboard();
            } else if (tab.dataset.tab === 'calculator') {
                if (session.isLoggedIn && !session.isAdmin) {
                    fetchAndFillProfile();
                }
            }
            updateFABVisibility();
        });
    });

    // Mobile Bottom Tab Click Handler
    const mobileTabs = document.querySelectorAll('.mobile-nav-tab');
    mobileTabs.forEach(mobTab => {
        mobTab.addEventListener('click', () => {
            const correspondingTopTab = document.querySelector(`.nav-tab[data-tab="${mobTab.dataset.tab}"]`);
            if (correspondingTopTab) {
                correspondingTopTab.click();
            }
        });
    });

    document.querySelectorAll('.modern-app-intro [data-tab], .dashboard-hero [data-tab]').forEach(action => {
        action.addEventListener('click', () => {
            const targetTab = document.querySelector(`.nav-tab[data-tab="${action.dataset.tab}"]`);
            if (targetTab && !targetTab.classList.contains('hidden')) targetTab.click();
        });
    });

    const btnIntroSignin = document.getElementById('btn-intro-signin');
    if (btnIntroSignin) {
        btnIntroSignin.addEventListener('click', openAuthModal);
    }

    const btnHeroMealPlan = document.getElementById('btn-hero-meal-plan');
    if (btnHeroMealPlan) {
        btnHeroMealPlan.addEventListener('click', () => {
            const dashboardTab = document.getElementById('tab-dashboard');
            if (dashboardTab) dashboardTab.click();
            const planButton = document.getElementById('btn-generate-meal-plan');
            if (planButton) planButton.click();
        });
    }

    // Consolidated Quick-Logger tabs handler
    const quickLogTabBtns = document.querySelectorAll('.quick-log-tab-btn');
    const quickLogPanels = document.querySelectorAll('.quick-log-panel');
    quickLogTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            quickLogTabBtns.forEach(b => b.classList.remove('active'));
            quickLogPanels.forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            const targetPanel = document.getElementById(`panel-log-${btn.dataset.logTab}`);
            if (targetPanel) {
                targetPanel.classList.add('active');
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }
        });
    });

    // Consolidated Activity Journal tabs handler
    const journalTabBtns = document.querySelectorAll('.journals-tab-btn');
    const journalPanels = document.querySelectorAll('.journal-panel');
    journalTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            journalTabBtns.forEach(b => b.classList.remove('active'));
            journalPanels.forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            const targetPanel = document.getElementById(`panel-journal-${btn.dataset.journalTab}`);
            if (targetPanel) {
                targetPanel.classList.add('active');
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }
        });
    });

    // -------------------------------------------------------------
    // Auth Modal Overlay Triggering
    // -------------------------------------------------------------
    function openAuthModal() {
        authModal.classList.remove('hidden');
        loginSide.classList.remove('hidden');
        registerSide.classList.add('hidden');
        document.getElementById('login-error').classList.add('hidden');
        document.getElementById('register-error').classList.add('hidden');
        loginForm.reset();
        registerForm.reset();
    }

    function closeAuthModal() {
        authModal.classList.add('hidden');
    }

    btnShowAuth.addEventListener('click', openAuthModal);
    btnCloseAuth.addEventListener('click', closeAuthModal);

    linkToRegister.addEventListener('click', (e) => {
        e.preventDefault();
        loginSide.classList.add('hidden');
        registerSide.classList.remove('hidden');
    });

    linkToLogin.addEventListener('click', (e) => {
        e.preventDefault();
        registerSide.classList.add('hidden');
        loginSide.classList.remove('hidden');
    });

    authModal.addEventListener('click', (e) => {
        if (e.target === authModal) {
            closeAuthModal();
        }
    });

    // -------------------------------------------------------------
    // Session State Rendering
    // -------------------------------------------------------------
    function applyRoleVisibility() {
        document.body.classList.toggle('is-guest', !session.isLoggedIn);
        document.body.classList.toggle('is-client', session.isLoggedIn && !session.isAdmin);
        document.body.classList.toggle('is-admin', session.isLoggedIn && session.isAdmin);
    }

    function updateFABVisibility() {
        const fabWrapper = document.getElementById('fab-wrapper');
        if (!fabWrapper) return;
        const activeTab = document.querySelector('.nav-tab.active');
        const activeTabName = activeTab ? activeTab.dataset.tab : '';
        if (session.isAdmin || activeTabName === 'admin') {
            fabWrapper.classList.add('hidden');
        } else {
            fabWrapper.classList.remove('hidden');
        }
    }

    function updateSessionUI() {
        applyRoleVisibility();
        updateFABVisibility();
        if (session.isLoggedIn) {
            btnShowAuth.classList.add('hidden');
            userGreeting.classList.remove('hidden');
            displayUsername.textContent = session.username;
            
            // Update settings avatar details
            const settingsAvatarInitials = document.getElementById('settings-avatar-initials');
            const settingsProfileUsername = document.getElementById('settings-profile-username');
            if (settingsAvatarInitials && settingsProfileUsername && session.username) {
                settingsAvatarInitials.textContent = session.username.charAt(0).toUpperCase();
                settingsProfileUsername.textContent = session.username;
            }
            
            // Role separation tabs
            if (session.isAdmin) {
                tabAdmin.classList.remove('hidden');
                tabDashboard.classList.add('hidden');
                tabHistory.classList.add('hidden');
                tabCalculator.classList.add('hidden');

                if (mobileAdmin) mobileAdmin.classList.remove('hidden');
                if (mobileDashboard) mobileDashboard.classList.add('hidden');
                if (mobileHistory) mobileHistory.classList.add('hidden');
                if (mobileCalculator) mobileCalculator.classList.add('hidden');

                const accountSettingsForm = document.getElementById('account-settings-form');
                if (accountSettingsForm) accountSettingsForm.classList.add('hidden');
            } else {
                tabDashboard.classList.remove('hidden');
                tabHistory.classList.remove('hidden');
                tabCalculator.classList.remove('hidden');
                tabAdmin.classList.add('hidden');

                if (mobileDashboard) mobileDashboard.classList.remove('hidden');
                if (mobileHistory) mobileHistory.classList.remove('hidden');
                if (mobileCalculator) mobileCalculator.classList.remove('hidden');
                if (mobileAdmin) mobileAdmin.classList.add('hidden');

                const accountSettingsForm = document.getElementById('account-settings-form');
                if (accountSettingsForm) accountSettingsForm.classList.remove('hidden');
            }
        } else {
            btnShowAuth.classList.remove('hidden');
            userGreeting.classList.add('hidden');
            tabDashboard.classList.add('hidden');
            tabHistory.classList.add('hidden');
            tabAdmin.classList.add('hidden');
            tabCalculator.classList.remove('hidden');

            if (mobileDashboard) mobileDashboard.classList.add('hidden');
            if (mobileHistory) mobileHistory.classList.add('hidden');
            if (mobileAdmin) mobileAdmin.classList.add('hidden');
            if (mobileCalculator) mobileCalculator.classList.remove('hidden');
            
            // Reset settings avatar details
            const settingsAvatarInitials = document.getElementById('settings-avatar-initials');
            const settingsProfileUsername = document.getElementById('settings-profile-username');
            if (settingsAvatarInitials && settingsProfileUsername) {
                settingsAvatarInitials.textContent = "U";
                settingsProfileUsername.textContent = "User Profile";
            }
            
            const accountSettingsForm = document.getElementById('account-settings-form');
            if (accountSettingsForm) accountSettingsForm.classList.add('hidden');

            // Reset to Calculator view
            document.getElementById('tab-calculator').click();
        }
    }

    updateSessionUI();
    if (session.isLoggedIn) {
        if (session.isAdmin) {
            document.getElementById('tab-admin').click();
        } else {
            document.getElementById('tab-dashboard').click();
            fetchAndFillProfile();
        }
    }

    function updatePlanUI(user = {}) {
        const workflowBadge = document.getElementById('workflow-status-badge');
        const planManageHint = document.getElementById('user-plan-manage-hint');

        if (workflowBadge) {
            const completed = Boolean(user.onboarding_completed);
            workflowBadge.textContent = completed ? 'onboarded' : 'setup';
            workflowBadge.className = `tier-badge ${completed ? 'tier-premium' : 'tier-free'}`;
        }
        if (planManageHint) {
            planManageHint.textContent = session.isLoggedIn
                ? "Your setup connects directly to dashboard logging, meal planning, progress trends, and coach check-ins."
                : "Create an account to save targets and unlock client tracking workflows.";
        }
    }

    function fillOnboardingForm(user = {}) {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el && val !== undefined && val !== null) el.value = Array.isArray(val) ? val.join(', ') : val;
        };
        setVal('onboarding-dietary-style', user.dietary_style || 'balanced');
        setVal('onboarding-cuisine', user.region_cuisine || 'global');
        setVal('onboarding-schedule', user.meal_schedule || 'standard');
        setVal('onboarding-coaching-level', user.coaching_level || 'self_guided');
        setVal('onboarding-allergies', user.allergies || []);
        const badge = document.getElementById('onboarding-status-badge');
        if (badge) badge.textContent = user.onboarding_completed ? 'complete' : 'setup';
    }

    // -------------------------------------------------------------
    // Fetch Profile Details & Auto-Fill
    // -------------------------------------------------------------
    function fetchAndFillProfile() {
        fetch('/api/profile')
        .then(response => {
            if (!response.ok) throw new Error("Could not load profile");
            return response.json();
        })
        .then(data => {
            const user = data.user;
            if (user.is_admin) return; // Admins don't have biometrics profiles to fill
            updatePlanUI(user);
            fillOnboardingForm(user);

            const accountFullname = document.getElementById('account-fullname');
            const accountEmail = document.getElementById('account-email');
            const accountPassword = document.getElementById('account-password');
            if (accountFullname) accountFullname.value = user.full_name || '';
            if (accountEmail) accountEmail.value = user.email || '';
            if (accountPassword) accountPassword.value = '';

            if (!user.age) return;

            // Sync inputs
            syncAge(user.age);

            heightMetric.value = user.height_cm;
            heightMetricNumber.value = user.height_cm;
            const ft = Math.floor((user.height_cm / 2.54) / 12);
            const inch = Math.round((user.height_cm / 2.54) % 12);
            heightFt.value = ft;
            heightIn.value = inch;
            updateHeightDisplay();

            syncWeightMetric(user.weight_kg);
            const lbs = Math.round(user.weight_kg * 2.20462);
            syncWeightImperial(lbs);
            autoEstimateWeight.checked = false;

            genderCards.forEach(card => {
                const input = card.querySelector('input');
                const match = input.value === user.gender;
                card.classList.toggle('active', match);
                if (match) input.checked = true;
            });

            activityOptions.forEach(opt => {
                const match = opt.dataset.value === user.activity;
                opt.classList.toggle('active', match);
                if (match) activityInput.value = user.activity;
            });

            document.getElementById('goal-select').value = user.goal;

            updateUnitSystem();

            // Run calculation immediately
            form.requestSubmit();
        })
        .catch(err => console.log(err.message));
    }

    // -------------------------------------------------------------
    // Authentication Submissions
    // -------------------------------------------------------------
    registerForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const errorBanner = document.getElementById('register-error');

        errorBanner.classList.add('hidden');

        fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Registration failed") });
            }
            return response.json();
        })
        .then(data => {
            session.isLoggedIn = true;
            session.username = data.user.username;
            session.userId = data.user.id;
            session.isAdmin = false;
            
            updateSessionUI();
            updatePlanUI(data.user);
            closeAuthModal();
            form.requestSubmit();
        })
        .catch(err => {
            errorBanner.textContent = err.message;
            errorBanner.classList.remove('hidden');
        });
    });

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorBanner = document.getElementById('login-error');

        errorBanner.classList.add('hidden');

        fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Login failed") });
            }
            return response.json();
        })
        .then(data => {
            session.isLoggedIn = true;
            session.username = data.user.username;
            session.userId = data.user.id;
            session.isAdmin = data.user.is_admin;
            
            updateSessionUI();
            updatePlanUI(data.user);
            closeAuthModal();
            
            if (session.isAdmin) {
                document.getElementById('tab-admin').click();
            } else {
                document.getElementById('tab-dashboard').click();
                fetchAndFillProfile();
            }
        })
        .catch(err => {
            errorBanner.textContent = err.message;
            errorBanner.classList.remove('hidden');
        });
    });

    btnLogout.addEventListener('click', () => {
        fetch('/api/auth/logout', { method: 'POST' })
        .then(() => {
            session.isLoggedIn = false;
            session.username = null;
            session.userId = null;
            session.isAdmin = false;
            
            stopSystemHealth();
            updateSessionUI();
            
            form.reset();
            syncAge(25);
            heightMetric.value = 170;
            heightMetricNumber.value = 170;
            syncWeightMetric(70);
            updateHeightDisplay();
            updateUnitSystem();
            autoEstimateWeight.checked = false;
            updatePlanUI();
            
            emptyStateView.classList.remove('hidden');
            dashboardView.classList.add('hidden');
            loadingView.classList.add('hidden');
        });
    });

    const onboardingForm = document.getElementById('onboarding-form');
    if (onboardingForm) {
        onboardingForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const status = document.getElementById('onboarding-status');
            const payload = {
                dietary_style: document.getElementById('onboarding-dietary-style').value,
                region_cuisine: document.getElementById('onboarding-cuisine').value,
                meal_schedule: document.getElementById('onboarding-schedule').value,
                coaching_level: document.getElementById('onboarding-coaching-level').value,
                allergies: document.getElementById('onboarding-allergies').value
                    .split(',')
                    .map(item => item.trim())
                    .filter(Boolean)
            };
            if (status) status.className = 'status-banner hidden';

            fetch('/api/onboarding', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => {
                if (!res.ok) return res.json().then(err => { throw new Error(err.error || 'Failed to save onboarding.'); });
                return res.json();
            })
            .then(data => {
                fillOnboardingForm(data.user);
                if (status) {
                    status.textContent = 'Onboarding saved. Dashboard is ready.';
                    status.className = 'status-banner success';
                }
                if (session.isLoggedIn && !session.isAdmin) {
                    document.getElementById('tab-dashboard').click();
                }
            })
            .catch(err => {
                if (status) {
                    status.textContent = err.message;
                    status.className = 'status-banner error';
                }
            });
        });
    }

    const accountSettingsForm = document.getElementById('account-settings-form');
    if (accountSettingsForm) {
        accountSettingsForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const fullName = document.getElementById('account-fullname').value;
            const email = document.getElementById('account-email').value;
            const password = document.getElementById('account-password').value;
            const statusBanner = document.getElementById('account-settings-status');

            statusBanner.classList.add('hidden');
            statusBanner.classList.remove('success', 'error');

            fetch('/api/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    password: password
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    statusBanner.textContent = data.error;
                    statusBanner.style.background = 'rgba(239, 68, 68, 0.1)';
                    statusBanner.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                    statusBanner.style.color = '#ef4444';
                    statusBanner.classList.remove('hidden');
                } else {
                    statusBanner.textContent = "Account details saved successfully!";
                    statusBanner.style.background = 'rgba(16, 185, 129, 0.1)';
                    statusBanner.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                    statusBanner.style.color = '#10b981';
                    statusBanner.classList.remove('hidden');
                    
                    document.getElementById('account-password').value = '';
                    
                    if (data.user && data.user.full_name) {
                        const settingsProfileUsername = document.getElementById('settings-profile-username');
                        if (settingsProfileUsername) {
                            settingsProfileUsername.textContent = data.user.full_name;
                        }
                    }
                }
            })
            .catch(err => {
                statusBanner.textContent = "An error occurred. Please try again.";
                statusBanner.style.background = 'rgba(239, 68, 68, 0.1)';
                statusBanner.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                statusBanner.style.color = '#ef4444';
                statusBanner.classList.remove('hidden');
            });
        });
    }

    // -------------------------------------------------------------
    // Nutrition Calculator Submission
    // -------------------------------------------------------------
    form.addEventListener('submit', (e) => {
        e.preventDefault();

        let heightCm = 170;
        if (unitMetric.checked) {
            heightCm = parseFloat(heightMetric.value);
        } else {
            const ft = parseInt(heightFt.value) || 5;
            const inch = parseInt(heightIn.value) || 0;
            heightCm = (ft * 12 + inch) * 2.54;
        }

        let weightKg = 70;
        const autoEstimate = autoEstimateWeight.checked;
        if (autoEstimate) {
            weightKg = 22.0 * ((heightCm / 100.0) ** 2);
        } else {
            if (unitMetric.checked) {
                weightKg = parseFloat(weightMetric.value);
            } else {
                const weightLbs = parseFloat(weightImperial.value);
                weightKg = weightLbs * 0.45359237;
            }
        }

        const age = parseInt(ageInput.value);
        const gender = document.querySelector('input[name="gender"]:checked').value;
        const activity = activityInput.value;
        const goal = document.getElementById('goal-select').value;

        emptyStateView.classList.add('hidden');
        dashboardView.classList.add('hidden');
        loadingView.classList.remove('hidden');

        if (window.innerWidth < 960) {
            outputSection.scrollIntoView({ behavior: 'smooth' });
        }

        const doCalculate = () => {
            fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    age: age,
                    height_cm: heightCm,
                    weight_kg: weightKg,
                    gender: gender,
                    activity: activity,
                    goal: goal
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || "Calculation failed") });
                }
                return response.json();
            })
            .then(data => {
                loadingView.classList.add('hidden');
                dashboardView.classList.remove('hidden');
                renderDashboard(data);
            })
            .catch(err => {
                loadingView.classList.add('hidden');
                emptyStateView.classList.remove('hidden');
                alert(err.message || "An error occurred during calculation.");
            });
        };

        doCalculate();
    });

    function renderDashboard(data) {
        const isMetric = unitMetric.checked;

        const idealKg = data.ideal_weight_kg;
        if (isMetric) {
            valIdealWeight.textContent = `${idealKg} kg`;
        } else {
            const idealLbs = Math.round(idealKg * 2.20462);
            valIdealWeight.textContent = `${idealKg} kg (${idealLbs} lbs)`;
        }

        valBmr.textContent = `${formatNumber(data.bmr)} kcal`;
        valTdee.textContent = `${formatNumber(data.tdee)} kcal`;
        valTargetCalories.textContent = formatNumber(data.target_calories);

        valWater.textContent = `${data.water_l} L`;
        const cupsVal = Math.round(data.water_l * 4.22675 * 10) / 10;
        valWaterCups.textContent = `~${cupsVal} cups`;

        const maxWaterVisual = 4.0;
        const fillPercent = Math.min((data.water_l / maxWaterVisual) * 100, 100);
        setTimeout(() => {
            waterLiquidFill.style.height = `${fillPercent}%`;
        }, 100);

        setTimeout(() => {
            calorieProgressCircle.style.strokeDashoffset = '0';
        }, 200);

        valProteinG.textContent = `${data.macros.protein.grams}g`;
        valProteinCal.textContent = `${data.macros.protein.calories} kcal`;
        valProteinPct.textContent = `${data.macros.protein.percentage}%`;
        setTimeout(() => {
            barProtein.style.width = `${data.macros.protein.percentage}%`;
        }, 300);

        valCarbsG.textContent = `${data.macros.carbs.grams}g`;
        valCarbsCal.textContent = `${data.macros.carbs.calories} kcal`;
        valCarbsPct.textContent = `${data.macros.carbs.percentage}%`;
        setTimeout(() => {
            barCarbs.style.width = `${data.macros.carbs.percentage}%`;
        }, 450);

        valFatsG.textContent = `${data.macros.fat.grams}g`;
        valFatsCal.textContent = `${data.macros.fat.calories} kcal`;
        valFatsPct.textContent = `${data.macros.fat.percentage}%`;
        setTimeout(() => {
            barFats.style.width = `${data.macros.fat.percentage}%`;
        }, 600);

        valFiberG.textContent = `${data.fiber_g}g`;
        const fiberPercent = Math.min((data.fiber_g / 40) * 100, 100);
        setTimeout(() => {
            barFiber.style.width = `${fiberPercent}%`;
        }, 700);

        microsContainer.innerHTML = '';
        const micros = data.micronutrients;

        Object.keys(micros).forEach(key => {
            const nutrient = micros[key];
            const iconName = getMicronutrientIcon(key);
            
            const sourcePills = nutrient.sources.split(', ')
                .map(source => `<span class="source-pill">${source}</span>`)
                .join('');

            const cardHtml = `
                <div class="micro-card">
                    <div class="micro-header">
                        <div class="micro-title-group-left">
                            <div class="micro-icon-container">
                                <i data-lucide="${iconName}"></i>
                            </div>
                            <span class="micro-name-label">${key}</span>
                        </div>
                        <span class="micro-value-badge">${nutrient.value} ${nutrient.unit}</span>
                    </div>
                    <p class="micro-desc">${nutrient.desc}</p>
                    <div class="micro-sources-group">
                        ${sourcePills}
                    </div>
                </div>
            `;
            microsContainer.insertAdjacentHTML('beforeend', cardHtml);
        });

        lucide.createIcons();
    }

    // -------------------------------------------------------------
    // Weight Tracker Submission & Fetching (Client Dashboard)
    // -------------------------------------------------------------
    function fetchWeightHistory() {
        fetch('/api/weight/history')
        .then(response => {
            if (!response.ok) throw new Error("Could not fetch weight history");
            return response.json();
        })
        .then(data => {
            renderWeightTracker(data.history);
        })
        .catch(err => console.log(err.message));
    }

    weightLogForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        let weightKg = 70;
        if (unitMetric.checked) {
            weightKg = parseFloat(logWeightMetric.value);
        } else {
            const lbs = parseFloat(logWeightImperial.value);
            weightKg = lbs * 0.45359237;
        }

        const dateStr = logDateInput.value;
        const errorBanner = document.getElementById('log-weight-error');
        errorBanner.classList.add('hidden');

        fetch('/api/weight/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weight_kg: weightKg, date_str: dateStr })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Logging failed") });
            }
            return response.json();
        })
        .then(data => {
            renderWeightTracker(data.history);
            syncWeightMetric(Math.round(weightKg));
            const lbs = Math.round(weightKg * 2.20462);
            syncWeightImperial(lbs);
            updateUnitSystem();
        })
        .catch(err => {
            errorBanner.textContent = err.message;
            errorBanner.classList.remove('hidden');
        });
    });

    function renderWeightTracker(history) {
        const isMetric = unitMetric.checked;
        weightLogsTbody.innerHTML = '';
        
        const sortedHistory = [...history].reverse();
        sortedHistory.forEach(log => {
            let weightDisplay = `${log.weight_kg} kg`;
            if (!isMetric) {
                weightDisplay = `${Math.round(log.weight_kg * 2.20462)} lbs`;
            }

            const row = `
                <tr>
                    <td data-label="Date">${log.logged_at}</td>
                    <td data-label="Weight"><strong>${weightDisplay}</strong></td>
                    <td data-label="Actions" style="text-align: right;">
                        <button class="btn-delete-log" data-date="${log.logged_at}" title="Load weight logs">
                            <i data-lucide="edit-3"></i>
                        </button>
                    </td>
                </tr>
            `;
            weightLogsTbody.insertAdjacentHTML('beforeend', row);
        });

        lucide.createIcons();

        const editBtns = document.querySelectorAll('.btn-delete-log');
        editBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                logDateInput.value = btn.dataset.date;
                const found = history.find(h => h.logged_at === btn.dataset.date);
                if (found) {
                    syncLogWeightMetric(Math.round(found.weight_kg));
                    syncLogWeightImperial(Math.round(found.weight_kg * 2.20462));
                    updateUnitSystem();
                }
            });
        });

        renderWeightChart(history);
    }

    function renderWeightChart(history) {
        const ctx = document.getElementById('weightHistoryChart').getContext('2d');
        const isMetric = unitMetric.checked;
        
        const labels = history.map(h => h.logged_at);
        const data = history.map(h => {
            return isMetric ? h.weight_kg : Math.round(h.weight_kg * 2.20462);
        });

        if (weightChartInstance) {
            weightChartInstance.data.labels = labels;
            weightChartInstance.data.datasets[0].data = data;
            weightChartInstance.data.datasets[0].label = isMetric ? 'Weight (kg)' : 'Weight (lbs)';
            weightChartInstance.update();
            return;
        }

        weightChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: isMetric ? 'Weight (kg)' : 'Weight (lbs)',
                    data: data,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.08)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#22d3ee',
                    pointBorderColor: '#070a12',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 22, 38, 0.95)',
                        titleFont: { family: 'Outfit', size: 13 },
                        bodyFont: { family: 'Inter', size: 12 },
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                    }
                }
            }
        });
    }

    // -------------------------------------------------------------
    // -------------------------------------------------------------
    // B2B Admin Console Controller
    // -------------------------------------------------------------
    
    // Wire Admin subtab controls
    const adminSubtabs = [
        { btn: btnAdminSubOverview, panel: adminPanelOverview, onShow: () => { stopSystemHealth(); fetchAdminStats(); } },
        { btn: btnAdminSubRegistry, panel: adminPanelRegistry, onShow: () => { stopSystemHealth(); fetchAdminUsers(); } },
        { btn: btnAdminSubFoods, panel: adminPanelFoods, onShow: () => { stopSystemHealth(); fetchAdminFoods(); } },
        { btn: btnAdminSubSystem, panel: adminPanelSystem, onShow: () => { fetchAdminAuditLogs(); startSystemHealthMonitoring(); } }
    ];

    adminSubtabs.forEach(tab => {
        if (tab.btn) {
            tab.btn.addEventListener('click', () => {
                adminSubtabs.forEach(t => {
                    if (t.btn) t.btn.classList.remove('active');
                    if (t.panel) {
                        t.panel.classList.add('hidden');
                        t.panel.classList.remove('active');
                    }
                });
                tab.btn.classList.add('active');
                if (tab.panel) {
                    tab.panel.classList.remove('hidden');
                    tab.panel.classList.add('active');
                }
                if (tab.onShow) tab.onShow();
            });
        }
    });

    function loadAdminDashboard() {
        selectedClientIdForAdmin = null;
        adminDetailsDisplay.classList.add('hidden');
        adminDetailsEmptyState.classList.remove('hidden');
        
        // Default to showing Overview subpanel
        if (btnAdminSubOverview) {
            btnAdminSubOverview.click();
        } else {
            fetchAdminStats();
            fetchAdminUsers();
        }
    }

    function fetchAdminStats() {
        fetch('/api/admin/stats')
        .then(response => {
            if (!response.ok) throw new Error("Could not fetch stats");
            return response.json();
        })
        .then(data => {
            const stats = data.stats;
            const isMetric = unitMetric.checked;
            
            if (adminValTotalUsers) {
                adminValTotalUsers.textContent = stats.total_users;
            }
            if (adminValAvgAge) {
                adminValAvgAge.textContent = `${stats.avg_age} yrs`;
            }
            if (adminValAvgWeight) {
                if (isMetric) {
                    adminValAvgWeight.textContent = `${stats.avg_weight} kg`;
                } else {
                    const lbsVal = Math.round(stats.avg_weight * 2.20462);
                    adminValAvgWeight.textContent = `${lbsVal} lbs`;
                }
            }

            if (adminValActiveWeek) {
                adminValActiveWeek.textContent = stats.active_last_7_days || 0;
            }
            if (adminValCheckinsWeek) {
                adminValCheckinsWeek.textContent = stats.checkins_last_7_days || 0;
            }
            if (adminValOnboardingComplete) {
                adminValOnboardingComplete.textContent = `${stats.onboarding_completed || 0} profiles onboarded`;
            }
            if (adminValTotalFoods) {
                adminValTotalFoods.textContent = stats.total_foods || 0;
            }
            if (adminValTotalLogs) {
                adminValTotalLogs.textContent = stats.total_audit_logs || 0;
            }
            
            // Draw Demographics Distribution Charts
            renderAdminDistributionCharts(stats.goals, stats.activities);
            renderAdminOpsChart(stats);
        })
        .catch(err => console.log(err.message));
    }

    function renderAdminDistributionCharts(goals, activities) {
        const goalCtx = document.getElementById('adminGoalDistChart');
        const activityCtx = document.getElementById('adminActivityDistChart');
        if (!goalCtx || !activityCtx) return;
        
        // Goals chart (Doughnut)
        const goalsLabels = Object.keys(goals).map(g => {
            const map = {
                "lose": "Weight Loss",
                "lose_mild": "Mild Loss",
                "maintain": "Maintain Weight",
                "gain_mild": "Mild Gain",
                "gain": "Muscle Gain"
            };
            return map[g] || g;
        });
        const goalsData = Object.values(goals);
        
        if (goalChartInstance) {
            goalChartInstance.data.labels = goalsLabels;
            goalChartInstance.data.datasets[0].data = goalsData;
            goalChartInstance.update();
        } else {
            goalChartInstance = new Chart(goalCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: goalsLabels,
                    datasets: [{
                        data: goalsData,
                        backgroundColor: ['#8b5cf6', '#ec4899', '#06b6d4', '#10b981', '#f59e0b'],
                        borderWidth: 1,
                        borderColor: 'rgba(255, 255, 255, 0.1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                        }
                    }
                }
            });
        }
        
        // Activities chart (Bar)
        const actLabels = Object.keys(activities).map(a => {
            const map = {
                "sedentary": "Sedentary",
                "light": "Light",
                "moderate": "Moderate",
                "active": "Active",
                "very_active": "Very Active"
            };
            return map[a] || a;
        });
        const actData = Object.values(activities);
        
        if (activityChartInstance) {
            activityChartInstance.data.labels = actLabels;
            activityChartInstance.data.datasets[0].data = actData;
            activityChartInstance.update();
        } else {
            activityChartInstance = new Chart(activityCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: actLabels,
                    datasets: [{
                        data: actData,
                        backgroundColor: 'rgba(6, 182, 212, 0.5)',
                        borderColor: '#06b6d4',
                        borderWidth: 1.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.03)' },
                            ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.03)' },
                            ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } }
                        }
                    }
                }
            });
        }
    }

    function renderAdminOpsChart(stats) {
        const opsCtx = document.getElementById('adminOpsChart');
        if (!opsCtx) return;
        
        const labels = ['Onboarded', 'Coach Assigned', 'Active 7d', 'Check-ins 7d'];
        const data = [
            stats.onboarding_completed || 0,
            stats.assigned_clients || 0,
            stats.active_last_7_days || 0,
            stats.checkins_last_7_days || 0
        ];
        
        if (opsChartInstance) {
            opsChartInstance.data.datasets[0].data = data;
            opsChartInstance.update();
        } else {
            opsChartInstance = new Chart(opsCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: ['#2563eb', '#0f766e', '#14b8a6', '#f59e0b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#64748b', font: { family: 'Inter', size: 10 } } },
                        y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { color: '#64748b', font: { family: 'Inter', size: 10 }, precision: 0 } }
                    }
                }
            });
        }
    }

    function fetchAdminUsers() {
        fetch('/api/admin/users')
        .then(response => {
            if (!response.ok) throw new Error("Could not load users list");
            return response.json();
        })
        .then(data => {
            allUsersData = data.users || [];
            filterAndRenderAdminUsers();
        })
        .catch(err => console.log(err.message));
    }

    function filterAndRenderAdminUsers() {
        const isMetric = unitMetric.checked;
        const searchQuery = adminUserSearch ? adminUserSearch.value.toLowerCase().trim() : '';
        const selectedCoachStatus = adminUserCoachFilter ? adminUserCoachFilter.value : 'all';
        const selectedGoal = adminUserGoalFilter ? adminUserGoalFilter.value : 'all';

        // Filter users
        const filteredUsers = allUsersData.filter(user => {
            const matchesSearch = user.username.toLowerCase().includes(searchQuery);
            const matchesCoachStatus =
                selectedCoachStatus === 'all' ||
                (selectedCoachStatus === 'assigned' && Boolean(user.coach_id)) ||
                (selectedCoachStatus === 'unassigned' && !user.coach_id) ||
                (selectedCoachStatus === 'onboarded' && Boolean(user.onboarding_completed));
            const matchesGoal = selectedGoal === 'all' || user.goal === selectedGoal;
            return matchesSearch && matchesCoachStatus && matchesGoal;
        });

        adminUsersTbody.innerHTML = '';
        
        if (filteredUsers.length === 0) {
            adminUsersTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No matching clients found.</td></tr>';
            return;
        }

        filteredUsers.forEach(user => {
            let weightVal = "—";
            if (user.weight_kg) {
                weightVal = isMetric ? `${Math.round(user.weight_kg)} kg` : `${Math.round(user.weight_kg * 2.20462)} lbs`;
            }

            const genderSymbol = user.gender === 'female' ? 'Female' : user.gender === 'male' ? 'Male' : '—';
            const coachingLabel = user.coach_id ? 'assigned' : user.onboarding_completed ? 'onboarded' : 'setup';
            const coachingClass = user.coach_id ? 'tier-premium' : user.onboarding_completed ? 'tier-enterprise' : 'tier-free';
            const coachingBadge = `<span class="tier-badge ${coachingClass}">${coachingLabel}</span>`;

            const row = `
                <tr data-id="${user.id}">
                    <td><strong>${user.username}</strong></td>
                    <td>${coachingBadge}</td>
                    <td>${genderSymbol}</td>
                    <td>${user.age || "—"}</td>
                    <td>${weightVal}</td>
                </tr>
            `;
            adminUsersTbody.insertAdjacentHTML('beforeend', row);
        });

        // Add click listener on user rows
        const rows = adminUsersTbody.querySelectorAll('tr');
        rows.forEach(row => {
            const userId = row.dataset.id;
            if (selectedClientIdForAdmin && selectedClientIdForAdmin == userId) {
                row.classList.add('selected-row');
            }
            row.addEventListener('click', () => {
                rows.forEach(r => r.classList.remove('selected-row'));
                row.classList.add('selected-row');
                
                const clickedUser = filteredUsers.find(u => u.id == userId);
                loadClientInsights(clickedUser);
            });
        });
    }

    // Bind filters
    if (adminUserSearch) {
        adminUserSearch.addEventListener('input', filterAndRenderAdminUsers);
    }
    if (adminUserCoachFilter) {
        adminUserCoachFilter.addEventListener('change', filterAndRenderAdminUsers);
    }
    if (adminUserGoalFilter) {
        adminUserGoalFilter.addEventListener('change', filterAndRenderAdminUsers);
    }

    function loadClientInsights(user) {
        selectedClientIdForAdmin = user.id;
        
        adminDetailsEmptyState.classList.add('hidden');
        adminDetailsDisplay.classList.remove('hidden');

        adminDisplayClientName.textContent = user.username;
        const joinDate = user.created_at ? user.created_at.split(' ')[0] : "—";
        adminDisplayJoinDate.textContent = `Registered: ${joinDate}`;

        // Standard stats
        const isMetric = unitMetric.checked;
        adminClientAge.textContent = user.age ? `${user.age} yrs` : "—";
        adminClientHeight.textContent = user.height_cm ? `${Math.round(user.height_cm)} cm` : "—";
        
        if (user.weight_kg) {
            adminClientWeight.textContent = isMetric ? `${Math.round(user.weight_kg)} kg` : `${Math.round(user.weight_kg * 2.20462)} lbs`;
        } else {
            adminClientWeight.textContent = "—";
        }

        if (adminClientCoachingStatus) {
            const status = user.coach_id ? 'Coach assigned' : user.onboarding_completed ? 'Onboarded' : 'Setup needed';
            adminClientCoachingStatus.textContent = status;
            adminClientCoachingStatus.className = `tier-badge ${user.coach_id ? 'tier-premium' : user.onboarding_completed ? 'tier-enterprise' : 'tier-free'}`;
        }
        const tagsInput = document.getElementById('admin-client-tags');
        const coachInput = document.getElementById('admin-coach-id');
        if (tagsInput) tagsInput.value = Array.isArray(user.client_tags) ? user.client_tags.join(', ') : '';
        if (coachInput) coachInput.value = user.coach_id || '';

        // Mapping Goal labels
        const goalsMap = {
            "lose": "Weight Loss",
            "lose_mild": "Mild Loss",
            "maintain": "Maintain",
            "gain_mild": "Mild Gain",
            "gain": "Muscle Gain"
        };
        adminClientGoal.textContent = goalsMap[user.goal] || "—";
        
        // Mapping Activity labels
        const activityMap = {
            "sedentary": "Sedentary",
            "light": "Lightly Active",
            "moderate": "Moderately Active",
            "active": "Very Active"
        };
        adminClientActivity.textContent = activityMap[user.activity] || "—";

        // Overrides Form Populate
        overrideCal.value = user.custom_calories || '';
        overridePro.value = user.custom_protein || '';
        overrideCarb.value = user.custom_carbs || '';
        overrideFat.value = user.custom_fat || '';

        // Call the calculator engine API to retrieve targets for this client (takes custom overrides into account)
        if (user.age && user.height_cm && user.weight_kg) {
            fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    age: user.age,
                    height_cm: user.height_cm,
                    weight_kg: user.weight_kg,
                    gender: user.gender,
                    activity: user.activity,
                    goal: user.goal
                })
            })
            .then(res => {
                if (!res.ok) throw new Error();
                return res.json();
            })
            .then(calcData => {
                adminClientTargetCalories.textContent = `${formatNumber(calcData.target_calories)} kcal`;
                adminClientProtein.textContent = `${calcData.macros.protein.grams}g`;
                adminClientCarbs.textContent = `${calcData.macros.carbs.grams}g`;
                adminClientFats.textContent = `${calcData.macros.fat.grams}g`;
            })
            .catch(() => {
                adminClientTargetCalories.textContent = "—";
                adminClientProtein.textContent = "—";
                adminClientCarbs.textContent = "—";
                adminClientFats.textContent = "—";
            });
        } else {
            adminClientTargetCalories.textContent = "Profile Incomplete";
            adminClientProtein.textContent = "—";
            adminClientCarbs.textContent = "—";
            adminClientFats.textContent = "—";
        }

        // Fetch user history log and render admin chart
        fetch(`/api/admin/users/${user.id}/history`)
        .then(res => res.json())
        .then(data => {
            renderAdminClientChart(data.history);
        })
        .catch(err => console.log(err.message));

        loadAdminThread(user.id);
        loadAdminWeeklyReport(user.id, false);
    }

    function loadAdminThread(userId) {
        fetch(`/api/admin/users/${userId}/thread`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('admin-thread-list');
            if (!list) return;
            const messages = data.messages || [];
            list.innerHTML = messages.slice(0, 6).map(msg => `<p><strong>${msg.sender_username}:</strong> ${msg.message}</p>`).join('') || '<p>No private thread messages yet.</p>';
        });
    }

    function loadAdminWeeklyReport(userId, showOutput = true) {
        fetch(`/api/admin/users/${userId}/weekly-report`)
        .then(res => res.json())
        .then(data => {
            const report = data.report;
            const targetList = document.getElementById('admin-target-history-list');
            if (targetList) {
                const history = report.target_history || [];
                targetList.innerHTML = history.length
                    ? `<h4>Target History</h4>${history.map(item => `<p>${item.created_at}: ${item.calories} kcal, ${item.protein}g P (${item.reason || 'update'})</p>`).join('')}`
                    : '<p>No target override history yet.</p>';
            }
            if (showOutput) {
                const output = document.getElementById('admin-weekly-report-output');
                if (output) {
                    output.classList.remove('hidden');
                    output.innerHTML = `<strong>Weekly Report Ready</strong><p>Period: ${report.period.start} to ${report.period.end}</p><p>Adherence: ${report.progress ? report.progress.adherence_score : 'n/a'} • Streak: ${report.progress ? report.progress.streak_days : 0} days</p>`;
                }
            }
        });
    }

    function renderAdminClientChart(history) {
        const adminChartCanvas = document.getElementById('adminClientChart');
        if (!adminChartCanvas) return;
        const ctx = adminChartCanvas.getContext('2d');
        const isMetric = unitMetric.checked;
        
        const labels = history.map(h => h.logged_at);
        const data = history.map(h => {
            return isMetric ? h.weight_kg : Math.round(h.weight_kg * 2.20462);
        });

        if (adminChartInstance) {
            adminChartInstance.data.labels = labels;
            adminChartInstance.data.datasets[0].data = data;
            adminChartInstance.data.datasets[0].label = isMetric ? 'Weight (kg)' : 'Weight (lbs)';
            adminChartInstance.update();
            return;
        }

        adminChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: isMetric ? 'Weight (kg)' : 'Weight (lbs)',
                    data: data,
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6, 182, 212, 0.08)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#6366f1',
                    pointBorderColor: '#070a12',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 22, 38, 0.95)',
                        titleFont: { family: 'Outfit', size: 13 },
                        bodyFont: { family: 'Inter', size: 12 },
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                    }
                }
            }
        });
    }

    // Predefined Food Database CRUD Controls
    function fetchAdminFoods() {
        fetch('/api/foods')
        .then(response => {
            if (!response.ok) throw new Error("Could not fetch foods");
            return response.json();
        })
        .then(data => {
            allPredefinedFoods = data.foods || [];
            currentFoodPage = 1;
            renderAdminFoods();
        })
        .catch(err => console.log(err.message));
    }

    function renderAdminFoods() {
        if (!adminFoodsTbody) return;
        const searchQuery = adminFoodSearch ? adminFoodSearch.value.toLowerCase().trim() : '';
        const filteredFoods = allPredefinedFoods.filter(food => 
            food.name.toLowerCase().includes(searchQuery)
        );

        const totalItems = filteredFoods.length;
        const totalPages = Math.max(1, Math.ceil(totalItems / foodItemsPerPage));
        
        if (currentFoodPage > totalPages) {
            currentFoodPage = totalPages;
        }

        const startIndex = (currentFoodPage - 1) * foodItemsPerPage;
        const endIndex = Math.min(startIndex + foodItemsPerPage, totalItems);
        const pageItems = filteredFoods.slice(startIndex, endIndex);

        if (foodPageInfo) {
            foodPageInfo.textContent = `Page ${currentFoodPage} of ${totalPages}`;
        }
        if (btnFoodPrev) {
            btnFoodPrev.disabled = currentFoodPage === 1;
        }
        if (btnFoodNext) {
            btnFoodNext.disabled = currentFoodPage === totalPages;
        }

        adminFoodsTbody.innerHTML = '';
        if (pageItems.length === 0) {
            adminFoodsTbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No foods found.</td></tr>';
            return;
        }

        pageItems.forEach(food => {
            const row = `
                <tr data-id="${food.id}">
                    <td><strong>${food.name}</strong></td>
                    <td>${food.calories_per_100g} kcal</td>
                    <td>${food.protein_per_100g}g</td>
                    <td>${food.carbs_per_100g}g</td>
                    <td>${food.fat_per_100g}g</td>
                    <td style="text-align: right;">
                        <button class="btn-icon btn-edit-food" data-id="${food.id}" title="Edit Food">
                            <i data-lucide="edit-3" style="width: 14px; height: 14px;"></i>
                        </button>
                        <button class="btn-icon btn-danger-action btn-delete-food" data-id="${food.id}" title="Delete Food" style="margin-left: 8px;">
                            <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                        </button>
                    </td>
                </tr>
            `;
            adminFoodsTbody.insertAdjacentHTML('beforeend', row);
        });

        // Re-initialize lucide icons inside the table
        lucide.createIcons();

        // Wire Edit/Delete buttons
        adminFoodsTbody.querySelectorAll('.btn-edit-food').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const foodId = btn.dataset.id;
                const food = allPredefinedFoods.find(f => f.id == foodId);
                if (food) showFoodForm(food);
            });
        });

        adminFoodsTbody.querySelectorAll('.btn-delete-food').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const foodId = btn.dataset.id;
                deletePredefinedFood(foodId);
            });
        });
    }

    function showFoodForm(food = null) {
        if (!adminFoodFormContainer) return;
        adminFoodFormContainer.classList.remove('hidden');
        adminFoodStatus.className = 'status-banner hidden';

        if (food) {
            // Edit Mode
            document.getElementById('food-form-title').textContent = "Edit Predefined Food";
            document.getElementById('food-form-subtitle').textContent = "Modify calorie and macro properties per 100g portion.";
            adminFoodFormId.value = food.id;
            adminFoodFormName.value = food.name;
            adminFoodFormCal.value = food.calories_per_100g;
            adminFoodFormPro.value = food.protein_per_100g;
            adminFoodFormCarb.value = food.carbs_per_100g;
            adminFoodFormFat.value = food.fat_per_100g;
            btnSaveFoodText.textContent = "Update Food";
        } else {
            // Add Mode
            document.getElementById('food-form-title').textContent = "Add Predefined Food";
            document.getElementById('food-form-subtitle').textContent = "Define calorie and macro properties per 100g portions.";
            adminFoodForm.reset();
            adminFoodFormId.value = '';
            btnSaveFoodText.textContent = "Save Food";
        }
    }

    if (btnCancelFood) {
        btnCancelFood.addEventListener('click', () => {
            if (adminFoodFormContainer) {
                adminFoodFormContainer.classList.add('hidden');
            }
        });
    }

    if (btnShowAddFoodForm) {
        btnShowAddFoodForm.addEventListener('click', () => {
            showFoodForm();
        });
    }

    if (adminFoodSearch) {
        adminFoodSearch.addEventListener('input', () => {
            currentFoodPage = 1;
            renderAdminFoods();
        });
    }

    if (btnFoodPrev) {
        btnFoodPrev.addEventListener('click', () => {
            if (currentFoodPage > 1) {
                currentFoodPage--;
                renderAdminFoods();
            }
        });
    }

    if (btnFoodNext) {
        btnFoodNext.addEventListener('click', () => {
            currentFoodPage++;
            renderAdminFoods();
        });
    }

    if (adminFoodForm) {
        adminFoodForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const foodId = adminFoodFormId.value;
            const name = adminFoodFormName.value.trim();
            const calories = parseInt(adminFoodFormCal.value);
            const protein = parseFloat(adminFoodFormPro.value);
            const carbs = parseFloat(adminFoodFormCarb.value);
            const fat = parseFloat(adminFoodFormFat.value);

            const payload = { name, calories, protein, carbs, fat };
            const method = foodId ? 'PUT' : 'POST';
            const url = foodId ? `/api/admin/foods/${foodId}` : '/api/admin/foods';

            adminFoodStatus.className = 'status-banner hidden';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => {
                if (!res.ok) throw new Error("Failed to save food item.");
                return res.json();
            })
            .then(() => {
                adminFoodStatus.textContent = foodId ? "Food updated successfully!" : "Food created successfully!";
                adminFoodStatus.className = "status-banner success";
                
                // Hide container after 1s
                setTimeout(() => {
                    adminFoodFormContainer.classList.add('hidden');
                }, 1000);

                // Refresh foods database list
                fetchAdminFoods();
            })
            .catch(err => {
                adminFoodStatus.textContent = err.message;
                adminFoodStatus.className = "status-banner error";
            });
        });
    }

    function deletePredefinedFood(foodId) {
        const confirmDelete = confirm("Are you sure you want to delete this predefined food item from the database?");
        if (!confirmDelete) return;

        fetch(`/api/admin/foods/${foodId}`, {
            method: 'DELETE'
        })
        .then(res => {
            if (!res.ok) throw new Error("Failed to delete food item.");
            return res.json();
        })
        .then(() => {
            fetchAdminFoods();
        })
        .catch(err => alert(err.message));
    }

    // System Monitor & Security Logs Controller
    function fetchAdminAuditLogs() {
        fetch('/api/admin/audit-logs')
        .then(response => {
            if (!response.ok) throw new Error("Could not load audit logs");
            return response.json();
        })
        .then(data => {
            const logs = data.logs || [];
            if (!adminLogsTbody) return;
            adminLogsTbody.innerHTML = '';
            
            if (logs.length === 0) {
                adminLogsTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No administrative actions logged yet.</td></tr>';
                return;
            }

            logs.forEach(log => {
                const row = `
                    <tr>
                        <td style="white-space: nowrap; color: var(--text-muted); font-size: 11px;">${log.logged_at}</td>
                        <td><strong>${log.admin_name || 'Admin'}</strong></td>
                        <td><span style="padding: 2px 6px; border-radius: 4px; font-size: 11px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: var(--text-secondary); text-transform: uppercase;">${log.action_type}</span></td>
                        <td><code>${log.target_info || '—'}</code></td>
                        <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${log.details || ''}">${log.details || '—'}</td>
                    </tr>
                `;
                adminLogsTbody.insertAdjacentHTML('beforeend', row);
            });
        })
        .catch(err => console.log(err.message));
    }

    function startSystemHealthMonitoring() {
        stopSystemHealth();
        updateSystemHealthMetrics();
        systemHealthInterval = setInterval(updateSystemHealthMetrics, 3000);
    }

    function stopSystemHealth() {
        if (systemHealthInterval) {
            clearInterval(systemHealthInterval);
            systemHealthInterval = null;
        }
    }

    function updateSystemHealthMetrics() {
        const cpu = Math.floor(Math.random() * 25) + 5; 
        const mem = Math.floor(Math.random() * 50) + 200; 
        const dbConns = Math.floor(Math.random() * 4) + 2; 
        const latency = Math.floor(Math.random() * 20) + 30; 

        if (systemValCpu) {
            systemValCpu.textContent = `${cpu}%`;
            systemBarCpu.style.width = `${cpu}%`;
            updateHealthDot(cpuHealthDot, cpu, 70, 90);
        }
        if (systemValMem) {
            systemValMem.textContent = `${mem} MB`;
            const memPercent = Math.round((mem / 1024) * 100);
            systemBarMem.style.width = `${memPercent}%`;
            updateHealthDot(memHealthDot, memPercent, 75, 90);
        }
        if (systemValDb) {
            systemValDb.textContent = `${dbConns} / 20 Conn`;
            systemBarDb.style.width = `${Math.round((dbConns / 20) * 100)}%`;
            updateHealthDot(dbHealthDot, dbConns, 15, 18);
        }
        if (systemValLatency) {
            systemValLatency.textContent = `${latency} ms`;
            systemBarLatency.style.width = `${Math.round((latency / 200) * 100)}%`;
            updateHealthDot(latencyHealthDot, latency, 100, 150);
        }
    }

    function updateHealthDot(dotElement, val, warningLimit, dangerLimit) {
        if (!dotElement) return;
        if (val >= dangerLimit) {
            dotElement.style.background = '#ef4444';
            dotElement.style.boxShadow = '0 0 8px #ef4444';
        } else if (val >= warningLimit) {
            dotElement.style.background = '#f59e0b';
            dotElement.style.boxShadow = '0 0 8px #f59e0b';
        } else {
            dotElement.style.background = '#10b981';
            dotElement.style.boxShadow = '0 0 8px #10b981';
        }
    }

    // Client Delete Event
    btnAdminDeleteUser.addEventListener('click', () => {
        if (!selectedClientIdForAdmin) return;
        
        const confirmDelete = confirm("Are you sure you want to delete this user profile? All historical weight logs will be permanently deleted and cannot be recovered.");
        if (!confirmDelete) return;

        fetch(`/api/admin/users/${selectedClientIdForAdmin}`, {
            method: 'DELETE'
        })
        .then(res => {
            if (!res.ok) throw new Error("Failed to delete user profile.");
            return res.json();
        })
        .then(() => {
            selectedClientIdForAdmin = null;
            adminDetailsDisplay.classList.add('hidden');
            adminDetailsEmptyState.classList.remove('hidden');
            fetchAdminStats();
            fetchAdminUsers();
        })
        .catch(err => alert(err.message));
    });

    // Wire Global Announcement Submit
    if (adminAnnouncementForm) {
        adminAnnouncementForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = adminAnnouncementMsg.value.trim();
            adminAnnouncementStatus.className = 'status-banner hidden';
            
            fetch('/api/admin/announcement', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            })
            .then(res => {
                if (!res.ok) throw new Error("Failed to broadcast announcement.");
                return res.json();
            })
            .then(() => {
                adminAnnouncementStatus.textContent = "Announcement broadcasted successfully!";
                adminAnnouncementStatus.className = "status-banner success";
                adminAnnouncementMsg.value = '';
            })
            .catch(err => {
                adminAnnouncementStatus.textContent = err.message;
                adminAnnouncementStatus.className = "status-banner error";
            });
        });
    }

    // Wire Direct Coaching Advice Message Submit
    if (adminMessageForm) {
        adminMessageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (!selectedClientIdForAdmin) return;
            const message = adminClientMsg.value.trim();
            adminMessageStatus.className = 'status-banner hidden';
            
            fetch('/api/admin/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ receiver_id: selectedClientIdForAdmin, message })
            })
            .then(res => {
                if (!res.ok) throw new Error("Failed to send coaching message.");
                return res.json();
            })
            .then(() => {
                adminMessageStatus.textContent = "Coaching advice sent successfully!";
                adminMessageStatus.className = "status-banner success";
                adminClientMsg.value = '';
            })
            .catch(err => {
                adminMessageStatus.textContent = err.message;
                adminMessageStatus.className = "status-banner error";
            });
        });
    }

    const btnAssignCoach = document.getElementById('btn-assign-coach');
    if (btnAssignCoach) {
        btnAssignCoach.addEventListener('click', () => {
            if (!selectedClientIdForAdmin) return;
            const status = document.getElementById('admin-coach-workflow-status');
            const tags = (document.getElementById('admin-client-tags').value || '').split(',').map(t => t.trim()).filter(Boolean);
            const coachId = document.getElementById('admin-coach-id').value || session.userId;
            fetch(`/api/admin/users/${selectedClientIdForAdmin}/coach`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ coach_id: coachId, client_tags: tags })
            })
            .then(res => {
                if (!res.ok) throw new Error('Failed to assign coach.');
                return res.json();
            })
            .then(() => {
                if (status) {
                    status.textContent = 'Coach assignment saved.';
                    status.className = 'status-banner success';
                }
                fetchAdminUsers();
            })
            .catch(err => {
                if (status) {
                    status.textContent = err.message;
                    status.className = 'status-banner error';
                }
            });
        });
    }

    const btnExportWeeklyReport = document.getElementById('btn-export-weekly-report');
    if (btnExportWeeklyReport) {
        btnExportWeeklyReport.addEventListener('click', () => {
            if (selectedClientIdForAdmin) loadAdminWeeklyReport(selectedClientIdForAdmin, true);
        });
    }

    const btnSendThreadMessage = document.getElementById('btn-send-thread-message');
    if (btnSendThreadMessage) {
        btnSendThreadMessage.addEventListener('click', () => {
            if (!selectedClientIdForAdmin) return;
            const textarea = document.getElementById('admin-thread-message');
            const message = textarea.value.trim();
            if (!message) return;
            fetch(`/api/admin/users/${selectedClientIdForAdmin}/thread`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            })
            .then(res => res.json())
            .then(() => {
                textarea.value = '';
                loadAdminThread(selectedClientIdForAdmin);
            });
        });
    }

    // Wire Target Overrides Form Submit
    if (adminOverrideForm) {
        adminOverrideForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (!selectedClientIdForAdmin) return;
            
            const calories = overrideCal.value;
            const protein = overridePro.value;
            const carbs = overrideCarb.value;
            const fat = overrideFat.value;
            adminOverrideStatus.className = 'status-banner hidden';
            
            fetch('/api/admin/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: selectedClientIdForAdmin,
                    calories,
                    protein,
                    carbs,
                    fat
                })
            })
            .then(res => {
                if (!res.ok) throw new Error("Failed to apply target overrides.");
                return res.json();
            })
            .then(() => {
                adminOverrideStatus.textContent = "Target overrides applied successfully!";
                adminOverrideStatus.className = "status-banner success";
                
                // Refresh client details display
                fetch('/api/admin/users')
                .then(r => r.json())
                .then(d => {
                    allUsersData = d.users || [];
                    const u = allUsersData.find(x => x.id == selectedClientIdForAdmin);
                    if (u) loadClientInsights(u);
                });
            })
            .catch(err => {
                adminOverrideStatus.textContent = err.message;
                adminOverrideStatus.className = "status-banner error";
            });
        });
        
        btnClearOverride.addEventListener('click', () => {
            if (!selectedClientIdForAdmin) return;
            adminOverrideStatus.className = 'status-banner hidden';
            
            fetch(`/api/admin/override/${selectedClientIdForAdmin}`, {
                method: 'DELETE'
            })
            .then(res => {
                if (!res.ok) throw new Error("Failed to clear overrides.");
                return res.json();
            })
            .then(() => {
                adminOverrideStatus.textContent = "Overrides cleared successfully.";
                adminOverrideStatus.className = "status-banner success";
                
                overrideCal.value = '';
                overridePro.value = '';
                overrideCarb.value = '';
                overrideFat.value = '';
                
                // Refresh client details
                fetch('/api/admin/users')
                .then(r => r.json())
                .then(d => {
                    allUsersData = d.users || [];
                    const u = allUsersData.find(x => x.id == selectedClientIdForAdmin);
                    if (u) loadClientInsights(u);
                });
            })
            .catch(err => {
                adminOverrideStatus.textContent = err.message;
                adminOverrideStatus.className = "status-banner error";
            });
        });
    }

    // -------------------------------------------------------------
    // User Dashboard Overview Controller
    // -------------------------------------------------------------
    function renderProgressIntelligence(progress) {
        if (!progress) return;
        const setText = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setText('adherence-score-pill', `${progress.adherence_score}`);
        setText('hero-adherence-score', `${progress.adherence_score}/100`);
        setText('insight-streak', `${progress.streak_days} days`);
        setText('insight-macro-consistency', `${progress.macro_consistency_pct}%`);
        setText('insight-goal-eta', progress.goal_eta && progress.goal_eta.eta_date ? progress.goal_eta.eta_date : 'Needs trend');
        setText('insight-why', progress.why_weight_changed || 'Keep logging to unlock explanations.');
    }

    function renderMealPlan(mealPlan) {
        const preview = document.getElementById('meal-plan-preview');
        const shopping = document.getElementById('shopping-list-preview');
        const btnViewFull = document.getElementById('btn-view-full-meal-plan');
        if (!preview) return;
        
        if (!mealPlan || !mealPlan.plan || !mealPlan.plan.days) {
            preview.innerHTML = '<p class="empty-inbox-text">Generate a macro-aware weekly plan and shopping list from your current targets.</p>';
            if (shopping) shopping.innerHTML = '';
            if (btnViewFull) btnViewFull.classList.add('hidden');
            return;
        }
        
        if (btnViewFull) btnViewFull.classList.remove('hidden');
        
        preview.innerHTML = mealPlan.plan.days.slice(0, 2).map(day => `
            <div class="meal-plan-day">
                <strong>${day.date}</strong>
                ${day.meals.map(meal => `<p>${meal.name}: ${meal.food} (${meal.calories} kcal)</p>`).join('')}
            </div>
        `).join('');
        
        const list = mealPlan.shopping || mealPlan.shopping_list || [];
        if (shopping) {
            shopping.innerHTML = list.slice(0, 8).map(item => `${item.item}: ${Math.round(item.amount_g)}g`).join(' • ');
        }
        
        populateMealPlanModal(mealPlan);
    }

    function populateMealPlanModal(mealPlan) {
        const targetsDiv = document.getElementById('meal-plan-modal-targets');
        if (targetsDiv) {
            const days = mealPlan.plan.days;
            const targetCal = days[0]?.meals.reduce((sum, m) => sum + m.calories, 0) || 2000;
            const targetProtein = days[0]?.meals.reduce((sum, m) => sum + m.protein, 0) || 120;
            const targetCarbs = days[0]?.meals.reduce((sum, m) => sum + m.carbs, 0) || 200;
            const targetFat = days[0]?.meals.reduce((sum, m) => sum + m.fat, 0) || 60;
            
            targetsDiv.innerHTML = `
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--radius-md); padding: 12px; text-align: center;">
                    <span style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Daily Calories</span>
                    <strong style="display: block; font-size: 1.25rem; color: #10b981; margin-top: 4px;">${targetCal} kcal</strong>
                </div>
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--radius-md); padding: 12px; text-align: center;">
                    <span style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Daily Protein</span>
                    <strong style="display: block; font-size: 1.25rem; color: #3b82f6; margin-top: 4px;">${targetProtein}g</strong>
                </div>
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--radius-md); padding: 12px; text-align: center;">
                    <span style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Daily Carbs</span>
                    <strong style="display: block; font-size: 1.25rem; color: #eab308; margin-top: 4px;">${targetCarbs}g</strong>
                </div>
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--radius-md); padding: 12px; text-align: center;">
                    <span style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Daily Fats</span>
                    <strong style="display: block; font-size: 1.25rem; color: #ef4444; margin-top: 4px;">${targetFat}g</strong>
                </div>
            `;
        }
        
        const scheduleDiv = document.getElementById('meal-plan-modal-schedule');
        if (scheduleDiv) {
            scheduleDiv.innerHTML = mealPlan.plan.days.map(day => {
                const dateParts = day.date.split('-');
                const dateObj = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
                const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
                const displayDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                return `
                    <div class="meal-plan-day-card" style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: var(--radius-md); padding: 16px; display: flex; flex-direction: column; gap: 10px;">
                        <div style="border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 6px; display: flex; justify-content: space-between; align-items: baseline;">
                            <strong style="color: var(--text-primary); font-size: 1rem; font-family: var(--font-heading);">${dayName}</strong>
                            <span style="font-size: 11px; color: var(--text-secondary);">${displayDate}</span>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 10px; flex: 1;">
                            ${day.meals.map(meal => `
                                <div style="font-size: 12px; line-height: 1.4;">
                                    <span style="color: var(--secondary-light); font-weight: 600; text-transform: uppercase; font-size: 10px; display: block; letter-spacing: 0.5px;">${meal.name}</span>
                                    <span style="color: var(--text-primary); font-weight: 500;">${meal.food}</span>
                                    <span style="color: var(--text-secondary); display: block; font-size: 11px; margin-top: 2px;">
                                        Portion: ${meal.amount_g}g • ${meal.calories} kcal<br/>
                                        (P: ${meal.protein}g C: ${meal.carbs}g F: ${meal.fat}g)
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                        <div style="font-size: 10px; color: var(--text-muted); border-top: 1px dashed rgba(255, 255, 255, 0.05); padding-top: 6px; font-style: italic; margin-top: auto;">
                            💡 Swap with similar calorie food if needed.
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        const shoppingDiv = document.getElementById('meal-plan-modal-shopping');
        if (shoppingDiv) {
            const list = mealPlan.shopping || mealPlan.shopping_list || [];
            shoppingDiv.innerHTML = list.map(item => `
                <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-primary); cursor: pointer; padding: 6px; border-radius: 4px;" class="shopping-item-label">
                    <input type="checkbox" style="accent-color: #10b981; cursor: pointer;">
                    <span>${item.item}: <strong style="color: #10b981;">${Math.round(item.amount_g)}g</strong></span>
                </label>
            `).join('');
        }
    }

    function renderLoggingShortcuts(data) {
        const wrap = document.getElementById('logging-shortcuts');
        if (!wrap) return;
        const items = [
            ...(data.favorite_foods || []).slice(0, 4).map(food => ({ label: `★ ${food.food_name}`, name: food.food_name })),
            ...(data.recent_foods || []).slice(0, 4).map(food => ({ label: `Recent: ${food.food_name}`, name: food.food_name }))
        ];
        if (items.length === 0) {
            wrap.innerHTML = '';
            return;
        }
        wrap.innerHTML = items.map(item => `<button type="button" class="shortcut-chip" data-food-name="${item.name}">${item.label}</button>`).join('');
        wrap.querySelectorAll('.shortcut-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const input = document.getElementById('food-search-input');
                if (input) {
                    input.value = btn.dataset.foodName;
                    input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter' }));
                }
            });
        });
    }

    function loadUserDashboard() {
        const todayStr = new Date().toISOString().split('T')[0];
        fetch(`/api/user/dashboard?date=${todayStr}`)
        .then(res => {
            if (!res.ok) throw new Error("Failed to load user dashboard");
            return res.json();
        })
        .then(data => {
            renderUserDashboard(data);
        })
        .catch(err => console.log(err.message));
    }

    const btnGenerateMealPlan = document.getElementById('btn-generate-meal-plan');
    if (btnGenerateMealPlan) {
        btnGenerateMealPlan.addEventListener('click', () => {
            btnGenerateMealPlan.disabled = true;
            btnGenerateMealPlan.textContent = 'Building...';
            fetch('/api/user/meal-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
            .then(res => {
                if (!res.ok) return res.json().then(err => { throw new Error(err.error || 'Could not generate meal plan.'); });
                return res.json();
            })
            .then(() => loadUserDashboard())
            .catch(err => alert(err.message))
            .finally(() => {
                btnGenerateMealPlan.disabled = false;
                btnGenerateMealPlan.textContent = 'Generate';
            });
        });
    }

    // Setup workflow step row clickable navigation
    document.querySelectorAll('.setup-step-row [data-step]').forEach(stepSpan => {
        stepSpan.addEventListener('click', () => {
            const step = stepSpan.dataset.step;
            if (step === 'profile') {
                const setupTab = document.getElementById('tab-calculator');
                if (setupTab) setupTab.click();
                const target = document.getElementById('settings-avatar-badge') || document.querySelector('.profile-settings-avatar-card') || document.querySelector('.input-panel');
                if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (step === 'targets') {
                const setupTab = document.getElementById('tab-calculator');
                if (setupTab) setupTab.click();
                const target = document.getElementById('calorie-calculator-form') || document.getElementById('output-section');
                if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (step === 'plan') {
                if (window.bootstrapSession && window.bootstrapSession.isLoggedIn) {
                    const dashboardTab = document.getElementById('tab-dashboard');
                    if (dashboardTab) dashboardTab.click();
                    setTimeout(() => {
                        const target = document.querySelector('.meal-plan-card');
                        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 150);
                } else {
                    openAuthModal();
                    alert("Please sign in or register to generate your personalized weekly meal plans.");
                }
            } else if (step === 'track') {
                if (window.bootstrapSession && window.bootstrapSession.isLoggedIn) {
                    const dashboardTab = document.getElementById('tab-dashboard');
                    if (dashboardTab) dashboardTab.click();
                } else {
                    openAuthModal();
                    alert("Please sign in or register to unlock daily food, hydration, and weight trackers.");
                }
            }
        });
    });

    // Diet Plan View and Export handlers
    const btnViewFullMealPlan = document.getElementById('btn-view-full-meal-plan');
    const mealPlanModal = document.getElementById('meal-plan-modal');
    const btnCloseMealPlan = document.getElementById('btn-close-meal-plan');
    const btnPrintMealPlan = document.getElementById('btn-print-meal-plan');
    const btnExportTxt = document.getElementById('btn-export-txt-meal-plan');

    if (btnViewFullMealPlan && mealPlanModal) {
        btnViewFullMealPlan.addEventListener('click', () => {
            mealPlanModal.classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        });
    }

    if (btnCloseMealPlan && mealPlanModal) {
        btnCloseMealPlan.addEventListener('click', () => {
            mealPlanModal.classList.add('hidden');
        });
        mealPlanModal.addEventListener('click', (e) => {
            if (e.target === mealPlanModal) {
                mealPlanModal.classList.add('hidden');
            }
        });
    }

    if (btnPrintMealPlan) {
        btnPrintMealPlan.addEventListener('click', () => {
            if (!currentDashboardData || !currentDashboardData.meal_plan) return;
            const mealPlan = currentDashboardData.meal_plan;
            const days = mealPlan.plan.days;
            const targetCal = days[0]?.meals.reduce((sum, m) => sum + m.calories, 0) || 2000;
            const targetProtein = days[0]?.meals.reduce((sum, m) => sum + m.protein, 0) || 120;
            const targetCarbs = days[0]?.meals.reduce((sum, m) => sum + m.carbs, 0) || 200;
            const targetFat = days[0]?.meals.reduce((sum, m) => sum + m.fat, 0) || 60;
            
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
<html>
<head>
    <title>NutriQuant Weekly Diet Plan</title>
    <style>
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #1e293b; padding: 30px; line-height: 1.5; background: #fff; }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; }
        h1 { color: #0f172a; margin: 0; font-size: 1.8rem; }
        .subtitle { color: #64748b; font-size: 0.95rem; margin-top: 5px; }
        .targets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; margin-bottom: 30px; }
        .target-col { text-align: center; }
        .target-col span { font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }
        .target-col strong { display: block; font-size: 1.3rem; color: #0f172a; margin-top: 4px; }
        .days-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; page-break-inside: auto; }
        .day-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; page-break-inside: avoid; background: #fff; }
        .day-card h3 { margin: 0 0 12px 0; color: #0f172a; font-size: 1.1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 6px; }
        .meal-item { margin: 10px 0; font-size: 0.88rem; }
        .meal-name { font-weight: 600; color: #0f766e; text-transform: uppercase; font-size: 0.75rem; display: block; letter-spacing: 0.5px; }
        .meal-food { color: #334155; font-weight: 500; }
        .meal-macros { font-size: 0.8rem; color: #64748b; display: block; margin-top: 2px; }
        .shopping-list { margin-top: 40px; page-break-before: always; }
        .shopping-list h2 { font-size: 1.4rem; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 15px; }
        .shopping-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .shopping-item { padding: 8px; border-bottom: 1px solid #f1f5f9; font-size: 0.88rem; color: #334155; }
        @media print {
            body { padding: 0; }
            .no-print { display: none; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>NutriQuant Weekly Diet Plan</h1>
        <div class="subtitle">Custom meal plan starting week of ${mealPlan.week_start}</div>
    </div>
    
    <div class="targets">
        <div class="target-col"><span>Daily Calories</span><strong>${targetCal} kcal</strong></div>
        <div class="target-col"><span>Daily Protein</span><strong>${targetProtein}g</strong></div>
        <div class="target-col"><span>Daily Carbs</span><strong>${targetCarbs}g</strong></div>
        <div class="target-col"><span>Daily Fats</span><strong>${targetFat}g</strong></div>
    </div>
    
    <div class="days-grid">
        ${days.map(day => {
            const dateParts = day.date.split('-');
            const dateObj = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
            const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
            const displayDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            return `
                <div class="day-card">
                    <h3>${dayName} (${displayDate})</h3>
                    ${day.meals.map(meal => `
                        <div class="meal-item">
                            <span class="meal-name">${meal.name}</span>
                            <span class="meal-food">${meal.food} (${meal.amount_g}g)</span>
                            <span class="meal-macros">${meal.calories} kcal • P: ${meal.protein}g C: ${meal.carbs}g F: ${meal.fat}g</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }).join('')}
    </div>
    
    <div class="shopping-list">
        <h2>Grocery Shopping List</h2>
        <div class="shopping-grid">
            ${(mealPlan.shopping || mealPlan.shopping_list || []).map(item => `
                <div class="shopping-item">${item.item}: <strong>${Math.round(item.amount_g)}g</strong></div>
            `).join('')}
        </div>
    </div>
    
    <script>
        window.onload = function() {
            window.print();
            window.onafterprint = function() { window.close(); };
        };
    </script>
</body>
</html>
            `);
            printWindow.document.close();
        });
    }

    if (btnExportTxt) {
        btnExportTxt.addEventListener('click', () => {
            if (!currentDashboardData || !currentDashboardData.meal_plan) return;
            const mealPlan = currentDashboardData.meal_plan;
            const days = mealPlan.plan.days;
            const targetCal = days[0]?.meals.reduce((sum, m) => sum + m.calories, 0) || 2000;
            const targetProtein = days[0]?.meals.reduce((sum, m) => sum + m.protein, 0) || 120;
            const targetCarbs = days[0]?.meals.reduce((sum, m) => sum + m.carbs, 0) || 200;
            const targetFat = days[0]?.meals.reduce((sum, m) => sum + m.fat, 0) || 60;
            
            let text = `==================================================\n`;
            text += `            NUTRIQUANT WEEKLY DIET PLAN\n`;
            text += `==================================================\n`;
            text += `Week Starting: ${mealPlan.week_start}\n`;
            text += `Daily Target Summary:\n`;
            text += `  Calories      : ${targetCal} kcal\n`;
            text += `  Protein       : ${targetProtein}g\n`;
            text += `  Carbohydrates : ${targetCarbs}g\n`;
            text += `  Fats          : ${targetFat}g\n`;
            text += `--------------------------------------------------\n\n`;
            
            days.forEach(day => {
                const dateParts = day.date.split('-');
                const dateObj = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
                const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
                const displayDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                text += `### ${dayName} (${displayDate}) ###\n`;
                day.meals.forEach(meal => {
                    text += `  * ${meal.name}: ${meal.food}\n`;
                    text += `    Portion: ${meal.amount_g}g | Calories: ${meal.calories} kcal\n`;
                    text += `    Macros: Protein ${meal.protein}g, Carbs ${meal.carbs}g, Fat ${meal.fat}g\n`;
                });
                text += `  * Swap note: Swap with a similar calorie food from your database.\n\n`;
            });
            
            text += `==================================================\n`;
            text += `            GROCERY SHOPPING LIST\n`;
            text += `==================================================\n`;
            const list = mealPlan.shopping || mealPlan.shopping_list || [];
            list.forEach(item => {
                text += `[ ] ${item.item}: ${Math.round(item.amount_g)}g\n`;
            });
            
            text += `\nGenerated by NutriQuant. Stay on track!`;
            
            const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `NutriQuant_Diet_Plan_${mealPlan.week_start}.txt`;
            link.click();
        });
    }

    const checkinForm = document.getElementById('client-checkin-form');
    if (checkinForm) {
        checkinForm.addEventListener('submit', (e) => {
            e.preventDefault();
            fetch('/api/user/checkins', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mood: document.getElementById('checkin-mood').value,
                    energy: document.getElementById('checkin-energy').value,
                    hunger: document.getElementById('checkin-hunger').value,
                    compliance: document.getElementById('checkin-compliance').value,
                    notes: document.getElementById('checkin-notes').value
                })
            })
            .then(res => res.json())
            .then(() => {
                document.getElementById('checkin-notes').value = '';
                loadUserDashboard();
            });
        });
    }

    function renderUserDashboard(data) {
        currentDashboardData = data;
        userDashboardGreeting.textContent = `Hello, ${data.user.username}!`;
        const welcomeMsg = document.getElementById('user-dashboard-welcome-msg');
        
        const isMetric = unitMetric.checked;
        const daily = data.daily_log;
        renderProgressIntelligence(data.progress);
        renderMealPlan(data.meal_plan);
        renderLoggingShortcuts(data);
        
        if (data.user && data.user.weight_kg) {
            currentUserWeight = data.user.weight_kg;
        }
        
        // 1. Check if user profile exists
        if (!data.user.age || !data.user.height_cm || !data.user.weight_kg) {
            welcomeMsg.textContent = "Welcome to NutriQuant! Go to the Calculator tab to set up your profile and generate targets.";
            
            // Set stats to zeroes
            userDashboardCalRemaining.textContent = "0";
            userDashboardCalTarget.textContent = "0 kcal";
            userDashboardCalConsumed.textContent = "0 kcal";
            document.getElementById('user-calorie-ring').style.strokeDashoffset = 415;
            
            userDashProteinProgress.textContent = "0g / 0g";
            userDashProteinBar.style.width = "0%";
            userDashCarbsProgress.textContent = "0g / 0g";
            userDashCarbsBar.style.width = "0%";
            userDashFatsProgress.textContent = "0g / 0g";
            userDashFatsBar.style.width = "0%";
            
            userDashWaterTotal.textContent = "0 ml";
            userDashWaterTarget.textContent = "0.0";
            
            dashWeightStart.textContent = "—";
            dashWeightCurrent.textContent = "—";
            dashWeightTarget.textContent = "—";
            userDashWeightProgressBar.style.width = "0%";
            userDashWeightGoalText.textContent = "Use the Calculator tab to estimate target calorie intake.";
            return;
        }
        
        welcomeMsg.textContent = "Let's stay on track with your nutrition and daily activity.";
        
        // 2. Compute targets using calculate API structure
        fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                age: data.user.age,
                height_cm: data.user.height_cm,
                weight_kg: data.user.weight_kg,
                gender: data.user.gender,
                activity: data.user.activity,
                goal: data.user.goal
            })
        })
        .then(res => res.json())
        .then(calc => {
            const targetCal = calc.target_calories;
            const proTarget = calc.macros.protein.grams;
            const carbTarget = calc.macros.carbs.grams;
            const fatTarget = calc.macros.fat.grams;
            const waterTargetL = calc.water_l;
            const proConsumed = daily.protein || 0;
            const carbConsumed = daily.carbs || 0;
            const fatConsumed = daily.fat || 0;
            const waterMl = daily.water_ml || 0;
            
            // Render Calories Ring
            const consumedCal = daily.calories || 0;
            const burnedCal = data.total_exercise_calories || 0;
            const remainingCal = Math.max(0, targetCal - consumedCal + burnedCal);
            userDashboardCalRemaining.textContent = formatNumber(remainingCal);
            const heroCalRemaining = document.getElementById('hero-cal-remaining');
            if (heroCalRemaining) {
                heroCalRemaining.textContent = `${formatNumber(remainingCal)} kcal`;
            }
            userDashboardCalTarget.textContent = `${formatNumber(targetCal)} kcal`;
            userDashboardCalConsumed.textContent = `${formatNumber(consumedCal)} kcal`;
            if (userDashboardCalBurned) {
                userDashboardCalBurned.textContent = `${formatNumber(burnedCal)} kcal`;
            }
            
            const calorieRing = document.getElementById('user-calorie-ring');
            const netConsumed = Math.max(0, consumedCal - burnedCal);
            const calPercentage = targetCal > 0 ? Math.min(1.0, netConsumed / targetCal) : 0;
            if (calorieRing) {
                calorieRing.style.strokeDashoffset = 415 - (415 * calPercentage);
            }

            const proteinRing = document.getElementById('user-protein-ring');
            if (proteinRing) {
                const proPercentage = proTarget > 0 ? Math.min(1.0, proConsumed / proTarget) : 0;
                proteinRing.style.strokeDashoffset = 339 - (339 * proPercentage);
            }

            const waterRing = document.getElementById('user-water-ring');
            if (waterRing) {
                const waterTargetMl = (waterTargetL || 0) * 1000;
                const waterPercentage = waterTargetMl > 0 ? Math.min(1.0, waterMl / waterTargetMl) : 0;
                waterRing.style.strokeDashoffset = 264 - (264 * waterPercentage);
            }
            
            // Render Macros Bars
            userDashProteinProgress.textContent = `${proConsumed}g / ${proTarget}g`;
            userDashProteinBar.style.width = `${Math.min(100, (proConsumed / proTarget) * 100)}%`;
            
            userDashCarbsProgress.textContent = `${carbConsumed}g / ${carbTarget}g`;
            userDashCarbsBar.style.width = `${Math.min(100, (carbConsumed / carbTarget) * 100)}%`;
            
            userDashFatsProgress.textContent = `${fatConsumed}g / ${fatTarget}g`;
            userDashFatsBar.style.width = `${Math.min(100, (fatConsumed / fatTarget) * 100)}%`;
            
            // Hydration widget
            userDashWaterTotal.textContent = `${waterMl} ml`;
            userDashWaterTarget.textContent = waterTargetL.toFixed(1);
            
            // Highlight interactive cups
            const loggedCups = Math.min(8, Math.floor(waterMl / 250));
            const cups = document.querySelectorAll('.water-cup-item');
            cups.forEach((cup, idx) => {
                if (idx < loggedCups) {
                    cup.classList.add('active');
                } else {
                    cup.classList.remove('active');
                }
            });
            
            // Render Weight Goal Progress
            const history = data.weight_history;
            const startW = history.length > 0 ? history[0].weight_kg : data.user.weight_kg;
            const currentW = history.length > 0 ? history[history.length - 1].weight_kg : data.user.weight_kg;
            const targetW = calc.ideal_weight_kg; // Default ideal BMI weight
            
            if (isMetric) {
                dashWeightStart.textContent = `${Math.round(startW)} kg`;
                dashWeightCurrent.textContent = `${Math.round(currentW)} kg`;
                dashWeightTarget.textContent = `${Math.round(targetW)} kg`;
            } else {
                dashWeightStart.textContent = `${Math.round(startW * 2.20462)} lbs`;
                dashWeightCurrent.textContent = `${Math.round(currentW * 2.20462)} lbs`;
                dashWeightTarget.textContent = `${Math.round(targetW * 2.20462)} lbs`;
            }
            
            // Calculate progress bar fill
            let weightPct = 0;
            if (data.user.goal.includes('lose')) {
                if (startW > targetW) {
                    weightPct = Math.max(0, Math.min(100, ((startW - currentW) / (startW - targetW)) * 100));
                } else {
                    weightPct = 100;
                }
                userDashWeightGoalText.textContent = `Weight Loss goal in progress. You have lost ${(Math.abs(startW - currentW)).toFixed(1)} kg.`;
            } else if (data.user.goal.includes('gain')) {
                if (targetW > startW) {
                    weightPct = Math.max(0, Math.min(100, ((currentW - startW) / (targetW - startW)) * 100));
                } else {
                    weightPct = 100;
                }
                userDashWeightGoalText.textContent = `Weight Gain goal in progress. You have gained ${(Math.abs(currentW - startW)).toFixed(1)} kg.`;
            } else {
                weightPct = 100;
                userDashWeightGoalText.textContent = `Weight Maintenance goal in progress. Stay consistent!`;
            }
            userDashWeightProgressBar.style.width = `${weightPct}%`;

            // Calculate weight projection forecast
            const projectionBox = document.getElementById('user-dashboard-weight-projection');
            const valProjectedDate = document.getElementById('val-projected-date');
            const valProjectedDaysLeft = document.getElementById('val-projected-days-left');

            if (projectionBox && valProjectedDate && valProjectedDaysLeft) {
                const goalType = data.user.goal;
                let daysToTarget = 0;
                
                if (goalType.includes('lose')) {
                    const diff = currentW - targetW;
                    if (diff > 0) {
                        const rate = goalType === 'lose' ? 500 : 250;
                        daysToTarget = Math.ceil((diff * 7700) / rate);
                    }
                } else if (goalType.includes('gain')) {
                    const diff = targetW - currentW;
                    if (diff > 0) {
                        const rate = goalType === 'gain' ? 500 : 250;
                        daysToTarget = Math.ceil((diff * 7700) / rate);
                    }
                }
                
                if (daysToTarget > 0 && daysToTarget < 365 * 5) {
                    const projDate = new Date();
                    projDate.setDate(projDate.getDate() + daysToTarget);
                    const dateOptions = { year: 'numeric', month: 'long', day: 'numeric' };
                    valProjectedDate.textContent = projDate.toLocaleDateString(undefined, dateOptions);
                    valProjectedDaysLeft.textContent = `(${daysToTarget} days remaining at target rate)`;
                    projectionBox.classList.remove('hidden');
                } else if ((goalType.includes('lose') && currentW <= targetW) || (goalType.includes('gain') && currentW >= targetW)) {
                    valProjectedDate.textContent = "Goal Achieved!";
                    valProjectedDaysLeft.textContent = "Congratulations on reaching your target weight!";
                    projectionBox.classList.remove('hidden');
                } else {
                    projectionBox.classList.add('hidden');
                }
            }

            // Compute dynamic automated achievements
            const loggedWeight = !!data.weight_logged_today;
            const metCalorie = consumedCal > 0 && consumedCal <= targetCal;
            const metProtein = proConsumed >= proTarget && proTarget > 0;
            const metHydration = waterMl >= (waterTargetL * 1000) && waterTargetL > 0;

            const achievements = {
                "log-weight": loggedWeight,
                "hit-calories": metCalorie,
                "hit-protein": metProtein,
                "drink-water": metHydration
            };

            let completedCount = 0;
            const checkedTasks = [];
            const checkboxes = document.querySelectorAll('#user-dashboard-checklist input[type="checkbox"]');
            checkboxes.forEach(cb => {
                const isCompleted = !!achievements[cb.dataset.task];
                cb.checked = isCompleted;
                if (isCompleted) {
                    checkedTasks.push(cb.dataset.task);
                }
                const label = cb.closest('.checklist-item-label');
                if (label) {
                    if (isCompleted) {
                        completedCount++;
                        label.classList.add('achievement-completed');
                    } else {
                        label.classList.remove('achievement-completed');
                    }
                }
            });

            // Update progress badge text
            const badge = document.getElementById('checklist-progress-badge');
            if (badge) {
                badge.textContent = `${completedCount}/4 Done`;
            }

            // Sync checklist achievements to the database automatically if out of sync
            const dbChecklist = JSON.parse(daily.checklist || '[]');
            const listsEqual = dbChecklist.length === checkedTasks.length && 
                               dbChecklist.every(t => checkedTasks.includes(t));
            if (!listsEqual) {
                const todayStr = new Date().toISOString().split('T')[0];
                fetch('/api/user/checklist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        date_str: todayStr,
                        checklist: JSON.stringify(checkedTasks)
                    })
                });
            }

            // Render Exercise Journal
            if (exerciseJournalTbody) {
                exerciseJournalTbody.innerHTML = '';
                const logs = data.exercise_logs || [];
                
                if (logs.length === 0) {
                    if (exerciseJournalEmptyState) exerciseJournalEmptyState.classList.remove('hidden');
                } else {
                    if (exerciseJournalEmptyState) exerciseJournalEmptyState.classList.add('hidden');
                    
                    logs.forEach(log => {
                        const row = `
                            <tr>
                                <td data-label="Activity"><strong>${log.activity_type}</strong></td>
                                <td data-label="Duration">${log.duration_min} mins</td>
                                <td data-label="Calories" style="color: #10b981; font-weight: 600;">+${log.calories_burned} kcal</td>
                                <td data-label="Actions" style="text-align: right;">
                                    <button class="btn-icon btn-danger-action btn-delete-exercise" data-id="${log.id}" title="Delete Log">
                                        <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                        exerciseJournalTbody.insertAdjacentHTML('beforeend', row);
                    });
                    
                    // Re-initialize lucide icons inside the table
                    lucide.createIcons();
                    
                    // Wire Delete buttons
                    exerciseJournalTbody.querySelectorAll('.btn-delete-exercise').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const logId = btn.dataset.id;
                            if (confirm("Are you sure you want to delete this exercise log?")) {
                                fetch(`/api/user/exercise/${logId}`, {
                                    method: 'DELETE'
                                })
                                .then(res => res.json())
                                .then(resData => {
                                    if (resData.success) {
                                        loadUserDashboard();
                                    } else {
                                        alert(resData.error || "Failed to delete exercise log.");
                                    }
                                })
                                .catch(err => console.log("Error deleting exercise log:", err));
                            }
                        });
                    });
                }
            }
        })
        .catch(err => console.log(err.message));
        
        // Render Coaching Board Inbox messages
        const inbox = document.getElementById('user-coaching-notes-list');
        if (data.coaching_notes.length === 0) {
            inbox.innerHTML = '<div class="empty-inbox-text">No notes or announcements from your coach.</div>';
        } else {
            inbox.innerHTML = '';
            data.coaching_notes.forEach(note => {
                const dateObj = new Date(note.created_at);
                const timeStr = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                const isGlobal = !note.receiver_id;
                const noteHtml = `
                    <div class="coach-note-item">
                        <div class="coach-note-header">
                            <span class="coach-badge" style="background:${isGlobal ? 'rgba(6,182,212,0.15);color:var(--secondary-light);' : 'rgba(99,102,241,0.15);color:var(--primary-light);'}">${isGlobal ? 'Broadcast' : 'Coaching Note'}</span>
                            <span class="note-time">${timeStr}</span>
                        </div>
                        <div class="note-msg">${note.message}</div>
                    </div>
                `;
                inbox.insertAdjacentHTML('beforeend', noteHtml);
            });
        }

        // Render Today's Food Journal Table
        const journalTbody = document.getElementById('food-journal-tbody');
        const journalEmptyState = document.getElementById('food-journal-empty-state');
        const journalTable = document.getElementById('food-journal-table');
        
        if (journalTbody && journalEmptyState && journalTable) {
            const logs = data.food_logs || [];
            if (logs.length === 0) {
                journalTbody.innerHTML = '';
                journalTable.classList.add('hidden');
                journalEmptyState.classList.remove('hidden');
            } else {
                journalEmptyState.classList.add('hidden');
                journalTable.classList.remove('hidden');
                journalTbody.innerHTML = '';
                
                logs.forEach(log => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td data-label="Food Item"><strong>${log.food_name}</strong></td>
                        <td data-label="Amount">${log.amount_g} g</td>
                        <td data-label="Calories">${log.calories} kcal</td>
                        <td data-label="Macros (P/C/F)">
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                P: <span style="color: var(--text-primary); font-weight: 500;">${log.protein}g</span> | 
                                C: <span style="color: var(--text-primary); font-weight: 500;">${log.carbs}g</span> | 
                                F: <span style="color: var(--text-primary); font-weight: 500;">${log.fat}g</span>
                            </div>
                        </td>
                        <td data-label="Actions" style="text-align: right;">
                            <button type="button" class="btn-delete-log" data-id="${log.id}" title="Remove entry">
                                <i data-lucide="trash-2" style="width: 16px; height: 16px;"></i>
                            </button>
                        </td>
                    `;
                    journalTbody.appendChild(tr);
                });
                
                // Re-initialize lucide icons for trash-2 icons in the table
                lucide.createIcons();
                
                // Wire delete button clicks
                journalTbody.querySelectorAll('.btn-delete-log').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const entryId = btn.dataset.id;
                        if (confirm("Are you sure you want to remove this logged food?")) {
                            fetch(`/api/user/food/${entryId}`, {
                                method: 'DELETE'
                            })
                            .then(res => res.json())
                            .then(resData => {
                                if (resData.success) {
                                    loadUserDashboard();
                                } else {
                                    alert(resData.error || "Failed to delete log.");
                                }
                            })
                            .catch(err => console.log("Error deleting log:", err));
                        }
                    });
                });
            }
        }
    }

    // Wire Hydration log buttons
    if (btnQuickAddWater) {
        btnQuickAddWater.addEventListener('click', () => {
            const todayStr = new Date().toISOString().split('T')[0];
            fetch('/api/user/water', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date_str: todayStr, amount_ml: 250 })
            })
            .then(res => res.json())
            .then(() => {
                loadUserDashboard();
            });
        });
    }
    
    // Wire interactive cup items click
    const cupsList = document.querySelectorAll('.water-cup-item');
    cupsList.forEach((cup, cupIndex) => {
        cup.addEventListener('click', () => {
            const todayStr = new Date().toISOString().split('T')[0];
            const absoluteAmount = (cupIndex + 1) * 250;
            
            fetch('/api/user/water', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    date_str: todayStr, 
                    amount_ml: absoluteAmount,
                    set_absolute: true
                })
            })
            .then(res => res.json())
            .then(() => {
                loadUserDashboard();
            });
        });
    });

    // Wire Quick Food Logger submit
    if (userDashFoodForm) {
        userDashFoodForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const todayStr = new Date().toISOString().split('T')[0];
            
            let payload = {
                date_str: todayStr
            };
            
            if (foodLoggingMode === 'select') {
                const amount = parseFloat(foodLogAmount.value);
                const servingUnit = document.getElementById('food-serving-unit') ? document.getElementById('food-serving-unit').value : 'g';
                const unitGrams = { g: 1, cup: 240, tbsp: 15, oz: 28.35, piece: 100 }[servingUnit] || 1;
                const amountInGrams = amount * unitGrams;
                
                if (!selectedAutocompleteFood) {
                    alert("Please search and select a food item first.");
                    return;
                }
                if (isNaN(amount) || amount <= 0) {
                    alert("Please enter a valid amount in grams.");
                    return;
                }
                
                const food = selectedAutocompleteFood;
                const factor = amountInGrams / 100.0;
                payload.food_name = `${food.name}`;
                payload.food_id = food.id;
                payload.amount_g = amountInGrams;
                payload.serving_unit = servingUnit;
                payload.serving_multiplier = amount;
                payload.calories = Math.round(food.calories_per_100g * factor);
                payload.protein = Math.round(food.protein_per_100g * factor);
                payload.carbs = Math.round(food.carbs_per_100g * factor);
                payload.fat = Math.round(food.fat_per_100g * factor);
            } else {
                const customName = document.getElementById('food-log-name').value.trim() || 'Custom Entry';
                const calories = parseInt(document.getElementById('food-log-calories').value);
                const protein = parseInt(document.getElementById('food-log-protein').value || 0);
                const carbs = parseInt(document.getElementById('food-log-carbs').value || 0);
                const fat = parseInt(document.getElementById('food-log-fat').value || 0);
                
                if (isNaN(calories) || calories < 0) {
                    alert("Please enter valid calories.");
                    return;
                }
                
                payload.food_name = customName;
                payload.amount_g = 100.0; // Default weight for custom logs
                payload.calories = calories;
                payload.protein = protein;
                payload.carbs = carbs;
                payload.fat = fat;
            }
            payload.favorite = !!(document.getElementById('food-log-favorite') && document.getElementById('food-log-favorite').checked);
            
            fetch('/api/user/food', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(() => {
                userDashFoodForm.reset();
                if (foodSearchInput) foodSearchInput.value = "";
                selectedAutocompleteFood = null;
                if (foodLogAmount) foodLogAmount.value = "100";
                if (foodLivePreview) foodLivePreview.classList.add('hidden');
                
                if (btnFoodModeSelect) btnFoodModeSelect.click();
                
                loadUserDashboard();
            })
            .catch(err => console.log("Error logging food:", err));
        });
    }

    const btnSaveCurrentTemplate = document.getElementById('btn-save-current-template');
    if (btnSaveCurrentTemplate) {
        btnSaveCurrentTemplate.addEventListener('click', () => {
            const entries = currentDashboardData ? (currentDashboardData.food_logs || []) : [];
            if (entries.length === 0) {
                alert('Log at least one food before saving a meal template.');
                return;
            }
            const name = prompt('Template name', 'My saved meal');
            if (!name) return;
            fetch('/api/user/meal-templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, entries })
            })
            .then(res => res.json())
            .then(() => loadUserDashboard());
        });
    }
    // Update live estimated burned calories preview
    function updateExerciseBurnPreview() {
        if (!exerciseSelect || !exerciseDuration || !exercisePreviewCal) return;
        const val = exerciseSelect.value;
        if (val === 'custom') {
            exercisePreviewCal.textContent = '0';
            return;
        }

        const duration = parseInt(exerciseDuration.value) || 0;
        if (duration <= 0) {
            exercisePreviewCal.textContent = '0';
            return;
        }

        // MET values
        const mets = {
            running: 8.0,
            cycling: 6.0,
            swimming: 7.0,
            walking: 3.5,
            weightlifting: 3.0,
            yoga: 2.5,
            hiit: 10.0,
            rope_jumping: 11.0,
            hiking: 6.0,
            rowing: 7.0,
            elliptical: 5.0,
            pilates: 3.0,
            dancing: 4.5,
            soccer: 7.0,
            basketball: 6.0,
            tennis: 7.0,
            crossfit: 8.0,
            boxing: 9.0,
            martial_arts: 10.0,
            badminton: 5.5,
            golf: 4.5,
            table_tennis: 4.0,
            volleyball: 4.0,
            cricket: 5.0,
            rock_climbing: 8.0,
            calisthenics: 6.0,
            stair_climber: 9.0
        };
        const met = mets[val] || 3.0;
        const weight = currentUserWeight || 70.0;
        const calories = Math.round(met * 3.5 * weight / 200.0 * duration);
        exercisePreviewCal.textContent = calories;
    }

    if (exerciseSelect) {
        exerciseSelect.addEventListener('change', () => {
            const val = exerciseSelect.value;
            if (val === 'custom') {
                if (exerciseNameGroup) exerciseNameGroup.classList.remove('hidden');
                if (exerciseCaloriesGroup) exerciseCaloriesGroup.classList.remove('hidden');
                if (exerciseLivePreview) exerciseLivePreview.classList.add('hidden');
            } else {
                if (exerciseNameGroup) exerciseNameGroup.classList.add('hidden');
                if (exerciseCaloriesGroup) exerciseCaloriesGroup.classList.add('hidden');
                if (exerciseLivePreview) exerciseLivePreview.classList.remove('hidden');
                updateExerciseBurnPreview();
            }
        });
    }

    if (exerciseDuration) {
        exerciseDuration.addEventListener('input', updateExerciseBurnPreview);
    }

    // Initial calculation preview call
    updateExerciseBurnPreview();

    // Wire Log Exercise submit
    if (userDashExerciseForm) {
        userDashExerciseForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const todayStr = new Date().toISOString().split('T')[0];
            const val = exerciseSelect.value;
            let activityType = "";
            let calories = null;
            const duration = parseInt(exerciseDuration.value);

            if (isNaN(duration) || duration <= 0) {
                alert("Please enter a valid exercise duration.");
                return;
            }

            if (val === 'custom') {
                activityType = exerciseNameInput.value.trim() || 'Custom Workout';
                calories = parseInt(exerciseCalories.value);
                if (isNaN(calories) || calories < 0) {
                    alert("Please enter valid calories burned.");
                    return;
                }
            } else {
                activityType = exerciseSelect.options[exerciseSelect.selectedIndex].text.split(" (")[0];
                calories = parseInt(exercisePreviewCal.textContent) || 0;
            }

            fetch('/api/user/exercise', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    date_str: todayStr,
                    activity_type: activityType,
                    duration_min: duration,
                    calories_burned: calories
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    userDashExerciseForm.reset();
                    if (exerciseNameGroup) exerciseNameGroup.classList.add('hidden');
                    if (exerciseCaloriesGroup) exerciseCaloriesGroup.classList.add('hidden');
                    if (exerciseLivePreview) exerciseLivePreview.classList.remove('hidden');
                    updateExerciseBurnPreview();
                    loadUserDashboard();
                } else {
                    alert(data.error || "Failed to log exercise.");
                }
            })
            .catch(err => console.log("Error logging exercise:", err));
        });
    }

    // Wire Daily Checklist Checkbox clicks
    const checklistCbs = document.querySelectorAll('#user-dashboard-checklist input[type="checkbox"]');
    checklistCbs.forEach(cb => {
        cb.addEventListener('change', () => {
            const todayStr = new Date().toISOString().split('T')[0];
            
            // Gather all checked task keys
            const checkedTasks = [];
            checklistCbs.forEach(box => {
                if (box.checked) checkedTasks.push(box.dataset.task);
            });
            
            fetch('/api/user/checklist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    date_str: todayStr,
                    checklist: JSON.stringify(checkedTasks)
                })
            });
        });
    });

    // -------------------------------------------------------------
    // Helper Layout Utilities
    // -------------------------------------------------------------
    function getMicronutrientIcon(name) {
        const map = {
            "Vitamin A": "eye",
            "Vitamin C": "sparkles",
            "Vitamin D": "sun",
            "Vitamin B12": "zap",
            "Folate (B9)": "dna",
            "Calcium": "bone",
            "Iron": "droplet",
            "Magnesium": "activity",
            "Zinc": "shield"
        };
        return map[name] || "info";
    }

    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\n))/g, ",");
    }

    const printButton = document.getElementById('btn-print');
    if (printButton) {
        printButton.addEventListener('click', () => {
            window.print();
        });
    }

    // -------------------------------------------------------------
    // Predefined Food Database & Live Calculations
    // -------------------------------------------------------------
    const foodSearchInput = document.getElementById('food-search-input');
    const foodSearchResults = document.getElementById('food-search-results');
    const foodLogAmount = document.getElementById('food-log-amount');
    const foodLivePreview = document.getElementById('food-live-preview');
    
    const previewCal = document.getElementById('preview-cal');
    const previewPro = document.getElementById('preview-pro');
    const previewCarb = document.getElementById('preview-carb');
    const previewFat = document.getElementById('preview-fat');

    function fetchPredefinedFoods() {
        fetch('/api/foods')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                predefinedFoods = data.foods;
            }
        })
        .catch(err => console.log("Error fetching predefined foods:", err));
    }

    function updateLivePreview() {
        if (!selectedAutocompleteFood || !foodLogAmount || !foodLivePreview) {
            foodLivePreview.classList.add('hidden');
            return;
        }
        
        const amount = parseFloat(foodLogAmount.value);
        if (isNaN(amount) || amount <= 0) {
            foodLivePreview.classList.add('hidden');
            return;
        }
        
        const food = selectedAutocompleteFood;
        const servingUnit = document.getElementById('food-serving-unit') ? document.getElementById('food-serving-unit').value : 'g';
        const unitGrams = { g: 1, cup: 240, tbsp: 15, oz: 28.35, piece: 100 }[servingUnit] || 1;
        const factor = (amount * unitGrams) / 100.0;
        const cal = Math.round(food.calories_per_100g * factor);
        const pro = Math.round(food.protein_per_100g * factor);
        const carb = Math.round(food.carbs_per_100g * factor);
        const fat = Math.round(food.fat_per_100g * factor);
        
        if (previewCal) previewCal.textContent = cal;
        if (previewPro) previewPro.textContent = `${pro}g`;
        if (previewCarb) previewCarb.textContent = `${carb}g`;
        if (previewFat) previewFat.textContent = `${fat}g`;
        
        foodLivePreview.classList.remove('hidden');
    }

    if (foodSearchInput && foodSearchResults) {
        foodSearchInput.addEventListener('keyup', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query) {
                foodSearchResults.classList.add('hidden');
                foodSearchResults.innerHTML = '';
                return;
            }

            const matches = predefinedFoods.filter(food => 
                food.name.toLowerCase().includes(query)
            ).slice(0, 15);

            if (matches.length === 0) {
                foodSearchResults.innerHTML = `<div class="autocomplete-item" style="cursor: default; color: var(--text-secondary);">No matching foods found</div>`;
                foodSearchResults.classList.remove('hidden');
                return;
            }

            foodSearchResults.innerHTML = '';
            matches.forEach(food => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.innerHTML = `
                    <span class="autocomplete-food-name">${food.name}</span>
                    <span class="autocomplete-food-macros">${food.calories_per_100g} kcal / 100g</span>
                `;
                item.addEventListener('click', () => {
                    selectedAutocompleteFood = food;
                    foodSearchInput.value = food.name;
                    foodSearchResults.classList.add('hidden');
                    updateLivePreview();
                });
                foodSearchResults.appendChild(item);
            });
            foodSearchResults.classList.remove('hidden');
        });

        document.addEventListener('click', (e) => {
            if (!foodSearchInput.contains(e.target) && !foodSearchResults.contains(e.target)) {
                foodSearchResults.classList.add('hidden');
            }
        });
    }

    if (foodLogAmount) {
        foodLogAmount.addEventListener('input', updateLivePreview);
    }
    const foodServingUnit = document.getElementById('food-serving-unit');
    if (foodServingUnit) {
        foodServingUnit.addEventListener('change', updateLivePreview);
    }

    // Toggle logger mode listeners
    const btnFoodModeSelect = document.getElementById('btn-food-mode-select');
    const btnFoodModeCustom = document.getElementById('btn-food-mode-custom');
    const foodSelectGroup = document.getElementById('food-select-group');
    const foodCustomGroup = document.getElementById('food-custom-group');
    const btnFoodLogText = document.getElementById('btn-food-log-text');

    if (btnFoodModeSelect && btnFoodModeCustom) {
        btnFoodModeSelect.addEventListener('click', () => {
            foodLoggingMode = 'select';
            btnFoodModeSelect.classList.add('active');
            btnFoodModeCustom.classList.remove('active');
            
            btnFoodModeSelect.style.background = 'rgba(99, 102, 241, 0.15)';
            btnFoodModeSelect.style.borderColor = 'rgba(99, 102, 241, 0.4)';
            btnFoodModeSelect.style.color = 'var(--text-primary)';
            btnFoodModeCustom.style.background = 'rgba(255, 255, 255, 0.05)';
            btnFoodModeCustom.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            btnFoodModeCustom.style.color = 'var(--text-secondary)';
            
            if (foodSelectGroup) foodSelectGroup.classList.remove('hidden');
            if (foodCustomGroup) foodCustomGroup.classList.add('hidden');
            if (btnFoodLogText) btnFoodLogText.textContent = 'Log Food';
            
            updateLivePreview();
        });

        btnFoodModeCustom.addEventListener('click', () => {
            foodLoggingMode = 'custom';
            btnFoodModeCustom.classList.add('active');
            btnFoodModeSelect.classList.remove('active');
            
            btnFoodModeCustom.style.background = 'rgba(99, 102, 241, 0.15)';
            btnFoodModeCustom.style.borderColor = 'rgba(99, 102, 241, 0.4)';
            btnFoodModeCustom.style.color = 'var(--text-primary)';
            btnFoodModeSelect.style.background = 'rgba(255, 255, 255, 0.05)';
            btnFoodModeSelect.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            btnFoodModeSelect.style.color = 'var(--text-secondary)';
            
            if (foodCustomGroup) foodCustomGroup.classList.remove('hidden');
            if (foodSelectGroup) foodSelectGroup.classList.add('hidden');
            if (btnFoodLogText) btnFoodLogText.textContent = 'Log Custom Calories';
        });
    }

    // Call food initialization on load
    fetchPredefinedFoods();

    // ==========================================================================
    // FAB Menu Toggles & Radial Shortcuts Logic
    // ==========================================================================
    const fabWrapper = document.getElementById('fab-wrapper');
    const fabTrigger = document.getElementById('fab-trigger');
    if (fabTrigger && fabWrapper) {
        fabTrigger.addEventListener('click', () => {
            fabWrapper.classList.toggle('active');
        });
    }

    // Close FAB when clicking elsewhere
    document.addEventListener('click', (e) => {
        if (fabWrapper && !fabWrapper.contains(e.target) && fabWrapper.classList.contains('active')) {
            fabWrapper.classList.remove('active');
        }
    });

    const fabShortcutFood = document.getElementById('fab-shortcut-food');
    const fabShortcutWater = document.getElementById('fab-shortcut-water');
    const fabShortcutExercise = document.getElementById('fab-shortcut-exercise');

    if (fabShortcutFood) {
        fabShortcutFood.addEventListener('click', () => {
            if (fabWrapper) fabWrapper.classList.remove('active');
            
            // Switch page to Dashboard
            const tabDash = document.getElementById('tab-dashboard');
            if (tabDash) tabDash.click();
            
            // Switch unified logger to Food Log tab
            const foodLogTab = document.getElementById('tab-log-food');
            if (foodLogTab) foodLogTab.click();
            
            // Scroll to the logger widget
            const quickLogWidget = document.querySelector('.quick-log-card');
            if (quickLogWidget) quickLogWidget.scrollIntoView({ behavior: 'smooth' });
        });
    }

    if (fabShortcutWater) {
        fabShortcutWater.addEventListener('click', () => {
            if (fabWrapper) fabWrapper.classList.remove('active');
            
            // Trigger quick water log event
            if (btnQuickAddWater) {
                btnQuickAddWater.click();
            }
        });
    }

    if (fabShortcutExercise) {
        fabShortcutExercise.addEventListener('click', () => {
            if (fabWrapper) fabWrapper.classList.remove('active');
            
            // Switch page to Dashboard
            const tabDash = document.getElementById('tab-dashboard');
            if (tabDash) tabDash.click();
            
            // Switch unified logger to Exercise Log tab
            const exerciseLogTab = document.getElementById('tab-log-exercise');
            if (exerciseLogTab) exerciseLogTab.click();
            
            // Scroll to logger
            const quickLogWidget = document.querySelector('.quick-log-card');
            if (quickLogWidget) quickLogWidget.scrollIntoView({ behavior: 'smooth' });
        });
    }
});
