import { useState } from 'react'
import { Phone, Mail, Plus, Search, Briefcase } from 'lucide-react'

const mockCustomers = [
  { id: 1, name: 'John Smith', email: 'john@email.com', phone: '555-0101', address: '123 Oak St, Dallas, TX', jobsCount: 2, totalSpent: 25400 },
  { id: 2, name: 'Sarah Johnson', email: 'sarah@email.com', phone: '555-0102', address: '456 Elm Ave, Plano, TX', jobsCount: 1, totalSpent: 8750 },
  { id: 3, name: 'Mike Williams', email: 'mike@email.com', phone: '555-0103', address: '789 Pine Rd, Frisco, TX', jobsCount: 3, totalSpent: 42100 },
  { id: 4, name: 'Lisa Brown', email: 'lisa@email.com', phone: '555-0104', address: '321 Cedar Ln, McKinney, TX', jobsCount: 1, totalSpent: 15200 },
]

export function CustomersPage() {
  const [searchTerm, setSearchTerm] = useState('')

  const filteredCustomers = mockCustomers.filter(customer =>
    customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    customer.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Customers</h1>
          <p className="text-muted-foreground">{mockCustomers.length} total customers</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          Add Customer
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
          placeholder="Search customers..."
        />
      </div>

      {/* Customers Table */}
      <div className="bg-card rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Customer</th>
              <th className="text-left p-4 font-medium">Contact</th>
              <th className="text-left p-4 font-medium">Address</th>
              <th className="text-left p-4 font-medium">Jobs</th>
              <th className="text-left p-4 font-medium">Total Spent</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filteredCustomers.map((customer) => (
              <tr key={customer.id} className="hover:bg-accent/50 cursor-pointer">
                <td className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <span className="text-primary font-medium">{customer.name.charAt(0)}</span>
                    </div>
                    <span className="font-medium">{customer.name}</span>
                  </div>
                </td>
                <td className="p-4">
                  <div className="text-sm">
                    <div className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {customer.email}
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      {customer.phone}
                    </div>
                  </div>
                </td>
                <td className="p-4 text-sm">{customer.address}</td>
                <td className="p-4">
                  <div className="flex items-center gap-1">
                    <Briefcase className="h-4 w-4 text-muted-foreground" />
                    {customer.jobsCount}
                  </div>
                </td>
                <td className="p-4 font-medium">${customer.totalSpent.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
