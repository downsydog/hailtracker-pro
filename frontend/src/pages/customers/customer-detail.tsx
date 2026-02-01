import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, User, Phone, Mail, MapPin, Car, Briefcase } from "lucide-react"

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/customers")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title="Customer Details"
          description={`Customer #${id}`}
        >
          <Button variant="outline" asChild>
            <Link to={`/customers/${id}/edit`}>Edit</Link>
          </Button>
        </PageHeader>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Contact Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">Customer data will appear here</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No vehicles on record</p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Job History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No job history</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
