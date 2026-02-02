import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { riApi, RIOperation } from '@/api/ri'
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
  DialogTrigger,
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
  Wrench,
  Plus,
  Search,
  Clock,
  DollarSign,
  Settings,
} from 'lucide-react'

const CATEGORIES = [
  { value: 'electrical', label: 'Electrical' },
  { value: 'trim', label: 'Trim' },
  { value: 'interior', label: 'Interior' },
  { value: 'molding', label: 'Molding' },
  { value: 'glass', label: 'Glass' },
  { value: 'mechanical', label: 'Mechanical' },
]

const LABOR_TYPES = [
  { value: 'body', label: 'Body' },
  { value: 'paint', label: 'Paint' },
  { value: 'pdr', label: 'PDR' },
  { value: 'mechanical', label: 'Mechanical' },
  { value: 'electrical', label: 'Electrical' },
  { value: 'glass', label: 'Glass' },
]

export function RIOperationsPage() {
  const [search, setSearch] = React.useState('')
  const [category, setCategory] = React.useState<string>('all')
  const [showNewOperation, setShowNewOperation] = React.useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['ri-operations', { search, category }],
    queryFn: () => riApi.getOperations({
      search: search || undefined,
      category: category !== 'all' ? category : undefined,
    }),
  })

  const { data: categoriesData } = useQuery({
    queryKey: ['ri-categories'],
    queryFn: riApi.getCategories,
  })

  const { data: statsData } = useQuery({
    queryKey: ['ri-stats'],
    queryFn: () => riApi.getStats(30),
  })

  const { data: ratesData } = useQuery({
    queryKey: ['ri-labor-rates'],
    queryFn: riApi.getLaborRates,
  })

  const createMutation = useMutation({
    mutationFn: riApi.createOperation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ri-operations'] })
      setShowNewOperation(false)
    },
  })

  const handleCreateOperation = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      code: formData.get('code') as string,
      name: formData.get('name') as string,
      category: formData.get('category') as string || 'trim',
      description: formData.get('description') as string || undefined,
      default_hours: parseFloat(formData.get('default_hours') as string) || 0.5,
      default_labor_type: formData.get('default_labor_type') as string || 'body',
    })
  }

  const operations = data?.operations || []
  const categories = categoriesData?.categories || []
  const stats = statsData || { total_ri_items: 0, total_revenue: 0, top_items: [] }
  const rates: Record<string, number> = ratesData?.rates || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">R&I Operations</h1>
          <p className="text-muted-foreground">Remove & Install operations catalog</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/ri/times">
              <Clock className="h-4 w-4 mr-2" />
              Time Lookup
            </Link>
          </Button>
          <Dialog open={showNewOperation} onOpenChange={setShowNewOperation}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Operation
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add R&I Operation</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateOperation} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="code">Code</Label>
                    <Input id="code" name="code" required placeholder="e.g., RI-HDLNR" />
                  </div>
                  <div>
                    <Label htmlFor="category">Category</Label>
                    <Select name="category" defaultValue="trim">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CATEGORIES.map(cat => (
                          <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" name="name" required placeholder="e.g., Headliner" />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea id="description" name="description" placeholder="Operation description..." />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="default_hours">Default Hours</Label>
                    <Input id="default_hours" name="default_hours" type="number" step="0.1" defaultValue={0.5} />
                  </div>
                  <div>
                    <Label htmlFor="default_labor_type">Labor Type</Label>
                    <Select name="default_labor_type" defaultValue="body">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LABOR_TYPES.map(type => (
                          <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setShowNewOperation(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? 'Creating...' : 'Add Operation'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Operations</CardTitle>
            <Wrench className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{operations.length}</div>
            <p className="text-xs text-muted-foreground">In catalog</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">R&I Items (30d)</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_ri_items}</div>
            <p className="text-xs text-muted-foreground">On estimates</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">R&I Revenue (30d)</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${stats.total_revenue?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">From R&I labor</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Body Rate</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${rates.body?.toFixed(2) || '52.00'}/hr
            </div>
            <p className="text-xs text-muted-foreground">Current rate</p>
          </CardContent>
        </Card>
      </div>

      {/* Top R&I Items */}
      {stats.top_items && stats.top_items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Most Used R&I Operations (30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {stats.top_items.slice(0, 10).map((item: { code: string; name: string; usage_count: number }) => (
                <Badge key={item.code} variant="secondary">
                  {item.name} ({item.usage_count}x)
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search operations..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(cat => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Operations Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : operations.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Wrench className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No operations found</h3>
            <p className="text-muted-foreground">Add your first R&I operation to get started</p>
            <Button className="mt-4" onClick={() => setShowNewOperation(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Operation
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">Default Hours</TableHead>
                <TableHead>Labor Type</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operations.map((op: RIOperation) => (
                <TableRow key={op.id}>
                  <TableCell className="font-mono">{op.code}</TableCell>
                  <TableCell>{op.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{op.category}</Badge>
                  </TableCell>
                  <TableCell className="text-right">{op.default_hours} hrs</TableCell>
                  <TableCell>{op.default_labor_type}</TableCell>
                  <TableCell>
                    {op.is_active ? (
                      <Badge variant="secondary">Active</Badge>
                    ) : (
                      <Badge variant="outline">Inactive</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

export { RIOperationsPage as default }
