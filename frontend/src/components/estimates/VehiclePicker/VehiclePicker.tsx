/**
 * Vehicle Picker Component
 * Select existing vehicle or add new for estimate
 */

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Car, Plus, Loader2, Search } from 'lucide-react'
import { useVehicles } from '@/hooks/use-vehicles'
import { Vehicle } from '@/types'

interface VehiclePickerProps {
  open: boolean
  onClose: () => void
  customerId: number | null
  onSelectVehicle: (vehicle: Vehicle) => void
  onAddNew: () => void
  selectedVehicleId?: number | null
}

export function VehiclePicker({
  open,
  onClose,
  customerId,
  onSelectVehicle,
  onAddNew,
  selectedVehicleId
}: VehiclePickerProps) {
  const [searchTerm, setSearchTerm] = useState('')

  // Fetch customer's vehicles
  const { vehicles, loading } = useVehicles(
    customerId ? { customer_id: customerId } : {}
  )

  // Filter vehicles by search term
  const filteredVehicles = searchTerm
    ? vehicles.filter(v =>
        `${v.year} ${v.make} ${v.model}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.vin?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : vehicles

  // Clear search when dialog opens
  useEffect(() => {
    if (open) {
      setSearchTerm('')
    }
  }, [open])

  const handleSelect = (vehicle: Vehicle) => {
    onSelectVehicle(vehicle)
    onClose()
  }

  const handleAddNew = () => {
    onAddNew()
    onClose()
  }

  // Don't show if no customer selected
  if (!customerId) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Select Vehicle</DialogTitle>
          </DialogHeader>
          <div className="text-center py-8">
            <Car className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-4">
              Please select a customer first before choosing a vehicle.
            </p>
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Vehicle</DialogTitle>
        </DialogHeader>

        {/* Search (only show if there are vehicles) */}
        {vehicles.length > 3 && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search vehicles..."
              className="w-full pl-10 pr-3 py-2 border rounded-md bg-background"
            />
          </div>
        )}

        {/* Vehicle List */}
        <div className="flex-1 overflow-auto min-h-[150px] max-h-[300px]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filteredVehicles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? 'No vehicles match your search' : 'No vehicles on record for this customer'}
            </div>
          ) : (
            <div className="space-y-1">
              {filteredVehicles.map((vehicle) => (
                <button
                  key={vehicle.id}
                  onClick={() => handleSelect(vehicle)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selectedVehicleId === vehicle.id
                      ? 'border-primary bg-primary/5'
                      : 'border-transparent hover:bg-accent'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Car className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">
                        {vehicle.year} {vehicle.make} {vehicle.model}
                      </p>
                      {vehicle.vin && (
                        <p className="text-sm text-muted-foreground font-mono truncate">
                          VIN: {vehicle.vin}
                        </p>
                      )}
                      {vehicle.color && (
                        <p className="text-sm text-muted-foreground">
                          {vehicle.color}
                        </p>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Add New Vehicle Button */}
        <div className="pt-2 border-t">
          <Button
            variant="outline"
            className="w-full"
            onClick={handleAddNew}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add New Vehicle
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default VehiclePicker
