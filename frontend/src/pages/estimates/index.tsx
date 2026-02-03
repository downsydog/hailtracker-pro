import { useState } from 'react'
import { FileText, Plus, Search } from 'lucide-react'

const mockEstimates = [
  { id: 1, number: 'EST-001', customer: 'John Smith', total: 12500, status: 'approved', date: '2024-01-15' },
  { id: 2, number: 'EST-002', customer: 'Sarah Johnson', total: 8750, status: 'pending', date: '2024-01-18' },
  { id: 3, number: 'EST-003', customer: 'Mike Williams', total: 18900, status: 'approved', date: '2024-01-12' },
  { id: 4, number: 'EST-004', customer: 'Lisa Brown', total: 15200, status: 'rejected', date: '2024-01-20' },
  { id: 5, number: 'EST-005', customer: 'Tom Davis', total: 9800, status: 'draft', date: '2024-01-22' },
]

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
}

export function EstimatesPage() {
  const [searchTerm, setSearchTerm] = useState('')

  const filteredEstimates = mockEstimates.filter(est =>
    est.number.toLowerCase().includes(searchTerm.toLowerCase()) ||
    est.customer.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Estimates</h1>
          <p className="text-muted-foreground">{mockEstimates.length} total estimates</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          New Estimate
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Total Value</p>
          <p className="text-2xl font-bold">${mockEstimates.reduce((sum, e) => sum + e.total, 0).toLocaleString()}</p>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Approved</p>
          <p className="text-2xl font-bold text-green-600">{mockEstimates.filter(e => e.status === 'approved').length}</p>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Pending</p>
          <p className="text-2xl font-bold text-yellow-600">{mockEstimates.filter(e => e.status === 'pending').length}</p>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">Rejected</p>
          <p className="text-2xl font-bold text-red-600">{mockEstimates.filter(e => e.status === 'rejected').length}</p>
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
          placeholder="Search estimates..."
        />
      </div>

      {/* Estimates Table */}
      <div className="bg-card rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Estimate #</th>
              <th className="text-left p-4 font-medium">Customer</th>
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
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <span className="font-medium">{estimate.number}</span>
                  </div>
                </td>
                <td className="p-4">{estimate.customer}</td>
                <td className="p-4 text-sm text-muted-foreground">{estimate.date}</td>
                <td className="p-4 font-medium">${estimate.total.toLocaleString()}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 text-xs rounded-full capitalize ${statusColors[estimate.status]}`}>
                    {estimate.status}
                  </span>
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    <button className="p-1 hover:bg-accent rounded">
                      <FileText className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
