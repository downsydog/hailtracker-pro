import { useState, useEffect, FormEvent, ChangeEvent } from "react"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { adminApi } from "@/api/admin"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Save } from "lucide-react"

interface SettingsData {
  company_name: string
  company_email: string
  company_phone: string
  company_address: string
  tax_rate: string
  default_labor_rate: string
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<SettingsData>({
    company_name: "",
    company_email: "",
    company_phone: "",
    company_address: "",
    tax_rate: "",
    default_labor_rate: "",
  })

  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin", "settings"],
    queryFn: () => adminApi.getSettings(),
  })

  useEffect(() => {
    if (settings) {
      const s = settings as Record<string, unknown>
      setFormData({
        company_name: String(s.company_name || ""),
        company_email: String(s.company_email || ""),
        company_phone: String(s.company_phone || ""),
        company_address: String(s.company_address || ""),
        tax_rate: s.tax_rate != null ? String(s.tax_rate) : "",
        default_labor_rate: s.default_labor_rate != null ? String(s.default_labor_rate) : "",
      })
    }
  }, [settings])

  const updateSettings = useMutation({
    mutationFn: (data: SettingsData) =>
      adminApi.updateSettings({
        ...data,
        tax_rate: parseFloat(data.tax_rate) || 0,
        default_labor_rate: parseFloat(data.default_labor_rate) || 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "settings"] })
    },
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    updateSettings.mutate(formData)
  }

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Manage your business settings and preferences."
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Company Information</CardTitle>
            <CardDescription>
              Basic information about your business.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="company_name">Company Name</Label>
                <Input
                  id="company_name"
                  name="company_name"
                  value={formData.company_name}
                  onChange={handleChange}
                  placeholder="Your Company Name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="company_email">Email</Label>
                <Input
                  id="company_email"
                  name="company_email"
                  type="email"
                  value={formData.company_email}
                  onChange={handleChange}
                  placeholder="contact@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="company_phone">Phone</Label>
                <Input
                  id="company_phone"
                  name="company_phone"
                  value={formData.company_phone}
                  onChange={handleChange}
                  placeholder="(555) 123-4567"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="company_address">Address</Label>
                <Input
                  id="company_address"
                  name="company_address"
                  value={formData.company_address}
                  onChange={handleChange}
                  placeholder="123 Main St, City, State"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Billing Settings</CardTitle>
            <CardDescription>
              Default rates and tax configuration.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="tax_rate">Tax Rate (%)</Label>
                <Input
                  id="tax_rate"
                  name="tax_rate"
                  type="number"
                  step="0.01"
                  value={formData.tax_rate}
                  onChange={handleChange}
                  placeholder="8.25"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="default_labor_rate">Default Labor Rate ($/hr)</Label>
                <Input
                  id="default_labor_rate"
                  name="default_labor_rate"
                  type="number"
                  step="0.01"
                  value={formData.default_labor_rate}
                  onChange={handleChange}
                  placeholder="85.00"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" disabled={updateSettings.isPending}>
            {updateSettings.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Settings
          </Button>
        </div>
      </form>
    </div>
  )
}
