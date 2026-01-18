/**
 * Elite Sales Mobile App
 * Progressive Web App for field sales team
 */

// ============================================================================
// APP STATE
// ============================================================================
const AppState = {
    currentView: 'dashboard',
    salespersonId: null,
    currentPosition: null,
    watchId: null,
    isOnline: navigator.onLine,
    pendingSync: [],
    currentRoute: null,
    routeStopIndex: 0,
    achievements: [],
    stats: {
        today: { leads: 0, knocks: 0, conversions: 0, points: 0 },
        week: { leads: 0, knocks: 0, conversions: 0, points: 0 }
    }
};

// ============================================================================
// API CLIENT
// ============================================================================
const API = {
    baseUrl: '/api/elite',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            if (!AppState.isOnline) {
                // Queue for later sync
                AppState.pendingSync.push({ endpoint, options, timestamp: Date.now() });
                localStorage.setItem('pendingSync', JSON.stringify(AppState.pendingSync));
            }
            throw error;
        }
    },

    // Dashboard
    async getDashboard() {
        return this.request(`/mobile/dashboard?salesperson_id=${AppState.salespersonId}`);
    },

    // Check-in
    async checkin(data) {
        return this.request('/mobile/checkin', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Leads
    async getLeads(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request(`/leads?${params}`);
    },

    async createLead(data) {
        return this.request('/leads', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async quickLead(data) {
        return this.request('/mobile/quick-lead', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateLead(leadId, data) {
        return this.request(`/leads/${leadId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // Routes
    async optimizeRoute(data) {
        return this.request('/routes/optimize', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async getPropertyData(address) {
        return this.request(`/routes/property/${encodeURIComponent(address)}`);
    },

    // Competitors
    async logCompetitor(data) {
        return this.request('/competitors', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async getCompetitorHeatmap(swathId, days = 7) {
        return this.request(`/competitors/heatmap?swath_id=${swathId}&days=${days}`);
    },

    // Estimates
    async generateEstimate(data) {
        return this.request('/estimates/instant', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // DNK
    async addDNK(data) {
        return this.request('/dnk', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async checkDNK(lat, lon) {
        return this.request(`/dnk/check?lat=${lat}&lon=${lon}`);
    },

    // Scripts
    async getScript(situation) {
        return this.request(`/scripts/${situation}`);
    },

    async getAllScripts() {
        return this.request('/scripts');
    },

    // Objections
    async logObjection(data) {
        return this.request('/objections', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Leaderboard
    async getLeaderboard(period = 'TODAY') {
        return this.request(`/leaderboard?period=${period}`);
    },

    // Achievements
    async getAchievements() {
        return this.request(`/achievements/${AppState.salespersonId}`);
    }
};

// ============================================================================
// UI COMPONENTS
// ============================================================================
const UI = {
    showView(viewId) {
        // Hide all views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

        // Show selected view
        const view = document.getElementById(`${viewId}-view`);
        if (view) {
            view.classList.add('active');
            AppState.currentView = viewId;
        }

        // Update nav
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        const navItem = document.querySelector(`.nav-item[data-view="${viewId}"]`);
        if (navItem) navItem.classList.add('active');

        // Load view data
        this.loadViewData(viewId);
    },

    async loadViewData(viewId) {
        switch (viewId) {
            case 'dashboard':
                await Dashboard.load();
                break;
            case 'route':
                await RouteView.load();
                break;
            case 'leads':
                await LeadsView.load();
                break;
            case 'estimate':
                await EstimateView.init();
                break;
            case 'scripts':
                await ScriptsView.load();
                break;
            case 'leaderboard':
                await LeaderboardView.load();
                break;
            case 'competitors':
                await CompetitorsView.load();
                break;
        }
    },

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    },

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    },

    hideAllModals() {
        document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
        document.body.style.overflow = '';
    },

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${this.getToastIcon(type)}</span>
            <span class="toast-message">${message}</span>
        `;

        document.body.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    getToastIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
            achievement: '🏆'
        };
        return icons[type] || icons.info;
    },

    showAchievement(achievement) {
        const toast = document.getElementById('achievement-toast');
        if (toast) {
            toast.querySelector('.achievement-icon').textContent = achievement.icon || '🏆';
            toast.querySelector('.achievement-name').textContent = achievement.name;
            toast.querySelector('.achievement-description').textContent = achievement.description;
            toast.querySelector('.achievement-points').textContent = `+${achievement.points} pts`;

            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 5000);
        }
    },

    toggleSideMenu() {
        document.getElementById('side-menu').classList.toggle('open');
        document.getElementById('menu-overlay').classList.toggle('active');
    },

    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    },

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },

    formatDate(dateStr) {
        return new Date(dateStr).toLocaleDateString();
    },

    formatTime(dateStr) {
        return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
};

// ============================================================================
// DASHBOARD VIEW
// ============================================================================
const Dashboard = {
    async load() {
        try {
            const data = await API.getDashboard();
            this.render(data);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.renderOffline();
        }
    },

    render(data) {
        // Update stats
        document.getElementById('today-leads').textContent = data.today?.leads || 0;
        document.getElementById('today-knocks').textContent = data.today?.knocks || 0;
        document.getElementById('today-conversions').textContent = data.today?.conversions || 0;

        document.getElementById('week-leads').textContent = data.this_week?.leads || 0;
        document.getElementById('week-knocks').textContent = data.this_week?.knocks || 0;
        document.getElementById('week-conversions').textContent = data.this_week?.conversions || 0;

        document.getElementById('total-points').textContent = UI.formatNumber(data.points?.total || 0);
        document.getElementById('today-points').textContent = `+${data.points?.today || 0} today`;

        // Update level progress
        const levelProgress = data.points?.level_progress || 0;
        document.getElementById('level-progress').style.width = `${levelProgress}%`;
        document.getElementById('level-text').textContent = `Level ${data.points?.level || 1}`;

        // Update recent activity
        this.renderRecentActivity(data.recent_activity || []);

        // Update quick actions based on current route
        if (data.active_route) {
            document.getElementById('route-status').textContent =
                `${data.active_route.completed}/${data.active_route.total} stops`;
        }
    },

    renderRecentActivity(activities) {
        const container = document.getElementById('recent-activity');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = '<div class="empty-state">No recent activity</div>';
            return;
        }

        container.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <span class="activity-icon">${this.getActivityIcon(activity.type)}</span>
                <div class="activity-content">
                    <div class="activity-text">${activity.description}</div>
                    <div class="activity-time">${UI.formatTime(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');
    },

    getActivityIcon(type) {
        const icons = {
            lead: '📋',
            knock: '🚪',
            conversion: '✅',
            achievement: '🏆',
            competitor: '👁',
            dnk: '🚫'
        };
        return icons[type] || '📌';
    },

    renderOffline() {
        // Show cached data
        const cached = localStorage.getItem('dashboardCache');
        if (cached) {
            this.render(JSON.parse(cached));
        }
    }
};

// ============================================================================
// ROUTE VIEW
// ============================================================================
const RouteView = {
    map: null,
    markers: [],

    async load() {
        if (AppState.currentRoute) {
            this.renderRoute(AppState.currentRoute);
        } else {
            this.renderNoRoute();
        }
    },

    async generateRoute() {
        const gridCellId = document.getElementById('grid-cell-select')?.value;
        const targetHomes = document.getElementById('target-homes')?.value || 20;

        try {
            UI.showToast('Generating optimized route...', 'info');

            const data = await API.optimizeRoute({
                salesperson_id: AppState.salespersonId,
                grid_cell_id: gridCellId,
                target_homes: parseInt(targetHomes)
            });

            AppState.currentRoute = data.route;
            AppState.routeStopIndex = 0;
            localStorage.setItem('currentRoute', JSON.stringify(data.route));

            this.renderRoute(data.route);
            UI.showToast('Route generated!', 'success');
        } catch (error) {
            UI.showToast('Failed to generate route', 'error');
        }
    },

    renderRoute(route) {
        const container = document.getElementById('route-stops');
        if (!container) return;

        document.getElementById('route-total-stops').textContent = route.total_stops;
        document.getElementById('route-estimated-time').textContent = route.estimated_time || 'N/A';

        container.innerHTML = route.stops.map((stop, index) => `
            <div class="route-stop ${index < AppState.routeStopIndex ? 'completed' : ''}
                         ${index === AppState.routeStopIndex ? 'current' : ''}"
                 data-index="${index}">
                <div class="stop-number">${index + 1}</div>
                <div class="stop-info">
                    <div class="stop-address">${stop.address}</div>
                    <div class="stop-meta">
                        ${stop.property_value ? `Value: ${UI.formatCurrency(stop.property_value)}` : ''}
                        ${stop.priority ? `<span class="priority-badge priority-${stop.priority.toLowerCase()}">${stop.priority}</span>` : ''}
                    </div>
                </div>
                <div class="stop-actions">
                    <button class="btn-icon" onclick="RouteView.navigateTo(${index})">📍</button>
                    <button class="btn-icon" onclick="RouteView.markComplete(${index})">✓</button>
                </div>
            </div>
        `).join('');
    },

    renderNoRoute() {
        const container = document.getElementById('route-stops');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🗺️</div>
                    <div class="empty-text">No active route</div>
                    <button class="btn btn-primary" onclick="RouteView.generateRoute()">
                        Generate Route
                    </button>
                </div>
            `;
        }
    },

    navigateTo(index) {
        const stop = AppState.currentRoute?.stops[index];
        if (stop) {
            const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(stop.address)}`;
            window.open(url, '_blank');
        }
    },

    markComplete(index) {
        AppState.routeStopIndex = index + 1;
        localStorage.setItem('routeStopIndex', AppState.routeStopIndex);
        this.renderRoute(AppState.currentRoute);

        // Check if route is complete
        if (AppState.routeStopIndex >= AppState.currentRoute.total_stops) {
            UI.showToast('Route completed! Great work!', 'success');
        }
    },

    skipStop(index) {
        // Mark as skipped and move to next
        AppState.routeStopIndex = index + 1;
        this.renderRoute(AppState.currentRoute);
    }
};

// ============================================================================
// LEADS VIEW
// ============================================================================
const LeadsView = {
    leads: [],
    filter: 'all',

    async load() {
        try {
            const data = await API.getLeads({ salesperson_id: AppState.salespersonId });
            this.leads = data.leads || [];
            this.render();
        } catch (error) {
            console.error('Failed to load leads:', error);
            this.renderOffline();
        }
    },

    render() {
        const container = document.getElementById('leads-list');
        if (!container) return;

        const filtered = this.filterLeads();

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div class="empty-text">No leads yet</div>
                    <button class="btn btn-primary" onclick="LeadsView.showQuickLead()">
                        Add First Lead
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(lead => `
            <div class="lead-card" data-id="${lead.id}" onclick="LeadsView.showDetail(${lead.id})">
                <div class="lead-header">
                    <span class="lead-quality quality-${lead.quality?.toLowerCase() || 'warm'}">${lead.quality || 'WARM'}</span>
                    <span class="lead-time">${UI.formatTime(lead.created_at)}</span>
                </div>
                <div class="lead-name">${lead.customer_name || 'Unknown'}</div>
                <div class="lead-address">${lead.address || 'No address'}</div>
                <div class="lead-footer">
                    <span class="lead-status status-${lead.status?.toLowerCase() || 'new'}">${lead.status || 'NEW'}</span>
                    ${lead.synced ? '<span class="synced-badge">✓ Synced</span>' : ''}
                </div>
            </div>
        `).join('');
    },

    filterLeads() {
        if (this.filter === 'all') return this.leads;
        return this.leads.filter(l => l.quality?.toLowerCase() === this.filter);
    },

    setFilter(filter) {
        this.filter = filter;
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.filter-btn[data-filter="${filter}"]`)?.classList.add('active');
        this.render();
    },

    showQuickLead() {
        // Pre-fill with current location
        if (AppState.currentPosition) {
            document.getElementById('lead-lat').value = AppState.currentPosition.latitude;
            document.getElementById('lead-lon').value = AppState.currentPosition.longitude;
        }
        UI.showModal('quick-lead-modal');
    },

    async submitQuickLead() {
        const form = document.getElementById('quick-lead-form');
        const formData = new FormData(form);

        const data = {
            salesperson_id: AppState.salespersonId,
            customer_name: formData.get('customer_name'),
            phone: formData.get('phone'),
            address: formData.get('address'),
            latitude: parseFloat(formData.get('latitude')) || AppState.currentPosition?.latitude,
            longitude: parseFloat(formData.get('longitude')) || AppState.currentPosition?.longitude,
            lead_quality: formData.get('quality') || 'WARM',
            notes: formData.get('notes')
        };

        try {
            const result = await API.quickLead(data);
            UI.hideModal('quick-lead-modal');
            UI.showToast('Lead captured!', 'success');
            form.reset();
            await this.load();

            // Check for achievement
            if (result.achievement) {
                UI.showAchievement(result.achievement);
            }
        } catch (error) {
            UI.showToast('Failed to save lead', 'error');
        }
    },

    showDetail(leadId) {
        const lead = this.leads.find(l => l.id === leadId);
        if (!lead) return;

        // Show lead detail modal or navigate to detail view
        console.log('Show lead detail:', lead);
    },

    renderOffline() {
        const cached = localStorage.getItem('leadsCache');
        if (cached) {
            this.leads = JSON.parse(cached);
            this.render();
        }
    }
};

// ============================================================================
// ESTIMATE VIEW
// ============================================================================
const EstimateView = {
    photos: [],
    vehicleInfo: null,
    currentEstimate: null,

    init() {
        this.photos = [];
        this.currentEstimate = null;
        this.render();
    },

    render() {
        // Reset form state
        document.getElementById('estimate-photos').innerHTML = '';
        document.getElementById('estimate-result').style.display = 'none';
    },

    async capturePhoto() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.capture = 'environment';

        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    this.photos.push({
                        data: event.target.result,
                        name: file.name
                    });
                    this.renderPhotos();
                };
                reader.readAsDataURL(file);
            }
        };

        input.click();
    },

    renderPhotos() {
        const container = document.getElementById('estimate-photos');
        container.innerHTML = this.photos.map((photo, index) => `
            <div class="photo-thumb">
                <img src="${photo.data}" alt="Damage photo ${index + 1}">
                <button class="photo-remove" onclick="EstimateView.removePhoto(${index})">×</button>
            </div>
        `).join('');
    },

    removePhoto(index) {
        this.photos.splice(index, 1);
        this.renderPhotos();
    },

    async generateEstimate() {
        const year = document.getElementById('vehicle-year').value;
        const make = document.getElementById('vehicle-make').value;
        const model = document.getElementById('vehicle-model').value;

        if (!year || !make || !model) {
            UI.showToast('Please enter vehicle information', 'warning');
            return;
        }

        if (this.photos.length === 0) {
            UI.showToast('Please add at least one photo', 'warning');
            return;
        }

        try {
            document.getElementById('estimate-loading').style.display = 'block';

            const result = await API.generateEstimate({
                vehicle_info: { year: parseInt(year), make, model },
                photos: this.photos.map(p => p.data)
            });

            this.currentEstimate = result.estimate;
            this.renderEstimate(result.estimate);

            document.getElementById('estimate-loading').style.display = 'none';
            document.getElementById('estimate-result').style.display = 'block';
        } catch (error) {
            document.getElementById('estimate-loading').style.display = 'none';
            UI.showToast('Failed to generate estimate', 'error');
        }
    },

    renderEstimate(estimate) {
        document.getElementById('estimate-total').textContent = UI.formatCurrency(estimate.pricing?.total || 0);
        document.getElementById('estimate-dents').textContent = estimate.analysis?.dent_count || 0;
        document.getElementById('estimate-severity').textContent = estimate.analysis?.severity || 'Unknown';

        // Render line items
        const itemsContainer = document.getElementById('estimate-items');
        if (estimate.pricing?.line_items) {
            itemsContainer.innerHTML = estimate.pricing.line_items.map(item => `
                <div class="line-item">
                    <span class="item-desc">${item.description}</span>
                    <span class="item-price">${UI.formatCurrency(item.price)}</span>
                </div>
            `).join('');
        }
    },

    async sendEstimate() {
        const email = document.getElementById('customer-email').value;
        if (!email) {
            UI.showToast('Please enter customer email', 'warning');
            return;
        }

        // Create contract with estimate
        try {
            await API.request('/contracts', {
                method: 'POST',
                body: JSON.stringify({
                    estimate: this.currentEstimate,
                    customer_email: email
                })
            });

            UI.showToast('Estimate sent to customer!', 'success');
        } catch (error) {
            UI.showToast('Failed to send estimate', 'error');
        }
    }
};

// ============================================================================
// SCRIPTS VIEW
// ============================================================================
const ScriptsView = {
    scripts: [],

    async load() {
        try {
            const data = await API.getAllScripts();
            this.scripts = data.scripts || [];
            this.render();
        } catch (error) {
            console.error('Failed to load scripts:', error);
        }
    },

    render() {
        const container = document.getElementById('scripts-list');
        if (!container) return;

        const situations = [
            { id: 'DOOR_APPROACH', name: 'Door Approach', icon: '🚪' },
            { id: 'OBJECTION_HANDLING', name: 'Objection Handling', icon: '🤝' },
            { id: 'PRICE_DISCUSSION', name: 'Price Discussion', icon: '💰' },
            { id: 'INSURANCE_EXPLANATION', name: 'Insurance', icon: '📋' },
            { id: 'CLOSING', name: 'Closing', icon: '✅' },
            { id: 'FOLLOW_UP', name: 'Follow Up', icon: '📞' }
        ];

        container.innerHTML = situations.map(situation => `
            <div class="script-card" onclick="ScriptsView.showScript('${situation.id}')">
                <span class="script-icon">${situation.icon}</span>
                <span class="script-name">${situation.name}</span>
                <span class="script-arrow">›</span>
            </div>
        `).join('');
    },

    async showScript(situation) {
        try {
            const data = await API.getScript(situation);
            this.renderScriptDetail(data);
        } catch (error) {
            UI.showToast('Failed to load script', 'error');
        }
    },

    renderScriptDetail(data) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${data.situation}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="script-content">
                        ${data.script.opening ? `
                            <div class="script-section">
                                <h4>Opening</h4>
                                <p class="script-text">"${data.script.opening}"</p>
                            </div>
                        ` : ''}
                        ${data.script.body ? `
                            <div class="script-section">
                                <h4>Key Points</h4>
                                <ul class="script-points">
                                    ${data.script.body.map(point => `<li>${point}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        ${data.script.objections ? `
                            <div class="script-section">
                                <h4>Common Objections</h4>
                                ${Object.entries(data.script.objections).map(([obj, response]) => `
                                    <div class="objection-item">
                                        <div class="objection">"${obj}"</div>
                                        <div class="response">→ "${response}"</div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                        ${data.script.closing ? `
                            <div class="script-section">
                                <h4>Closing</h4>
                                <p class="script-text">"${data.script.closing}"</p>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }
};

// ============================================================================
// LEADERBOARD VIEW
// ============================================================================
const LeaderboardView = {
    period: 'TODAY',

    async load() {
        try {
            const data = await API.getLeaderboard(this.period);
            this.render(data);
        } catch (error) {
            console.error('Failed to load leaderboard:', error);
        }
    },

    render(data) {
        const container = document.getElementById('leaderboard-list');
        if (!container) return;

        const leaderboard = data.leaderboard || [];

        container.innerHTML = leaderboard.map((entry, index) => `
            <div class="leaderboard-entry ${entry.salesperson_id === AppState.salespersonId ? 'is-me' : ''}">
                <div class="rank ${index < 3 ? 'top-' + (index + 1) : ''}">${index + 1}</div>
                <div class="entry-info">
                    <div class="entry-name">${entry.name}</div>
                    <div class="entry-stats">${entry.leads} leads • ${entry.conversions} conversions</div>
                </div>
                <div class="entry-points">${UI.formatNumber(entry.points)} pts</div>
            </div>
        `).join('');
    },

    setPeriod(period) {
        this.period = period;
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.period-btn[data-period="${period}"]`)?.classList.add('active');
        this.load();
    }
};

// ============================================================================
// COMPETITORS VIEW
// ============================================================================
const CompetitorsView = {
    async load() {
        try {
            const data = await API.getCompetitorHeatmap(1, 7);
            this.render(data);
        } catch (error) {
            console.error('Failed to load competitors:', error);
        }
    },

    render(data) {
        document.getElementById('total-sightings').textContent = data.total_sightings || 0;

        const container = document.getElementById('competitor-list');
        if (!container) return;

        const competitors = data.competitors || [];

        if (competitors.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">👁</div>
                    <div class="empty-text">No competitor activity logged</div>
                </div>
            `;
            return;
        }

        container.innerHTML = competitors.map(comp => `
            <div class="competitor-card">
                <div class="competitor-name">${comp.name}</div>
                <div class="competitor-stats">
                    <span>${comp.sightings} sightings</span>
                    <span>Last seen: ${UI.formatDate(comp.last_seen)}</span>
                </div>
            </div>
        `).join('');
    },

    showLogModal() {
        if (AppState.currentPosition) {
            document.getElementById('competitor-lat').value = AppState.currentPosition.latitude;
            document.getElementById('competitor-lon').value = AppState.currentPosition.longitude;
        }
        UI.showModal('competitor-modal');
    },

    async submitLog() {
        const form = document.getElementById('competitor-form');
        const formData = new FormData(form);

        const data = {
            salesperson_id: AppState.salespersonId,
            competitor_name: formData.get('competitor_name'),
            location_lat: parseFloat(formData.get('latitude')) || AppState.currentPosition?.latitude,
            location_lon: parseFloat(formData.get('longitude')) || AppState.currentPosition?.longitude,
            activity_type: formData.get('activity_type'),
            notes: formData.get('notes')
        };

        try {
            await API.logCompetitor(data);
            UI.hideModal('competitor-modal');
            UI.showToast('Competitor logged!', 'success');
            form.reset();
            await this.load();
        } catch (error) {
            UI.showToast('Failed to log competitor', 'error');
        }
    }
};

// ============================================================================
// DNK (Do Not Knock)
// ============================================================================
const DNK = {
    showModal() {
        if (AppState.currentPosition) {
            document.getElementById('dnk-lat').value = AppState.currentPosition.latitude;
            document.getElementById('dnk-lon').value = AppState.currentPosition.longitude;
        }
        UI.showModal('dnk-modal');
    },

    async submit() {
        const form = document.getElementById('dnk-form');
        const formData = new FormData(form);

        const data = {
            address: formData.get('address'),
            latitude: parseFloat(formData.get('latitude')) || AppState.currentPosition?.latitude,
            longitude: parseFloat(formData.get('longitude')) || AppState.currentPosition?.longitude,
            reason: formData.get('reason'),
            notes: formData.get('notes')
        };

        try {
            await API.addDNK(data);
            UI.hideModal('dnk-modal');
            UI.showToast('Added to Do-Not-Knock list', 'success');
            form.reset();
        } catch (error) {
            UI.showToast('Failed to add DNK', 'error');
        }
    },

    async checkLocation(lat, lon) {
        try {
            const data = await API.checkDNK(lat, lon);
            return data.is_dnk;
        } catch (error) {
            return false;
        }
    }
};

// ============================================================================
// GEOLOCATION
// ============================================================================
const Geolocation = {
    init() {
        if ('geolocation' in navigator) {
            this.startWatching();
        } else {
            console.warn('Geolocation not supported');
        }
    },

    startWatching() {
        AppState.watchId = navigator.geolocation.watchPosition(
            (position) => this.onPositionUpdate(position),
            (error) => this.onError(error),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000
            }
        );
    },

    stopWatching() {
        if (AppState.watchId) {
            navigator.geolocation.clearWatch(AppState.watchId);
        }
    },

    onPositionUpdate(position) {
        AppState.currentPosition = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp
        };

        // Check DNK status
        DNK.checkLocation(
            position.coords.latitude,
            position.coords.longitude
        ).then(isDNK => {
            if (isDNK) {
                UI.showToast('⚠️ Do-Not-Knock area', 'warning');
            }
        });
    },

    onError(error) {
        console.error('Geolocation error:', error);
    },

    async getCurrentPosition() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000
            });
        });
    }
};

// ============================================================================
// OFFLINE SUPPORT
// ============================================================================
const OfflineManager = {
    init() {
        window.addEventListener('online', () => this.onOnline());
        window.addEventListener('offline', () => this.onOffline());

        // Load pending sync queue
        const pending = localStorage.getItem('pendingSync');
        if (pending) {
            AppState.pendingSync = JSON.parse(pending);
        }
    },

    onOnline() {
        AppState.isOnline = true;
        document.body.classList.remove('offline');
        UI.showToast('Back online', 'success');
        this.syncPending();
    },

    onOffline() {
        AppState.isOnline = false;
        document.body.classList.add('offline');
        UI.showToast('You are offline', 'warning');
    },

    async syncPending() {
        if (AppState.pendingSync.length === 0) return;

        UI.showToast(`Syncing ${AppState.pendingSync.length} items...`, 'info');

        const failed = [];

        for (const item of AppState.pendingSync) {
            try {
                await API.request(item.endpoint, item.options);
            } catch (error) {
                failed.push(item);
            }
        }

        AppState.pendingSync = failed;
        localStorage.setItem('pendingSync', JSON.stringify(failed));

        if (failed.length === 0) {
            UI.showToast('All data synced!', 'success');
        } else {
            UI.showToast(`${failed.length} items failed to sync`, 'warning');
        }
    }
};

// ============================================================================
// APP INITIALIZATION
// ============================================================================
const App = {
    async init() {
        console.log('Initializing Elite Sales App...');

        // Get salesperson ID from session or local storage
        AppState.salespersonId = this.getSalespersonId();

        // Initialize modules
        Geolocation.init();
        OfflineManager.init();

        // Setup event listeners
        this.setupEventListeners();

        // Load initial view
        UI.showView('dashboard');

        // Perform initial check-in
        await this.checkin();

        // Load cached route if exists
        const cachedRoute = localStorage.getItem('currentRoute');
        if (cachedRoute) {
            AppState.currentRoute = JSON.parse(cachedRoute);
            AppState.routeStopIndex = parseInt(localStorage.getItem('routeStopIndex') || '0');
        }

        console.log('Elite Sales App initialized');
    },

    getSalespersonId() {
        // Try to get from page data or local storage
        const pageData = document.getElementById('app-data');
        if (pageData) {
            const data = JSON.parse(pageData.textContent);
            if (data.salesperson_id) {
                localStorage.setItem('salespersonId', data.salesperson_id);
                return data.salesperson_id;
            }
        }
        return localStorage.getItem('salespersonId') || 1;
    },

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                if (view) UI.showView(view);
            });
        });

        // Menu toggle
        document.getElementById('menu-toggle')?.addEventListener('click', UI.toggleSideMenu);
        document.getElementById('menu-overlay')?.addEventListener('click', UI.toggleSideMenu);

        // Modal close on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) UI.hideModal(modal.id);
            });
        });

        // Quick action buttons
        document.getElementById('btn-quick-lead')?.addEventListener('click', () => LeadsView.showQuickLead());
        document.getElementById('btn-log-competitor')?.addEventListener('click', () => CompetitorsView.showLogModal());
        document.getElementById('btn-mark-dnk')?.addEventListener('click', () => DNK.showModal());

        // Form submissions
        document.getElementById('quick-lead-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            LeadsView.submitQuickLead();
        });

        document.getElementById('competitor-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            CompetitorsView.submitLog();
        });

        document.getElementById('dnk-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            DNK.submit();
        });

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const filter = btn.dataset.filter;
                if (filter) LeadsView.setFilter(filter);
            });
        });

        // Period buttons for leaderboard
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const period = btn.dataset.period;
                if (period) LeaderboardView.setPeriod(period);
            });
        });

        // Estimate actions
        document.getElementById('btn-capture-photo')?.addEventListener('click', () => EstimateView.capturePhoto());
        document.getElementById('btn-generate-estimate')?.addEventListener('click', () => EstimateView.generateEstimate());
        document.getElementById('btn-send-estimate')?.addEventListener('click', () => EstimateView.sendEstimate());
    },

    async checkin() {
        if (!AppState.currentPosition) {
            try {
                const position = await Geolocation.getCurrentPosition();
                AppState.currentPosition = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
            } catch (error) {
                console.warn('Could not get position for checkin');
            }
        }

        try {
            await API.checkin({
                salesperson_id: AppState.salespersonId,
                latitude: AppState.currentPosition?.latitude,
                longitude: AppState.currentPosition?.longitude,
                battery_level: navigator.getBattery ? (await navigator.getBattery()).level * 100 : null,
                app_version: '1.0.0'
            });
        } catch (error) {
            console.warn('Checkin failed:', error);
        }
    }
};

// ============================================================================
// START APP
// ============================================================================
document.addEventListener('DOMContentLoaded', () => App.init());

// Export for debugging
window.EliteSalesApp = {
    AppState,
    API,
    UI,
    Dashboard,
    RouteView,
    LeadsView,
    EstimateView,
    ScriptsView,
    LeaderboardView,
    CompetitorsView,
    DNK,
    Geolocation,
    OfflineManager
};
