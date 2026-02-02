import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"

export function SchedulingTokensPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Scheduling Tokens"
        description="Manage self-scheduling links for customers"
      >
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Generate Token
        </Button>
      </PageHeader>

      <Card>
        <CardHeader>
          <CardTitle>About Scheduling Tokens</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Scheduling tokens allow customers to self-schedule their appointments
            without logging in. Each token is unique and can be configured with
            specific constraints like available dates and times.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Tokens</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No active scheduling tokens. Generate one to get started.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Expired Tokens</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No expired tokens
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
