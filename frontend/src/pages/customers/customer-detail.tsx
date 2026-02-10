import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, User, Car, Briefcase, FileText, Plus, Loader2, Phone, Mail, MapPin } from "lucide-react"
import { useCustomer } from "@/hooks/use-customers"
import { usePDREstimates } from "@/hooks/use-pdr-estimates"

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  completed: 'bg-emerald-100 text-emerald-700',
}

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const customerId = id ? parseInt(id) : null

  // Fetch customer data
  const { customer, isLoading: isLoadingCustomer, error: customerError } = useCustomer(customerId)

  // Fetch customer's estimates
  const { data: estimatesData, isLoading: isLoadingEstimates } = usePDREstimates(
    customerId ? { contact_id: customerId } : undefined
  )

  const estimates = estimatesData?.estimates || []

  if (isLoadingCustomer) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (customerError || !customer) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/customers")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <PageHeader
            title="Customer Not Found"
            description="The requested customer could not be found"
          />
        </div>
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">Customer with ID {id} was not found.</p>
            <Button variant="outline" className="mt-4" onClick={() => navigate("/customers")}>
              Back to Customers
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const customerName = `${customer.first_name} ${customer.last_name}`
  const fullAddress = [
    customer.street_address || customer.address,
    customer.city,
    customer.state,
    customer.zip_code || customer.zip
  ].filter(Boolean).join(', ')

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/customers")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={customerName}
          description={customer.company_name || `Customer #${id}`}
        >
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to={`/customers/${id}/edit`}>Edit</Link>
            </Button>
            <Button asChild>
              <Link to={`/estimating/new?customer_id=${id}`}>
                <Plus className="h-4 w-4 mr-2" />
                Create Estimate
              </Link>
            </Button>
          </div>
        </PageHeader>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Contact Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Contact Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{customerName}</span>
              </div>
              {customer.phone && (
                <div className="flex items-center gap-3">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <a href={`tel:${customer.phone}`} className="text-primary hover:underline">
                    {customer.phone}
                  </a>
                </div>
              )}
              {customer.email && (
                <div className="flex items-center gap-3">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <a href={`mailto:${customer.email}`} className="text-primary hover:underline">
                    {customer.email}
                  </a>
                </div>
              )}
              {fullAddress && (
                <div className="flex items-start gap-3">
                  <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <span className="text-muted-foreground">{fullAddress}</span>
                </div>
              )}
            </div>
            {customer.source && (
              <div className="pt-3 border-t">
                <span className="text-sm text-muted-foreground">Source: </span>
                <span className="text-sm font-medium capitalize">{customer.source}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Vehicles */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicles
            </CardTitle>
          </CardHeader>
          <CardContent>
            {customer.vehicles_count === 0 ? (
              <p className="text-muted-foreground">No vehicles on record</p>
            ) : (
              <p className="text-muted-foreground">
                {customer.vehicles_count} vehicle{customer.vehicles_count !== 1 ? 's' : ''} on record
              </p>
            )}
          </CardContent>
        </Card>

        {/* Estimates */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Estimates
            </CardTitle>
            <Button size="sm" asChild>
              <Link to={`/estimating/new?customer_id=${id}`}>
                <Plus className="h-4 w-4 mr-1" />
                New Estimate
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoadingEstimates ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : estimates.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground mb-3">No estimates yet</p>
                <Button variant="outline" size="sm" asChild>
                  <Link to={`/estimating/new?customer_id=${id}`}>
                    Create First Estimate
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="overflow-hidden rounded-lg border">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 text-sm font-medium">Estimate #</th>
                      <th className="text-left p-3 text-sm font-medium">Vehicle</th>
                      <th className="text-left p-3 text-sm font-medium">Date</th>
                      <th className="text-left p-3 text-sm font-medium">Total</th>
                      <th className="text-left p-3 text-sm font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {estimates.map((estimate) => (
                      <tr key={estimate.id} className="hover:bg-accent/50">
                        <td className="p-3">
                          <Link
                            to={`/estimating/${estimate.id}`}
                            className="font-medium text-primary hover:underline"
                          >
                            {estimate.estimate_number || `EST-${estimate.id}`}
                          </Link>
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {estimate.created_at ? new Date(estimate.created_at).toLocaleDateString() : '-'}
                        </td>
                        <td className="p-3 font-medium">
                          ${(estimate.total_price || 0).toLocaleString()}
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 text-xs rounded-full capitalize ${statusColors[estimate.status] || statusColors.draft}`}>
                            {estimate.status?.replace('_', ' ') || 'draft'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Job History */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Job History
            </CardTitle>
          </CardHeader>
          <CardContent>
            {customer.jobs_count === 0 ? (
              <p className="text-muted-foreground">No job history</p>
            ) : (
              <p className="text-muted-foreground">
                {customer.jobs_count} job{customer.jobs_count !== 1 ? 's' : ''} on record
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
