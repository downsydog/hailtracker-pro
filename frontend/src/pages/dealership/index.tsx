import * as React from "react"
import { Outlet, Link, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Car,
  Upload,
  MapPin,
  Code,
  LayoutDashboard,
  LogOut,
  Settings,
} from "lucide-react"

// Dealership Layout
export function DealershipLayout() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold">Dealership Portal</h1>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon">
              <Settings className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => navigate("/login")}>
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>
      <nav className="bg-white border-b">
        <div className="container mx-auto px-4 flex gap-4 py-2">
          <Link to="/dealership" className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 rounded">
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Link>
          <Link to="/dealership/vehicles" className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 rounded">
            <Car className="h-4 w-4" />
            Vehicles
          </Link>
          <Link to="/dealership/upload" className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 rounded">
            <Upload className="h-4 w-4" />
            Upload
          </Link>
          <Link to="/dealership/locations" className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 rounded">
            <MapPin className="h-4 w-4" />
            Locations
          </Link>
          <Link to="/dealership/api" className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 rounded">
            <Code className="h-4 w-4" />
            API
          </Link>
        </div>
      </nav>
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

// Dealership Dashboard
export function DealershipDashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dealership Dashboard"
        description="Manage your dealership's hail damage repair program"
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Vehicles in Queue</CardTitle>
            <Car className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
            <p className="text-xs text-muted-foreground">Awaiting inspection</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Car className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
            <p className="text-xs text-muted-foreground">Being repaired</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <Car className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No recent activity
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

// Dealership Vehicles
export function DealershipVehiclesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Vehicles"
        description="Manage vehicles submitted for hail repair"
      >
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Add Vehicle
        </Button>
      </PageHeader>

      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No vehicles found. Add your first vehicle to get started.
        </CardContent>
      </Card>
    </div>
  )
}

// Dealership Upload
export function DealershipUploadPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Bulk Upload"
        description="Upload multiple vehicles at once"
      />

      <Card>
        <CardContent className="py-12">
          <div className="border-2 border-dashed rounded-lg p-12 text-center">
            <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Drop files here or click to upload</p>
            <p className="text-sm text-muted-foreground">
              Supports CSV, XLS, XLSX files
            </p>
            <Button variant="outline" className="mt-4">
              Select Files
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Dealership Locations
export function DealershipLocationsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Locations"
        description="Manage your dealership locations"
      >
        <Button>
          <MapPin className="h-4 w-4 mr-2" />
          Add Location
        </Button>
      </PageHeader>

      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No locations configured. Add your first location.
        </CardContent>
      </Card>
    </div>
  )
}

// Dealership API
export function DealershipApiPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="API Integration"
        description="Integrate with your DMS or inventory system"
      />

      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            Use these credentials to integrate with our API
          </p>
          <div className="bg-muted p-4 rounded-lg font-mono text-sm">
            <p>API Key: ••••••••••••••••</p>
            <p>Secret: ••••••••••••••••</p>
          </div>
          <Button variant="outline" className="mt-4">
            Regenerate Keys
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
