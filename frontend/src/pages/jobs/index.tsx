import { useState } from 'react'
import { Briefcase, Calendar, DollarSign, MapPin, Plus, Search } from 'lucide-react'

const mockJobs = [
  { id: 1, title: 'Roof Replacement', customer: 'John Smith', address: '123 Oak St', status: 'in_progress', value: 12500, date: '2024-01-15' },
  { id: 2, title: 'Hail Damage Repair', customer: 'Sarah Johnson', address: '456 Elm Ave', status: 'scheduled', value: 8750, date: '2024-01-20' },
  { id: 3, title: 'Full Roof Install', customer: 'Mike Williams', address: '789 Pine Rd', status: 'completed', value: 18900, date: '2024-01-10' },
  { id: 4, title: 'Insurance Claim Repair', customer: 'Lisa Brown', address: '321 Cedar Ln', status: 'pending', value: 15200, date: '2024-01-25' },
]

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  scheduled: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-purple-100 text-purple-700',
  completed: 'bg-green-100 text-green-700',
}

export function JobsPage() {
  const [searchTerm, setSearchTerm] = useState('')

  const filteredJobs = mockJobs.filter(job =>
    job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.customer.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Jobs</h1>
          <p className="text-muted-foreground">{mockJobs.length} total jobs</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          Create Job
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-3 py-2 border rounded-md bg-background"
          placeholder="Search jobs..."
        />
      </div>

      {/* Jobs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredJobs.map((job) => (
          <div key={job.id} className="bg-card rounded-lg border p-4 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-primary" />
                <span className="font-semibold">{job.title}</span>
              </div>
              <span className={`px-2 py-1 text-xs rounded-full capitalize ${statusColors[job.status]}`}>
                {job.status.replace('_', ' ')}
              </span>
            </div>
            <p className="text-sm font-medium mb-2">{job.customer}</p>
            <div className="space-y-1 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <MapPin className="h-3 w-3" />
                {job.address}
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="h-3 w-3" />
                {job.date}
              </div>
              <div className="flex items-center gap-2">
                <DollarSign className="h-3 w-3" />
                ${job.value.toLocaleString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
