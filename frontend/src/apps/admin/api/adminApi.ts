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

  // ============ Dashboard ============

  async getDashboard() {
    return this.request('/admin/dashboard');
  }

  // ============ Customers ============

  async getCustomers(status?: string) {
    const params = status ? `?status=${status}` : '';
    return this.request(`/admin/customers${params}`);
  }

  async getCustomer(id: number) {
    return this.request(`/admin/customers/${id}`);
  }

  async createCustomer(data: {
    company_name: string;
    owner_name: string;
    owner_email: string;
    password: string;
    plan?: string;
  }) {
    return this.request('/admin/customers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCustomer(id: number, data: { status?: string; plan?: string; max_users?: number }) {
    return this.request(`/admin/customers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async suspendCustomer(id: number) {
    return this.updateCustomer(id, { status: 'suspended' });
  }

  async activateCustomer(id: number) {
    return this.updateCustomer(id, { status: 'active' });
  }

  async getCustomerStats() {
    return this.request('/admin/customers/stats');
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

  async getApiUsage() {
    return this.request('/admin/usage');
  }
}

export const adminApi = new AdminApi();
export default adminApi;
