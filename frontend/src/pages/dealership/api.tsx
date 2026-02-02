import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { dealershipApi, ApiUsage, Dealership } from "@/api/dealership"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Key,
  Copy,
  RefreshCw,
  Eye,
  EyeOff,
  CheckCircle2,
  Clock,
  Activity,
  BarChart3,
  AlertTriangle,
  ExternalLink,
  Code,
} from "lucide-react"

// Demo data
const DEMO_DEALERSHIP: Dealership = {
  id: 1,
  name: "Premier Auto Group",
  code: "PAG001",
  api_key: "dk_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  pricing_tier: "premium",
  discount_percent: 15,
  status: "active",
  locations_count: 3,
  vehicles_count: 47,
  active_jobs: 10,
  created_at: "2023-06-15T10:00:00Z",
}

const DEMO_API_USAGE: ApiUsage = {
  period: "January 2024",
  requests_total: 1247,
  requests_limit: 5000,
  vehicles_synced: 156,
  jobs_created: 34,
  last_sync: "2024-01-24T14:32:00Z",
  endpoints: [
    { endpoint: "/vehicles", method: "GET", calls: 423, avg_response_ms: 125 },
    { endpoint: "/vehicles", method: "POST", calls: 156, avg_response_ms: 234 },
    { endpoint: "/jobs", method: "GET", calls: 312, avg_response_ms: 98 },
    { endpoint: "/jobs", method: "POST", calls: 34, avg_response_ms: 456 },
    { endpoint: "/stats", method: "GET", calls: 89, avg_response_ms: 67 },
    { endpoint: "/locations", method: "GET", calls: 233, avg_response_ms: 45 },
  ],
}

const API_DOCS_URL = "https://docs.hailtracker.com/api/dealership"

const CODE_EXAMPLES = {
  curl: `curl -X GET "https://api.hailtracker.com/v1/dealership/vehicles" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json"`,
  python: `import requests

response = requests.get(
    "https://api.hailtracker.com/v1/dealership/vehicles",
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)
vehicles = response.json()`,
  javascript: `const response = await fetch(
  "https://api.hailtracker.com/v1/dealership/vehicles",
  {
    headers: {
      "Authorization": "Bearer YOUR_API_KEY",
      "Content-Type": "application/json"
    }
  }
);
const vehicles = await response.json();`,
}

export function DealershipApiPage() {
  const dealershipId = 1
  const queryClient = useQueryClient()

  const [showKey, setShowKey] = React.useState(false)
  const [copied, setCopied] = React.useState(false)
  const [showRegenerateDialog, setShowRegenerateDialog] = React.useState(false)
  const [selectedExample, setSelectedExample] = React.useState<keyof typeof CODE_EXAMPLES>("curl")

  const { data: dealership } = useQuery({
    queryKey: ["dealership", dealershipId],
    queryFn: () => dealershipApi.getDealership(dealershipId),
    placeholderData: DEMO_DEALERSHIP,
  })

  const { data: usage } = useQuery({
    queryKey: ["dealership", dealershipId, "api-usage"],
    queryFn: () => dealershipApi.getApiUsage(dealershipId),
    placeholderData: DEMO_API_USAGE,
  })

  const regenerateMutation = useMutation({
    mutationFn: () => dealershipApi.regenerateApiKey(dealershipId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dealership", dealershipId] })
      setShowRegenerateDialog(false)
    },
  })

  const apiKey = dealership?.api_key ?? DEMO_DEALERSHIP.api_key
  const apiUsage = usage ?? DEMO_API_USAGE

  const copyToClipboard = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const maskedKey = apiKey
    ? `${apiKey.slice(0, 10)}${"•".repeat(20)}${apiKey.slice(-4)}`
    : ""

  const usagePercent = (apiUsage.requests_total / apiUsage.requests_limit) * 100
  const isNearLimit = usagePercent > 80

  return (
    <div className="space-y-6">
      {/* API Key Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            <CardTitle>API Key</CardTitle>
          </div>
          <CardDescription>
            Use this key to authenticate API requests from your systems
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <Input
                type={showKey ? "text" : "password"}
                value={showKey ? apiKey : maskedKey}
                readOnly
                className="font-mono pr-20"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => setShowKey(!showKey)}
                >
                  {showKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={copyToClipboard}
                >
                  {copied ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => setShowRegenerateDialog(true)}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate
            </Button>
          </div>

          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Keep your API key secure</AlertTitle>
            <AlertDescription>
              Never share your API key publicly or commit it to version control.
              Regenerating will invalidate the old key immediately.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Usage Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {apiUsage.requests_total.toLocaleString()}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <Progress value={usagePercent} className={`h-2 ${isNearLimit ? "bg-yellow-100" : ""}`} />
              <span className="text-xs text-muted-foreground">
                {apiUsage.requests_limit.toLocaleString()}
              </span>
            </div>
            {isNearLimit && (
              <p className="text-xs text-yellow-600 mt-1">
                Approaching monthly limit
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Vehicles Synced</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apiUsage.vehicles_synced}</div>
            <p className="text-xs text-muted-foreground mt-1">
              This billing period
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Jobs Created</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apiUsage.jobs_created}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Via API this month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Sync</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Date(apiUsage.last_sync).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {new Date(apiUsage.last_sync).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Endpoint Usage */}
      <Card>
        <CardHeader>
          <CardTitle>Endpoint Usage</CardTitle>
          <CardDescription>
            API call breakdown for {apiUsage.period}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Endpoint</TableHead>
                <TableHead>Method</TableHead>
                <TableHead className="text-right">Calls</TableHead>
                <TableHead className="text-right">Avg Response</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiUsage.endpoints.map((endpoint, index) => (
                <TableRow key={index}>
                  <TableCell className="font-mono text-sm">
                    {endpoint.endpoint}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={
                        endpoint.method === "GET"
                          ? "bg-blue-50 text-blue-700"
                          : endpoint.method === "POST"
                          ? "bg-green-50 text-green-700"
                          : endpoint.method === "PUT"
                          ? "bg-yellow-50 text-yellow-700"
                          : "bg-red-50 text-red-700"
                      }
                    >
                      {endpoint.method}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {endpoint.calls.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {endpoint.avg_response_ms}ms
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Quick Start */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Quick Start
              </CardTitle>
              <CardDescription>
                Example code to get started with the API
              </CardDescription>
            </div>
            <Button variant="outline" asChild>
              <a href={API_DOCS_URL} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                Full Documentation
              </a>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              {(Object.keys(CODE_EXAMPLES) as Array<keyof typeof CODE_EXAMPLES>).map(
                (lang) => (
                  <Button
                    key={lang}
                    variant={selectedExample === lang ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedExample(lang)}
                  >
                    {lang.charAt(0).toUpperCase() + lang.slice(1)}
                  </Button>
                )
              )}
            </div>

            <div className="relative">
              <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm">
                <code>{CODE_EXAMPLES[selectedExample]}</code>
              </pre>
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 h-8 w-8"
                onClick={() => {
                  navigator.clipboard.writeText(CODE_EXAMPLES[selectedExample])
                }}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pricing Tier Info */}
      <Card>
        <CardHeader>
          <CardTitle>Your Plan</CardTitle>
          <CardDescription>
            Current API access tier and limits
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Badge className="bg-primary text-primary-foreground">
                  {dealership?.pricing_tier?.toUpperCase() ?? "PREMIUM"}
                </Badge>
              </div>
              <div>
                <h3 className="font-semibold">
                  {(dealership?.pricing_tier ?? "premium").charAt(0).toUpperCase() +
                    (dealership?.pricing_tier ?? "premium").slice(1)}{" "}
                  Plan
                </h3>
                <p className="text-sm text-muted-foreground">
                  {dealership?.discount_percent ?? 15}% volume discount •{" "}
                  {apiUsage.requests_limit.toLocaleString()} requests/month
                </p>
              </div>
            </div>
            <Button variant="outline">Upgrade Plan</Button>
          </div>
        </CardContent>
      </Card>

      {/* Regenerate Key Dialog */}
      <AlertDialog open={showRegenerateDialog} onOpenChange={setShowRegenerateDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Regenerate API Key</AlertDialogTitle>
            <AlertDialogDescription>
              This will create a new API key and immediately invalidate your current key.
              Any systems using the old key will stop working until updated.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => regenerateMutation.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {regenerateMutation.isPending ? "Regenerating..." : "Regenerate Key"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
