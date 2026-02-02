import { apiGet } from './client'
import { SearchResult } from '@/types'

export type { SearchResult }

interface SearchResults {
  results: SearchResult[]
}

export const searchApi = {
  search: (query: string) => apiGet<SearchResults>('/api/search', { params: { q: query } }),
}
