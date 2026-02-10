/**
 * Customer Picker Component
 * Search and select customer for estimate
 */

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, User, Plus, Loader2 } from 'lucide-react'
import { useCustomers } from '@/hooks/use-customers'
import { Customer } from '@/types'

interface CustomerPickerProps {
  open: boolean
  onClose: () => void
  onSelectCustomer: (customer: Customer) => void
  onCreateNew?: () => void
  selectedCustomerId?: number | null
}

export function CustomerPicker({
  open,
  onClose,
  onSelectCustomer,
  onCreateNew,
  selectedCustomerId
}: CustomerPickerProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const { customers, loading } = useCustomers({ search: searchTerm })

  // Clear search when dialog opens
  useEffect(() => {
    if (open) {
      setSearchTerm('')
    }
  }, [open])

  const handleSelect = (customer: Customer) => {
    onSelectCustomer(customer)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Customer</DialogTitle>
        </DialogHeader>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search customers..."
            className="pl-10"
            autoFocus
          />
        </div>

        {/* Customer List */}
        <div className="flex-1 overflow-auto min-h-[200px] max-h-[400px]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : customers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? 'No customers found' : 'No customers yet'}
            </div>
          ) : (
            <div className="space-y-1">
              {customers.map((customer) => (
                <button
                  key={customer.id}
                  onClick={() => handleSelect(customer)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selectedCustomerId === customer.id
                      ? 'border-primary bg-primary/5'
                      : 'border-transparent hover:bg-accent'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">
                        {customer.first_name} {customer.last_name}
                      </p>
                      {customer.company_name && (
                        <p className="text-sm text-muted-foreground truncate">
                          {customer.company_name}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        {customer.phone}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Create New Button */}
        {onCreateNew && (
          <div className="pt-2 border-t">
            <Button
              variant="outline"
              className="w-full"
              onClick={onCreateNew}
            >
              <Plus className="h-4 w-4 mr-2" />
              Create New Customer
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default CustomerPicker
