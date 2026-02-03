import { apiClient } from './client'

export interface Part {
  id: number
  name: string
  part_number: string
  description?: string
  category: string
  quantity: number
  in_stock?: number
  unit_price: number
  retail_price?: number
  supplier_id?: number
  supplier_name?: string
  min_quantity: number
  reorder_level?: number
  location?: string
  is_active: boolean
  [key: string]: unknown  // Allow additional properties
}

export interface PartOrder {
  id: number
  order_number: string
  supplier_id: number
  supplier_name: string
  status: 'pending' | 'ordered' | 'shipped' | 'received' | 'cancelled'
  total: number
  items: PartOrderItem[]
  order_date: string
  expected_delivery?: string
  received_date?: string
  notes?: string
  job_number?: string
  job_id?: number
  actual_amount?: number
  quote_amount?: number
  created_at?: string
}

export interface PartOrderItem {
  id: number
  part_id: number
  part_name: string
  part_number: string
  quantity: number
  unit_price: number
  total: number
}

export interface Supplier {
  id: number
  name: string
  contact_name?: string
  email?: string
  phone?: string
  address?: string
  is_active: boolean
}

export interface PartsStats {
  total_parts: number
  total_inventory_value: number
  low_stock_count: number
  out_of_stock_count: number
}

export interface PartsCategory {
  id: number
  name: string
  parts_count: number
}

export const partsApi = {
  // Parts Inventory
  getParts: (params?: { category?: string; search?: string; page?: number; per_page?: number }) =>
    apiClient.get<{ parts: Part[]; total: number; pages?: number }>('/parts', params),

  getCategories: () =>
    apiClient.get<{ categories: PartsCategory[] }>('/parts/categories'),

  getStats: () =>
    apiClient.get<PartsStats>('/parts/stats'),

  getLowStock: () =>
    apiClient.get<{ parts: Part[] }>('/parts/low-stock'),

  getPart: (id: number) =>
    apiClient.get<Part>(`/parts/${id}`),

  createPart: (data: Partial<Part>) =>
    apiClient.post<Part>('/parts', data),

  updatePart: (id: number, data: Partial<Part>) =>
    apiClient.patch<Part>(`/parts/${id}`, data),

  deletePart: (id: number) =>
    apiClient.delete(`/parts/${id}`),

  adjustQuantity: (id: number, quantity: number, reason: string) =>
    apiClient.post(`/parts/${id}/adjust`, { quantity, reason }),

  // Orders
  getOrders: (params?: { status?: string; page?: number; per_page?: number }) =>
    apiClient.get<{ orders: PartOrder[]; total: number }>('/parts/orders', params),

  getOrder: (id: number) =>
    apiClient.get<PartOrder>(`/parts/orders/${id}`),

  createOrder: (data: { supplier_id?: number; supplier_name?: string; supplier_email?: string; supplier_phone?: string; notes?: string; items?: Array<{ part_id: number; quantity: number }> }) =>
    apiClient.post<PartOrder>('/parts/orders', data),

  updateOrderStatus: (id: number, status: string) =>
    apiClient.patch(`/parts/orders/${id}/status`, { status }),

  receiveOrder: (id: number, items: Array<{ part_id: number; quantity_received: number }>) =>
    apiClient.post(`/parts/orders/${id}/receive`, { items }),

  // Suppliers
  getSuppliers: () =>
    apiClient.get<{ suppliers: Supplier[] }>('/parts/suppliers'),

  createSupplier: (data: Partial<Supplier>) =>
    apiClient.post<Supplier>('/parts/suppliers', data),

  updateSupplier: (id: number, data: Partial<Supplier>) =>
    apiClient.patch<Supplier>(`/parts/suppliers/${id}`, data),

  // Low stock alerts
  getLowStockParts: () =>
    apiClient.get<{ parts: Part[] }>('/parts/low-stock'),
}

export default partsApi
