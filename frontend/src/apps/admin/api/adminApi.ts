/**
 * Admin Portal API Client
 * =======================
 * API client for the admin control panel.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

class AdminApi {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('admin_token', token);
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('admin_token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('admin_token');
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const token = this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/admin/login';
      throw new Error('Unauthorized');
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Request failed');
    }

    return data;
  }

  // ============ Auth ============

  async login(email: string, password: string) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (data.access_token) {
      this.setToken(data.access_token);
    }

    return data;
  }

  async getMe() {
    return this.request('/auth/me');
  }

  logout() {
    this.clearToken();
  }

  // ============ Dashboard / Stats ============

  async getDashboard() {
    // Use the new /admin/stats endpoint
    return this.request('/admin/stats');
  }

  async getStats() {
    return this.request('/admin/stats');
  }

  // ============ Tenants ============

  async getTenants() {
    return this.request('/admin/tenants');
  }

  async getTenant(id: number) {
    return this.request(`/admin/tenants/${id}`);
  }

  async createTenant(data: {
    company_name: string;
    owner_email: string;
    plan?: string;
    max_users?: number;
  }) {
    return this.request('/admin/tenants', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTenant(id: number, data: { company_name?: string; plan?: string; status?: string; max_users?: number }) {
    return this.request(`/admin/tenants/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async suspendTenant(id: number) {
    return this.updateTenant(id, { status: 'suspended' });
  }

  async activateTenant(id: number) {
    return this.updateTenant(id, { status: 'active' });
  }

  // ============ Users ============

  async getUsers(tenantId?: number) {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    return this.request(`/admin/users${params}`);
  }

  async getUser(id: number) {
    return this.request(`/admin/users/${id}`);
  }

  async createUser(data: {
    email: string;
    password: string;
    name: string;
    tenant_id: number;
    role?: string;
    phone?: string;
  }) {
    return this.request('/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(id: number, data: { name?: string; role?: string; is_active?: boolean; tenant_id?: number }) {
    return this.request(`/admin/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Legacy aliases for backwards compatibility
  async getCustomers(_status?: string) {
    // Redirect to tenants (status filter not used in new API)
    return this.getTenants();
  }

  async getCustomer(id: number) {
    return this.getTenant(id);
  }

  async createCustomer(data: {
    company_name: string;
    owner_name: string;
    owner_email: string;
    password: string;
    plan?: string;
  }) {
    return this.createTenant({
      company_name: data.company_name,
      owner_email: data.owner_email,
      plan: data.plan,
    });
  }

  async updateCustomer(id: number, data: { status?: string; plan?: string; max_users?: number }) {
    return this.updateTenant(id, data);
  }

  async suspendCustomer(id: number) {
    return this.suspendTenant(id);
  }

  async activateCustomer(id: number) {
    return this.activateTenant(id);
  }

  async getCustomerStats() {
    return this.getStats();
  }

  // ============ Storms ============

  async getStorms(status?: string, limit: number = 50) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());
    return this.request(`/admin/storms?${params}`);
  }

  async getPendingStorms() {
    return this.request('/admin/storms/pending');
  }

  async getStormStats() {
    return this.request('/admin/storms/stats');
  }

  async processStorm(stormId: number, force: boolean = false) {
    return this.request(`/admin/storms/${stormId}/process`, {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
  }

  async reprocessStorm(stormId: number) {
    return this.request(`/admin/storms/${stormId}/reprocess`, {
      method: 'POST',
    });
  }

  async processBatch(stormIds: number[]) {
    return this.request('/admin/storms/process-batch', {
      method: 'POST',
      body: JSON.stringify({ storm_ids: stormIds }),
    });
  }

  async getTaskStatus(taskId: string) {
    return this.request(`/admin/tasks/${taskId}`);
  }

  // ============ API Usage ============

  async getApiUsage(days: number = 30, tenantId?: number) {
    const params = new URLSearchParams();
    params.append('days', days.toString());
    if (tenantId) params.append('tenant_id', tenantId.toString());
    return this.request(`/admin/api-usage?${params}`);
  }
}

export const adminApi = new AdminApi();
export default adminApi;
