import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Wrench, Clock, Plus, CheckCircle } from "lucide-react"

export function RIOperationsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="R&I Operations"
        description="Remove & Install tracking"
      >
        <Button variant="outline" asChild>
          <Link to="/ri/times">
            <Clock className="h-4 w-4 mr-2" />
            View Times
          </Link>
        </Button>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Log R&I
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pending R&I</CardTitle>
            <Wrench className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">5</p>
            <p className="text-xs text-muted-foreground">Jobs needing R&I</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">2</p>
            <p className="text-xs text-muted-foreground">Currently working</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">8</p>
            <p className="text-xs text-muted-foreground">R&I operations</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>R&I Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No R&I operations in queue
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export function RITimesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="R&I Time Standards"
        description="Standard times for R&I operations"
      >
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Standard
        </Button>
      </PageHeader>

      <Card>
        <CardHeader>
          <CardTitle>Time Standards</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No time standards configured
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
