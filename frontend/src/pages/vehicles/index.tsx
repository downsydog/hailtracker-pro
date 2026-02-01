import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Car } from "lucide-react"

export function VehiclesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Vehicles"
        description="Manage customer vehicles"
      >
        <Button asChild>
          <Link to="/vehicles/new">
            <Plus className="h-4 w-4 mr-2" />
            Add Vehicle
          </Link>
        </Button>
      </PageHeader>

      <Card>
        <CardContent className="py-12 text-center">
          <Car className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No vehicles found</p>
          <Button variant="link" asChild>
            <Link to="/vehicles/new">Add your first vehicle</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
