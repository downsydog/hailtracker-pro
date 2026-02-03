import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, User, Car, FileText, DollarSign } from "lucide-react"

export function EstimateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/estimates")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title="Estimate Details"
          description={`Estimate #${id}`}
        >
          <Button variant="outline" asChild>
            <Link to={`/estimates/${id}/edit`}>Edit</Link>
          </Button>
          <Button>Send to Customer</Button>
        </PageHeader>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Customer
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">Customer information</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicle
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Vehicle details</p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Line Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No line items</p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex justify-end">
              <div className="text-right space-y-2">
                <p>Subtotal: $0.00</p>
                <p>Tax: $0.00</p>
                <p className="text-xl font-bold">Total: $0.00</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
