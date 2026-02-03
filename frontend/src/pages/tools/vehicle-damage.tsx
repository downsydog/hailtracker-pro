import { useState, useRef } from "react"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Car,
  Upload,
  Link as LinkIcon,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  DollarSign,
  Wrench,
  Target,
  Plus,
  X,
} from "lucide-react"
import { useMutation } from "@tanstack/react-query"

interface DamageAnalysisResult {
  vehicle_detected: boolean
  damage_detected: boolean
  severity?: string
  confidence?: number

  // Damage details
  dent_count?: number
  affected_panels?: string[]
  damage_type?: string

  // Cost estimates
  repair_cost_estimate?: {
    low: number
    high: number
    pdr_eligible: boolean
  }

  // Per-image results (for multi-image)
  results?: DamageAnalysisResult[]

  error?: string
}

const SEVERITY_INFO: Record<string, { label: string; color: string; description: string }> = {
  none: { label: "No Damage", color: "bg-gray-500", description: "No visible hail damage detected" },
  minor: { label: "Minor", color: "bg-green-500", description: "Light dents, typically PDR repairable" },
  moderate: { label: "Moderate", color: "bg-yellow-500", description: "Multiple dents, may require body work" },
  severe: { label: "Severe", color: "bg-orange-500", description: "Significant damage, likely requires conventional repair" },
  catastrophic: { label: "Total Loss", color: "bg-red-600", description: "Extensive damage, possible total loss" },
}

const PANEL_ICONS: Record<string, string> = {
  hood: "Hood",
  roof: "Roof",
  trunk: "Trunk/Deck Lid",
  door: "Door(s)",
  fender: "Fender(s)",
  quarter_panel: "Quarter Panel(s)",
}

async function analyzeVehicleDamage(images: string[]): Promise<DamageAnalysisResult> {
  const response = await fetch("/api/ml/analyze-vehicle-damage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      images: images.map(img => ({ base64: img })),
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || "Analysis failed")
  }

  return response.json()
}

export function VehicleDamagePage() {
  const [images, setImages] = useState<{ preview: string; base64: string }[]>([])
  const [imageUrl, setImageUrl] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const analysisMutation = useMutation({
    mutationFn: (imageData: string[]) => analyzeVehicleDamage(imageData),
  })

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const result = e.target?.result as string
        const base64 = result.split(",")[1]
        setImages(prev => [...prev, { preview: result, base64 }])
      }
      reader.readAsDataURL(file)
    })

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleUrlLoad = async () => {
    if (!imageUrl) return

    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const reader = new FileReader()
      reader.onload = (e) => {
        const result = e.target?.result as string
        const base64 = result.split(",")[1]
        setImages(prev => [...prev, { preview: result, base64 }])
        setImageUrl("")
      }
      reader.readAsDataURL(blob)
    } catch (error) {
      console.error("Failed to load image from URL:", error)
    }
  }

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleAnalyze = () => {
    if (images.length > 0) {
      analysisMutation.mutate(images.map(img => img.base64))
    }
  }

  const clearAll = () => {
    setImages([])
    setImageUrl("")
    analysisMutation.reset()
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const result = analysisMutation.data
  const severityInfo = result?.severity ? SEVERITY_INFO[result.severity] : null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vehicle Damage Analyzer"
        description="AI-powered hail damage assessment and repair cost estimation"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Upload Vehicle Photos
            </CardTitle>
            <CardDescription>
              Upload multiple photos of the vehicle for comprehensive damage assessment
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs defaultValue="upload" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Files
                </TabsTrigger>
                <TabsTrigger value="url">
                  <LinkIcon className="mr-2 h-4 w-4" />
                  From URL
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="photos">Vehicle Photos</Label>
                  <Input
                    id="photos"
                    type="file"
                    accept="image/*"
                    multiple
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    className="cursor-pointer"
                  />
                  <p className="text-xs text-muted-foreground">
                    For best results, include photos of hood, roof, trunk, and side panels
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="url" className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="url">Image URL</Label>
                  <div className="flex gap-2">
                    <Input
                      id="url"
                      type="url"
                      placeholder="https://example.com/vehicle-photo.jpg"
                      value={imageUrl}
                      onChange={(e) => setImageUrl(e.target.value)}
                    />
                    <Button onClick={handleUrlLoad} variant="secondary">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Image Previews */}
            {images.length > 0 && (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label>{images.length} Photo{images.length !== 1 ? "s" : ""} Added</Label>
                  <Button variant="ghost" size="sm" onClick={clearAll}>
                    Clear All
                  </Button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {images.map((img, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={img.preview}
                        alt={`Vehicle ${index + 1}`}
                        className="w-full h-24 object-cover rounded-lg border"
                      />
                      <Button
                        variant="destructive"
                        size="icon"
                        className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => removeImage(index)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Analyze Button */}
            <Button
              onClick={handleAnalyze}
              disabled={images.length === 0 || analysisMutation.isPending}
              className="w-full"
              size="lg"
            >
              {analysisMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing {images.length} photo{images.length !== 1 ? "s" : ""}...
                </>
              ) : (
                <>
                  <Target className="mr-2 h-4 w-4" />
                  Analyze Damage
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              Damage Assessment
            </CardTitle>
            <CardDescription>
              AI-detected damage severity and repair cost estimates
            </CardDescription>
          </CardHeader>
          <CardContent>
            {analysisMutation.isError && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Analysis Failed</AlertTitle>
                <AlertDescription>
                  {analysisMutation.error?.message || "An error occurred during analysis"}
                </AlertDescription>
              </Alert>
            )}

            {!result && !analysisMutation.isPending && !analysisMutation.isError && (
              <div className="text-center py-12 text-muted-foreground">
                <Car className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Upload vehicle photos and click "Analyze" to get damage assessment</p>
              </div>
            )}

            {analysisMutation.isPending && (
              <div className="text-center py-12">
                <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-blue-500" />
                <p className="text-muted-foreground">Analyzing vehicle damage with AI...</p>
              </div>
            )}

            {result && (
              <div className="space-y-6">
                {/* Vehicle Detection */}
                {!result.vehicle_detected ? (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>No Vehicle Detected</AlertTitle>
                    <AlertDescription>
                      Could not detect a vehicle in the uploaded images. Please upload clear photos of the vehicle.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <>
                    {/* Damage Detection */}
                    {!result.damage_detected ? (
                      <Alert className="border-green-500 bg-green-500/10">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                        <AlertTitle>No Damage Detected</AlertTitle>
                        <AlertDescription>
                          No visible hail damage was detected on this vehicle
                        </AlertDescription>
                      </Alert>
                    ) : (
                      <>
                        {/* Severity */}
                        {severityInfo && (
                          <div className="p-4 rounded-lg bg-muted space-y-2">
                            <div className="flex items-center gap-3">
                              <div className={`w-4 h-4 rounded-full ${severityInfo.color}`} />
                              <div>
                                <p className="font-semibold text-lg">{severityInfo.label} Damage</p>
                                <p className="text-sm text-muted-foreground">{severityInfo.description}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Dent Count */}
                        {result.dent_count !== undefined && (
                          <div className="flex items-center justify-between p-3 rounded-lg border">
                            <span className="font-medium">Estimated Dent Count</span>
                            <Badge variant="secondary" className="text-lg px-3 py-1">
                              {result.dent_count}+
                            </Badge>
                          </div>
                        )}

                        {/* Affected Panels */}
                        {result.affected_panels && result.affected_panels.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-sm font-medium">Affected Panels</span>
                            <div className="flex flex-wrap gap-2">
                              {result.affected_panels.map((panel, i) => (
                                <Badge key={i} variant="outline">
                                  {PANEL_ICONS[panel] || panel}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Confidence */}
                        {result.confidence !== undefined && (
                          <div className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span>Detection Confidence</span>
                              <span>{result.confidence.toFixed(1)}%</span>
                            </div>
                            <Progress value={result.confidence} className="h-2" />
                          </div>
                        )}

                        {/* Cost Estimate */}
                        {result.repair_cost_estimate && (
                          <div className="pt-4 border-t space-y-3">
                            <h4 className="font-medium flex items-center gap-2">
                              <DollarSign className="h-4 w-4" />
                              Repair Cost Estimate
                            </h4>

                            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                              <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">Estimated Range</span>
                                <span className="text-xl font-bold text-green-600">
                                  ${result.repair_cost_estimate.low.toLocaleString()} - ${result.repair_cost_estimate.high.toLocaleString()}
                                </span>
                              </div>
                            </div>

                            {result.repair_cost_estimate.pdr_eligible && (
                              <Alert className="border-blue-500 bg-blue-500/10">
                                <CheckCircle2 className="h-4 w-4 text-blue-500" />
                                <AlertTitle>PDR Eligible</AlertTitle>
                                <AlertDescription>
                                  This vehicle appears to be a good candidate for Paintless Dent Repair (PDR)
                                </AlertDescription>
                              </Alert>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tips Section */}
      <Card>
        <CardHeader>
          <CardTitle>Tips for Best Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-1">Good Lighting</h4>
              <p className="text-sm text-muted-foreground">
                Take photos in daylight or with bright, even lighting to highlight dents
              </p>
            </div>
            <div className="p-3 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-1">Multiple Angles</h4>
              <p className="text-sm text-muted-foreground">
                Include photos from different angles to capture all damaged areas
              </p>
            </div>
            <div className="p-3 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-1">Close-ups</h4>
              <p className="text-sm text-muted-foreground">
                Take close-up shots of damaged areas for more accurate assessment
              </p>
            </div>
            <div className="p-3 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-1">Clean Vehicle</h4>
              <p className="text-sm text-muted-foreground">
                A clean vehicle surface makes dents easier for the AI to detect
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
