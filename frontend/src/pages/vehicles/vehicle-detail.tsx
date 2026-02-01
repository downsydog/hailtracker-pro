import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Car, User, Briefcase } from "lucide-react"

export function VehicleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/vehicles")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title="Vehicle Details"
          description={`Vehicle #${id}`}
        >
          <Button variant="outline" asChild>
            <Link to={`/vehicles/${id}/edit`}>Edit</Link>
          </Button>
        </PageHeader>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicle Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">Vehicle data will appear here</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Owner
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Owner information</p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Service History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No service history</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
