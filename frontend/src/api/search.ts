import { apiClient, ApiParams } from './client'

// Define SearchResult here for components that import from this module
export interface SearchResult {
  id: number
  type: string
  title: string
  subtitle?: string
  url: string
}

export interface GlobalSearchParams {
  query: string
  types?: string[]
  limit?: number
}

export interface GlobalSearchResponse {
  results: SearchResult[]
  total: number
  query: string
}

export async function globalSearch(params: GlobalSearchParams): Promise<GlobalSearchResponse> {
  return apiClient.get<GlobalSearchResponse>('/search', params as unknown as ApiParams)
}

export async function searchCustomers(query: string, limit = 10): Promise<SearchResult[]> {
  const response = await apiClient.get<GlobalSearchResponse>('/search', {
    query,
    types: ['customer'],
    limit
  } as unknown as ApiParams)
  return response.results
}

export async function searchJobs(query: string, limit = 10): Promise<SearchResult[]> {
  const response = await apiClient.get<GlobalSearchResponse>('/search', {
    query,
    types: ['job'],
    limit
  } as unknown as ApiParams)
  return response.results
}

export async function searchVehicles(query: string, limit = 10): Promise<SearchResult[]> {
  const response = await apiClient.get<GlobalSearchResponse>('/search', {
    query,
    types: ['vehicle'],
    limit
  } as unknown as ApiParams)
  return response.results
}

export const searchApi = {
  globalSearch,
  searchCustomers,
  searchJobs,
  searchVehicles
}

export default searchApi
