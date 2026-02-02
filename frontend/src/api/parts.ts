/**
 * Parts API Client
 * Parts catalog, inventory, job parts, and ordering
 */

import { apiGet, apiPost, apiPut, apiDelete } from './client'

// =============================================================================
// TYPES
// =============================================================================

export interface Part {
  id: number
  part_number: string
  description: string
  category: string
  preferred_supplier?: string
  supplier_part_number?: string
  cost?: number
  retail_price?: number
  in_stock: number
  reorder_level: number
  created_at: string
  updated_at?: string
}

export interface PartInput {
  part_number?: string
  description: string
  category?: string
  preferred_supplier?: string
  supplier_part_number?: string
  cost?: number
  retail_price?: number
  in_stock?: number
  reorder_level?: number
}

export interface JobPart {
  id: number
  job_id: number
  part_id: number
  part_number?: string
  description?: string
  category?: string
  quantity: number
  price: number
  total: number
  notes?: string
  created_at: string
  updated_at?: string
}

export interface PartOrder {
  id: number
  order_number: string
  supplier_name: string
  supplier_email?: string
  supplier_phone?: string
  job_id?: number
  job_number?: string
  status: 'PENDING' | 'QUOTED' | 'ORDERED' | 'SHIPPED' | 'RECEIVED' | 'CANCELLED'
  parts_json?: string
  parts_list?: PartOrderItem[]
  quote_amount?: number
  actual_amount?: number
  expected_delivery_date?: string
  actual_delivery_date?: string
  return_cost?: number
  notes?: string
  created_at: string
  updated_at?: string
}

export interface PartOrderItem {
  part_id: number
  part_number?: string
  description: string
  quantity: number
  price?: number
}

export interface PartOrderQuote {
  id: number
  order_id: number
  supplier_name: string
  quoted_price: number
  quoted_delivery_days?: number
  return_policy?: string
  core_charge?: number
  expires_date?: string
  is_selected: boolean
  created_at: string
}

export interface SupplierPerformance {
  supplier_name: string
  total_orders: number
  on_time_rate: number
  avg_price_variance: number
  return_rate: number
  avg_delivery_days: number
}

export interface PartsStats {
  total_parts: number
  low_stock_count: number
  out_of_stock_count: number
  total_inventory_value: number
  pending_orders: number
}

// =============================================================================
// PARTS CATALOG API
// =============================================================================

export const partsApi = {
  // List parts with filters and pagination
  getParts: (params?: {
    search?: string
    category?: string
    needs_reorder?: boolean
    page?: number
    per_page?: number
  }) =>
    apiGet<{
      parts: Part[]
      total: number
      page: number
      per_page: number
      pages: number
    }>('/api/parts', { params }),

  // Get single part
  getPart: (id: number) =>
    apiGet<{ part: Part }>(`/api/parts/${id}`),

  // Create new part
  createPart: (data: PartInput) =>
    apiPost<{ success: boolean; part_id: number; message: string }>('/api/parts', data),

  // Update part
  updatePart: (id: number, data: Partial<PartInput>) =>
    apiPut<{ success: boolean; message: string }>(`/api/parts/${id}`, data),

  // Delete part
  deletePart: (id: number) =>
    apiDelete<{ success: boolean; message: string }>(`/api/parts/${id}`),

  // Search parts
  searchParts: (query: string, limit?: number) =>
    apiGet<{ parts: Part[] }>('/api/parts/search', { params: { q: query, limit } }),

  // Get low stock parts
  getLowStock: () =>
    apiGet<{ parts: Part[]; count: number }>('/api/parts/low-stock'),

  // Get parts statistics
  getStats: () =>
    apiGet<PartsStats>('/api/parts/stats'),

  // Get part categories
  getCategories: () =>
    apiGet<{ categories: string[] }>('/api/parts/categories'),

  // Update inventory level
  updateInventory: (partId: number, quantityChange: number, notes?: string) =>
    apiPost<{ success: boolean; new_stock: number; message: string }>(
      `/api/parts/${partId}/inventory`,
      { quantity_change: quantityChange, notes }
    ),

  // ==========================================================================
  // JOB PARTS
  // ==========================================================================

  // Get parts for a job
  getJobParts: (jobId: number) =>
    apiGet<{ parts: JobPart[]; count: number; total: number }>(
      `/api/parts/jobs/${jobId}/parts`
    ),

  // Add part to job
  addPartToJob: (
    jobId: number,
    data: { part_id: number; quantity: number; price?: number; notes?: string }
  ) =>
    apiPost<{ success: boolean; job_part_id: number; message: string }>(
      `/api/parts/jobs/${jobId}/parts`,
      data
    ),

  // Update job part
  updateJobPart: (
    jobId: number,
    jobPartId: number,
    data: { quantity?: number; price?: number; notes?: string }
  ) =>
    apiPut<{ success: boolean; message: string }>(
      `/api/parts/jobs/${jobId}/parts/${jobPartId}`,
      data
    ),

  // Remove part from job
  removePartFromJob: (jobId: number, jobPartId: number) =>
    apiDelete<{ success: boolean; message: string }>(
      `/api/parts/jobs/${jobId}/parts/${jobPartId}`
    ),

  // ==========================================================================
  // PART ORDERS
  // ==========================================================================

  // List orders
  getOrders: (params?: { status?: string; job_id?: number; page?: number; per_page?: number }) =>
    apiGet<{
      orders: PartOrder[]
      total: number
      page: number
      per_page: number
    }>('/api/parts/orders', { params }),

  // Get order detail
  getOrder: (orderId: number) =>
    apiGet<{ order: PartOrder & { quotes: PartOrderQuote[] } }>(`/api/parts/orders/${orderId}`),

  // Create order
  createOrder: (data: {
    supplier_name: string
    job_id?: number
    parts?: PartOrderItem[]
    supplier_email?: string
    supplier_phone?: string
    notes?: string
  }) =>
    apiPost<{ success: boolean; order_id: number; order_number: string; message: string }>(
      '/api/parts/orders',
      data
    ),

  // Update order status
  updateOrderStatus: (
    orderId: number,
    data: {
      status: string
      quote_amount?: number
      actual_amount?: number
      expected_delivery_date?: string
      actual_delivery_date?: string
      return_cost?: number
      notes?: string
    }
  ) =>
    apiPut<{ success: boolean; message: string }>(`/api/parts/orders/${orderId}/status`, data),

  // Get order quotes
  getOrderQuotes: (orderId: number) =>
    apiGet<{ quotes: PartOrderQuote[] }>(`/api/parts/orders/${orderId}/quotes`),

  // Add quote to order
  addQuote: (
    orderId: number,
    data: {
      supplier_name: string
      quoted_price: number
      quoted_delivery_days?: number
      return_policy?: string
      core_charge?: number
      expires_date?: string
    }
  ) =>
    apiPost<{ success: boolean; quote_id: number; message: string }>(
      `/api/parts/orders/${orderId}/quotes`,
      data
    ),

  // Select a quote
  selectQuote: (orderId: number, quoteId: number) =>
    apiPost<{ success: boolean; message: string }>(
      `/api/parts/orders/${orderId}/quotes/${quoteId}/select`
    ),

  // ==========================================================================
  // SUPPLIERS
  // ==========================================================================

  // Get suppliers with performance data
  getSuppliers: () =>
    apiGet<{ suppliers: SupplierPerformance[] }>('/api/parts/suppliers'),
}

export default partsApi
