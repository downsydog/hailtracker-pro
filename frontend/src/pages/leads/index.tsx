import { useState } from 'react'
import { Users, Phone, Mail, Plus, Search } from 'lucide-react'

const mockLeads = [
  { id: 1, name: 'John Smith', email: 'john@email.com', phone: '555-0101', address: '123 Oak St, Dallas, TX', status: 'new', source: 'Hail Event' },
  { id: 2, name: 'Sarah Johnson', email: 'sarah@email.com', phone: '555-0102', address: '456 Elm Ave, Plano, TX', status: 'contacted', source: 'Referral' },
  { id: 3, name: 'Mike Williams', email: 'mike@email.com', phone: '555-0103', address: '789 Pine Rd, Frisco, TX', status: 'qualified', source: 'Website' },
  { id: 4, name: 'Lisa Brown', email: 'lisa@email.com', phone: '555-0104', address: '321 Cedar Ln, McKinney, TX', status: 'proposal', source: 'Hail Event' },
]

const statusColors: Record<string, string> = {
  new: 'bg-blue-100 text-blue-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  qualified: 'bg-purple-100 text-purple-700',
  proposal: 'bg-green-100 text-green-700',
}

export function LeadsPage() {
  const [searchTerm, setSearchTerm] = useState('')

  const filteredLeads = mockLeads.filter(lead =>
    lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.address.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Leads</h1>
          <p className="text-muted-foreground">{mockLeads.length} total leads</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          Add Lead
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
          placeholder="Search leads..."
        />
      </div>

      {/* Leads Table */}
      <div className="bg-card rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Name</th>
              <th className="text-left p-4 font-medium">Contact</th>
              <th className="text-left p-4 font-medium">Address</th>
              <th className="text-left p-4 font-medium">Source</th>
              <th className="text-left p-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filteredLeads.map((lead) => (
              <tr key={lead.id} className="hover:bg-accent/50 cursor-pointer">
                <td className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Users className="h-4 w-4 text-primary" />
                    </div>
                    <span className="font-medium">{lead.name}</span>
                  </div>
                </td>
                <td className="p-4">
                  <div className="text-sm">
                    <div className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {lead.email}
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      {lead.phone}
                    </div>
                  </div>
                </td>
                <td className="p-4 text-sm">{lead.address}</td>
                <td className="p-4 text-sm">{lead.source}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 text-xs rounded-full capitalize ${statusColors[lead.status]}`}>
                    {lead.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
