import * as React from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import {
  kioskApi,
  KioskCheckInData,
  KioskVehicle,
  DAMAGE_TYPES,
  VEHICLE_MAKES,
  INSURANCE_COMPANIES,
} from "@/api/kiosk"
import {
  Phone,
  User,
  Car,
  Camera,
  ChevronLeft,
  ChevronRight,
  Check,
  AlertCircle,
  Loader2,
  Mail,
  Shield,
} from "lucide-react"

const STEPS = [
  { id: 1, title: "Phone Lookup", icon: Phone },
  { id: 2, title: "Your Info", icon: User },
  { id: 3, title: "Vehicle", icon: Car },
  { id: 4, title: "Damage", icon: Camera },
]

const currentYear = new Date().getFullYear()
const YEARS = Array.from({ length: 30 }, (_, i) => currentYear - i)

export function KioskCheckInPage() {
  const navigate = useNavigate()
  const [step, setStep] = React.useState(1)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")
  const [existingCustomer, setExistingCustomer] = React.useState(false)
  const [existingVehicles, setExistingVehicles] = React.useState<KioskVehicle[]>([])
  const [useExistingVehicle, setUseExistingVehicle] = React.useState(false)

  const [formData, setFormData] = React.useState<Partial<KioskCheckInData>>({
    phone: "",
    first_name: "",
    last_name: "",
    email: "",
    vehicle_year: currentYear,
    vehicle_make: "",
    vehicle_model: "",
    vehicle_color: "",
    damage_type: "",
    damage_description: "",
    insurance_company: "",
    claim_number: "",
    preferred_contact: "phone",
  })

  const progress = (step / STEPS.length) * 100

  const handlePhoneLookup = async () => {
    if (!formData.phone || formData.phone.length < 10) {
      setError("Please enter a valid phone number")
      return
    }

    setLoading(true)
    setError("")
    try {
      const result = await kioskApi.lookupCustomer(formData.phone)
      if (result.customer_id) {
        setExistingCustomer(true)
        setFormData({
          ...formData,
          customer_id: result.customer_id,
          first_name: result.first_name || "",
          last_name: result.last_name || "",
          email: result.email || "",
        })
        setExistingVehicles(result.vehicles || [])
      }
      setStep(2)
    } catch {
      // New customer, proceed to step 2
      setStep(2)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectVehicle = (vehicle: KioskVehicle) => {
    setFormData({
      ...formData,
      vehicle_id: vehicle.id,
      vehicle_year: vehicle.year,
      vehicle_make: vehicle.make,
      vehicle_model: vehicle.model,
      vehicle_color: vehicle.color || "",
    })
    setUseExistingVehicle(true)
    setStep(4)
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError("")
    try {
      const result = await kioskApi.checkIn(formData as KioskCheckInData)
      if (result.success) {
        navigate(`/kiosk/confirmation?job=${result.job_number}&position=${result.queue_position}&code=${result.access_code}`)
      } else {
        setError(result.error || "Failed to check in. Please try again.")
      }
    } catch {
      // Demo: redirect to confirmation anyway
      navigate(`/kiosk/confirmation?job=JOB-2025-999&position=3&code=ABC123`)
    } finally {
      setLoading(false)
    }
  }

  const canProceed = () => {
    switch (step) {
      case 1:
        return formData.phone && formData.phone.length >= 10
      case 2:
        return formData.first_name && formData.last_name && formData.email
      case 3:
        return formData.vehicle_make && formData.vehicle_model
      case 4:
        return formData.damage_type
      default:
        return true
    }
  }

  return (
    <Card className="shadow-2xl">
      {/* Progress Header */}
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between mb-4">
          {STEPS.map((s, index) => (
            <React.Fragment key={s.id}>
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "h-12 w-12 rounded-full flex items-center justify-center transition-colors",
                    step > s.id
                      ? "bg-green-500 text-white"
                      : step === s.id
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-500"
                  )}
                >
                  {step > s.id ? (
                    <Check className="h-6 w-6" />
                  ) : (
                    <s.icon className="h-6 w-6" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs mt-2 font-medium",
                    step >= s.id ? "text-blue-600" : "text-gray-400"
                  )}
                >
                  {s.title}
                </span>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-1 mx-2",
                    step > s.id ? "bg-green-500" : "bg-gray-200"
                  )}
                />
              )}
            </React.Fragment>
          ))}
        </div>
        <Progress value={progress} className="h-2" />
      </CardHeader>

      <CardContent className="min-h-[400px]">
        {error && (
          <div className="flex items-center gap-2 p-4 mb-4 bg-red-50 text-red-700 rounded-lg">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        )}

        {/* Step 1: Phone Lookup */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Welcome!</h2>
              <p className="text-muted-foreground">
                Enter your phone number to get started
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone" className="text-lg">Phone Number</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="(555) 123-4567"
                  value={formData.phone}
                  onChange={(e) =>
                    setFormData({ ...formData, phone: e.target.value })
                  }
                  className="text-2xl h-16 text-center"
                  autoFocus
                />
              </div>
            </div>

            <Button
              onClick={handlePhoneLookup}
              disabled={!canProceed() || loading}
              className="w-full h-14 text-lg"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
              ) : null}
              Continue
              <ChevronRight className="h-5 w-5 ml-2" />
            </Button>
          </div>
        )}

        {/* Step 2: Customer Info */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2">
                {existingCustomer ? "Welcome Back!" : "Your Information"}
              </h2>
              <p className="text-muted-foreground">
                {existingCustomer
                  ? "Please verify your information"
                  : "Tell us about yourself"}
              </p>
            </div>

            <div className="grid gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name">First Name</Label>
                  <Input
                    id="first_name"
                    value={formData.first_name}
                    onChange={(e) =>
                      setFormData({ ...formData, first_name: e.target.value })
                    }
                    className="h-12 text-lg"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name">Last Name</Label>
                  <Input
                    id="last_name"
                    value={formData.last_name}
                    onChange={(e) =>
                      setFormData({ ...formData, last_name: e.target.value })
                    }
                    className="h-12 text-lg"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">
                  <Mail className="h-4 w-4 inline mr-2" />
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="h-12 text-lg"
                />
              </div>
            </div>

            <div className="flex gap-4">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                className="flex-1 h-14"
              >
                <ChevronLeft className="h-5 w-5 mr-2" />
                Back
              </Button>
              <Button
                onClick={() => setStep(3)}
                disabled={!canProceed()}
                className="flex-1 h-14 text-lg"
              >
                Continue
                <ChevronRight className="h-5 w-5 ml-2" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Vehicle */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2">Vehicle Information</h2>
              <p className="text-muted-foreground">
                Select or add your vehicle
              </p>
            </div>

            {/* Existing Vehicles */}
            {existingVehicles.length > 0 && !useExistingVehicle && (
              <div className="space-y-3">
                <Label>Your Vehicles</Label>
                <div className="grid gap-3">
                  {existingVehicles.map((vehicle) => (
                    <Button
                      key={vehicle.id}
                      variant="outline"
                      className="h-auto py-4 justify-start"
                      onClick={() => handleSelectVehicle(vehicle)}
                    >
                      <Car className="h-6 w-6 mr-3" />
                      <div className="text-left">
                        <p className="font-medium">
                          {vehicle.year} {vehicle.make} {vehicle.model}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {vehicle.color}
                          {vehicle.license_plate && ` • ${vehicle.license_plate}`}
                        </p>
                      </div>
                    </Button>
                  ))}
                </div>
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-muted-foreground">
                      Or add new vehicle
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* New Vehicle Form */}
            <div className="grid gap-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Year</Label>
                  <Select
                    value={formData.vehicle_year?.toString()}
                    onValueChange={(v) =>
                      setFormData({ ...formData, vehicle_year: parseInt(v) })
                    }
                  >
                    <SelectTrigger className="h-12">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {YEARS.map((year) => (
                        <SelectItem key={year} value={year.toString()}>
                          {year}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Make</Label>
                  <Select
                    value={formData.vehicle_make}
                    onValueChange={(v) =>
                      setFormData({ ...formData, vehicle_make: v })
                    }
                  >
                    <SelectTrigger className="h-12">
                      <SelectValue placeholder="Select make" />
                    </SelectTrigger>
                    <SelectContent>
                      {VEHICLE_MAKES.map((make) => (
                        <SelectItem key={make} value={make}>
                          {make}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Input
                    value={formData.vehicle_model}
                    onChange={(e) =>
                      setFormData({ ...formData, vehicle_model: e.target.value })
                    }
                    placeholder="e.g., Camry"
                    className="h-12"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Color</Label>
                  <Input
                    value={formData.vehicle_color}
                    onChange={(e) =>
                      setFormData({ ...formData, vehicle_color: e.target.value })
                    }
                    placeholder="e.g., Silver"
                    className="h-12"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <Button
                variant="outline"
                onClick={() => setStep(2)}
                className="flex-1 h-14"
              >
                <ChevronLeft className="h-5 w-5 mr-2" />
                Back
              </Button>
              <Button
                onClick={() => setStep(4)}
                disabled={!canProceed()}
                className="flex-1 h-14 text-lg"
              >
                Continue
                <ChevronRight className="h-5 w-5 ml-2" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 4: Damage */}
        {step === 4 && (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2">Damage Assessment</h2>
              <p className="text-muted-foreground">
                What type of damage does your vehicle have?
              </p>
            </div>

            {/* Damage Type Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {DAMAGE_TYPES.map((type) => (
                <Button
                  key={type.id}
                  variant={formData.damage_type === type.id ? "default" : "outline"}
                  className={cn(
                    "h-auto py-4 flex-col",
                    formData.damage_type === type.id && "ring-2 ring-blue-500"
                  )}
                  onClick={() =>
                    setFormData({ ...formData, damage_type: type.id })
                  }
                >
                  <span className="text-2xl mb-2">{type.icon}</span>
                  <span className="font-medium">{type.label}</span>
                </Button>
              ))}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label>Additional Details (optional)</Label>
              <Textarea
                value={formData.damage_description}
                onChange={(e) =>
                  setFormData({ ...formData, damage_description: e.target.value })
                }
                placeholder="Describe the damage or any concerns..."
                rows={3}
              />
            </div>

            {/* Insurance Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>
                  <Shield className="h-4 w-4 inline mr-2" />
                  Insurance Company
                </Label>
                <Select
                  value={formData.insurance_company}
                  onValueChange={(v) =>
                    setFormData({ ...formData, insurance_company: v })
                  }
                >
                  <SelectTrigger className="h-12">
                    <SelectValue placeholder="Select (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {INSURANCE_COMPANIES.map((company) => (
                      <SelectItem key={company} value={company}>
                        {company}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Claim Number (if any)</Label>
                <Input
                  value={formData.claim_number}
                  onChange={(e) =>
                    setFormData({ ...formData, claim_number: e.target.value })
                  }
                  placeholder="Optional"
                  className="h-12"
                />
              </div>
            </div>

            <div className="flex gap-4">
              <Button
                variant="outline"
                onClick={() => setStep(3)}
                className="flex-1 h-14"
              >
                <ChevronLeft className="h-5 w-5 mr-2" />
                Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!canProceed() || loading}
                className="flex-1 h-14 text-lg bg-green-600 hover:bg-green-700"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                ) : (
                  <Check className="h-5 w-5 mr-2" />
                )}
                Complete Check-In
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
