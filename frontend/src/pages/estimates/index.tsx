import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Plus, Search, Loader2, Receipt } from 'lucide-react'
import { usePDREstimates, useConvertToInvoice } from '@/hooks/use-pdr-estimates'
import { Button } from '@/components/ui/button'

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  completed: 'bg-emerald-100 text-emerald-700',
}

export function EstimatesPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [convertingId, setConvertingId] = useState<number | null>(null)
  const navigate = useNavigate()
  const convertToInvoice = useConvertToInvoice()

  // Fetch real estimates from API
  const { data, isLoading, error } = usePDREstimates(
    searchTerm ? { search: searchTerm } : undefined
  )

  const estimates = data?.estimates || []
  const total = data?.total || 0

  // Calculate stats
  const stats = {
    totalValue: estimates.reduce((sum, e) => sum + (e.total_price || 0), 0),
    approved: estimates.filter(e => e.status === 'approved').length,
    pending: estimates.filter(e => e.status === 'in_progress' || e.status === 'draft').length,
    completed: estimates.filter(e => e.status === 'completed').length,
  }

  // Filter estimates by search term
  const filteredEstimates = searchTerm
    ? estimates.filter(est =>
        est.estimate_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        est.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        `${est.vehicle_year} ${est.vehicle_make} ${est.vehicle_model}`.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : estimates

  // Handle convert to invoice
  const handleConvertToInvoice = async (estimateId: number) => {
    setConvertingId(estimateId)
    try {
      const result = await convertToInvoice.mutateAsync(estimateId)
      if (result.invoice_id) {
        navigate(`/invoices/${result.invoice_id}`)
      } else {
        navigate('/invoices')
      }
    } catch (error) {
      console.error('Convert to invoice failed:', error)
      // Navigate to invoices anyway
      navigate('/invoices')
    } finally {
      setConvertingId(null)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Estimates</h1>
          <p className="text-muted-foreground">{total} total estimates</p>
        </div>
        <Button onClick={() => navigate('/estimates/new')}>
          <Plus className="h-4 w-4 mr-2" />
          New Estimate
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Total Value</p>
          <p className="text-2xl font-bold">${stats.totalValue.toLocaleString()}</p>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Approved</p>
          <p className="text-2xl font-bold text-green-600">{stats.approved}</p>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Pending</p>
          <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Completed</p>
          <p className="text-2xl font-bold text-emerald-600">{stats.completed}</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-3 py-2 border rounded-md bg-background"
          placeholder="Search by estimate number, customer, or vehicle..."
        />
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-destructive/10 text-destructive rounded-lg p-4 mb-4">
          Failed to load estimates. Please try again.
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredEstimates.length === 0 && (
        <div className="text-center py-12 bg-card rounded-lg border">
          <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No estimates found</h3>
          <p className="text-muted-foreground mb-4">
            {searchTerm ? 'Try a different search term' : 'Create your first estimate to get started'}
          </p>
          {!searchTerm && (
            <Button onClick={() => navigate('/estimates/new')}>
              <Plus className="h-4 w-4 mr-2" />
              New Estimate
            </Button>
          )}
        </div>
      )}

      {/* Estimates Table */}
      {!isLoading && !error && filteredEstimates.length > 0 && (
        <div className="bg-card rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-4 font-medium">Estimate #</th>
                <th className="text-left p-4 font-medium">Customer</th>
                <th className="text-left p-4 font-medium">Vehicle</th>
                <th className="text-left p-4 font-medium">Date</th>
                <th className="text-left p-4 font-medium">Total</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredEstimates.map((estimate) => (
                <tr key={estimate.id} className="hover:bg-accent/50">
                  <td className="p-4">
                    <Link
                      to={`/estimates/${estimate.id}`}
                      className="flex items-center gap-2 hover:text-primary"
                    >
                      <FileText className="h-4 w-4 text-primary" />
                      <span className="font-medium">{estimate.estimate_number || `EST-${estimate.id}`}</span>
                    </Link>
                  </td>
                  <td className="p-4">
                    {estimate.customer_name || 'No customer'}
                  </td>
                  <td className="p-4 text-sm text-muted-foreground">
                    {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                  </td>
                  <td className="p-4 text-sm text-muted-foreground">
                    {estimate.created_at ? new Date(estimate.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="p-4 font-medium">
                    ${(estimate.total_price || 0).toLocaleString()}
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-1 text-xs rounded-full capitalize ${statusColors[estimate.status] || statusColors.draft}`}>
                      {estimate.status?.replace('_', ' ') || 'draft'}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/estimates/${estimate.id}`}
                        className="p-1 hover:bg-accent rounded"
                        title="View/Edit"
                      >
                        <FileText className="h-4 w-4" />
                      </Link>
                      {estimate.status === 'approved' && (
                        <button
                          onClick={() => handleConvertToInvoice(estimate.id)}
                          disabled={convertingId === estimate.id}
                          className="p-1 hover:bg-accent rounded text-green-600 disabled:opacity-50"
                          title="Convert to Invoice"
                        >
                          {convertingId === estimate.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Receipt className="h-4 w-4" />
                          )}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
