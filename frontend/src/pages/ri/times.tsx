import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { riApi, RITime } from '@/api/ri'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ArrowLeft,
  Search,
  Clock,
  AlertCircle,
  CheckCircle,
  Send,
} from 'lucide-react'

// Common vehicle makes for selection
const MAKES = [
  'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler',
  'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jeep',
  'Kia', 'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'Nissan',
  'Ram', 'Subaru', 'Tesla', 'Toyota', 'Volkswagen', 'Volvo',
]

// Generate years from current year back to 1990
const YEARS = Array.from({ length: 37 }, (_, i) => new Date().getFullYear() - i)

export function RITimesPage() {
  const [year, setYear] = React.useState<string>('')
  const [make, setMake] = React.useState<string>('')
  const [model, setModel] = React.useState<string>('')
  const [hasSearched, setHasSearched] = React.useState(false)
  const [showCorrectionDialog, setShowCorrectionDialog] = React.useState(false)
  const [selectedTime, setSelectedTime] = React.useState<RITime | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['ri-times', { year, make, model }],
    queryFn: () => riApi.getTimes({
      year: year ? parseInt(year) : undefined,
      make: make || undefined,
      model: model || undefined,
    }),
    enabled: hasSearched && !!(year && make && model),
  })

  const correctionMutation = useMutation({
    mutationFn: riApi.submitTimeCorrection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ri-times'] })
      setShowCorrectionDialog(false)
      setSelectedTime(null)
    },
  })

  const handleSearch = () => {
    if (year && make && model) {
      setHasSearched(true)
      refetch()
    }
  }

  const handleSubmitCorrection = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!selectedTime) return

    const formData = new FormData(e.currentTarget)
    correctionMutation.mutate({
      ri_operation_id: selectedTime.ri_operation_id,
      ri_time_id: selectedTime.id,
      suggested_hours: selectedTime.labor_hours,
      actual_hours: parseFloat(formData.get('actual_hours') as string),
      vehicle_year: parseInt(year),
      vehicle_make: make,
      vehicle_model: model,
      notes: formData.get('notes') as string || undefined,
    })
  }

  const times = data?.times || []
  const vehicle = data?.vehicle

  // Group times by category
  const groupedTimes = times.reduce((acc: Record<string, RITime[]>, time: RITime) => {
    const cat = time.category || 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(time)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/ri">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Operations
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">R&I Time Lookup</h1>
            <p className="text-muted-foreground">Find vehicle-specific R&I labor times</p>
          </div>
        </div>
      </div>

      {/* Vehicle Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Vehicle</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Year</Label>
              <Select value={year} onValueChange={setYear}>
                <SelectTrigger>
                  <SelectValue placeholder="Select year" />
                </SelectTrigger>
                <SelectContent>
                  {YEARS.map(y => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Make</Label>
              <Select value={make} onValueChange={setMake}>
                <SelectTrigger>
                  <SelectValue placeholder="Select make" />
                </SelectTrigger>
                <SelectContent>
                  {MAKES.map(m => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Model</Label>
              <Input
                placeholder="e.g., F-150, Camry"
                value={model}
                onChange={e => setModel(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={handleSearch}
                disabled={!year || !make || !model}
                className="w-full"
              >
                <Search className="h-4 w-4 mr-2" />
                Lookup Times
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : hasSearched && times.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-yellow-500 mb-4" />
            <h3 className="text-lg font-medium">No specific times found</h3>
            <p className="text-muted-foreground">
              No vehicle-specific R&I times found for {year} {make} {model}.
              <br />
              Default times will be used from the operations catalog.
            </p>
          </CardContent>
        </Card>
      ) : hasSearched && times.length > 0 ? (
        <>
          {/* Vehicle Info */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">
                    {vehicle?.year} {vehicle?.make} {vehicle?.model}
                  </h3>
                  <p className="text-muted-foreground">
                    {times.length} R&I operations with vehicle-specific times
                  </p>
                </div>
                <Badge variant="secondary">
                  <Clock className="h-3 w-3 mr-1" />
                  {times.reduce((sum: number, t: RITime) => sum + t.labor_hours, 0).toFixed(1)} total hours
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Times by Category */}
          {Object.entries(groupedTimes).map(([category, categoryTimes]) => (
            <Card key={category}>
              <CardHeader>
                <CardTitle className="capitalize">{category} Operations</CardTitle>
              </CardHeader>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Operation</TableHead>
                    <TableHead className="text-right">Hours</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(categoryTimes as RITime[]).map((time: RITime) => (
                    <TableRow key={time.id}>
                      <TableCell className="font-mono">{time.operation_code}</TableCell>
                      <TableCell>{time.operation_name}</TableCell>
                      <TableCell className="text-right font-medium">
                        {time.labor_hours} hrs
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{time.source}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${time.confidence_score >= 80
                                  ? 'bg-green-500'
                                  : time.confidence_score >= 60
                                    ? 'bg-yellow-500'
                                    : 'bg-red-500'
                                }`}
                              style={{ width: `${time.confidence_score}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {time.confidence_score}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedTime(time)
                            setShowCorrectionDialog(true)
                          }}
                        >
                          <Send className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          ))}
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">Select a vehicle</h3>
            <p className="text-muted-foreground">
              Enter year, make, and model to lookup R&I times
            </p>
          </CardContent>
        </Card>
      )}

      {/* Time Correction Dialog */}
      <Dialog open={showCorrectionDialog} onOpenChange={setShowCorrectionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit Time Correction</DialogTitle>
          </DialogHeader>
          {selectedTime && (
            <form onSubmit={handleSubmitCorrection} className="space-y-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">{selectedTime.operation_name}</p>
                <p className="text-sm text-muted-foreground">
                  {year} {make} {model}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Current Time</Label>
                  <div className="text-2xl font-bold text-muted-foreground">
                    {selectedTime.labor_hours} hrs
                  </div>
                </div>
                <div>
                  <Label htmlFor="actual_hours">Your Actual Time</Label>
                  <Input
                    id="actual_hours"
                    name="actual_hours"
                    type="number"
                    step="0.1"
                    min="0.1"
                    required
                    placeholder="e.g., 1.5"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="notes">Notes (optional)</Label>
                <Textarea
                  id="notes"
                  name="notes"
                  placeholder="Why did it take more or less time?"
                />
              </div>

              <div className="bg-blue-50 p-3 rounded-lg text-sm text-blue-700">
                <CheckCircle className="h-4 w-4 inline mr-2" />
                Your correction will help improve times for everyone!
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowCorrectionDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={correctionMutation.isPending}>
                  {correctionMutation.isPending ? 'Submitting...' : 'Submit Correction'}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export { RITimesPage as default }
