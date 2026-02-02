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
  Camera,
  Upload,
  Link as LinkIcon,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Ruler,
  Shield,
  CloudRain,
  Sparkles,
} from "lucide-react"
import { useMutation } from "@tanstack/react-query"

interface AnalysisResult {
  // Hail size analysis
  hail_detected?: boolean
  estimated_size_inches?: number
  size_category?: string
  size_confidence?: number
  severity?: string

  // Photo validation
  is_authentic?: boolean
  authenticity_confidence?: number
  manipulation_indicators?: string[]

  // Combined analysis flags
  analyzed_hail?: boolean
  analyzed_authenticity?: boolean

  // Error handling
  error?: string
}

const SIZE_CATEGORIES = {
  pea: { label: "Pea", range: "0.25\"", color: "bg-green-500" },
  marble: { label: "Marble", range: "0.5\"", color: "bg-lime-500" },
  dime: { label: "Dime", range: "0.7\"", color: "bg-yellow-500" },
  penny: { label: "Penny", range: "0.75\"", color: "bg-yellow-600" },
  nickel: { label: "Nickel", range: "0.88\"", color: "bg-amber-500" },
  quarter: { label: "Quarter", range: "1.0\"", color: "bg-orange-500" },
  half_dollar: { label: "Half Dollar", range: "1.25\"", color: "bg-orange-600" },
  golf_ball: { label: "Golf Ball", range: "1.75\"", color: "bg-red-500" },
  tennis_ball: { label: "Tennis Ball", range: "2.5\"", color: "bg-red-600" },
  baseball: { label: "Baseball", range: "2.75\"", color: "bg-red-700" },
  softball: { label: "Softball", range: "4.0\"", color: "bg-purple-600" },
  grapefruit: { label: "Grapefruit", range: "4.5\"", color: "bg-purple-700" },
}

const SEVERITY_COLORS: Record<string, string> = {
  trace: "bg-gray-500",
  minor: "bg-green-500",
  moderate: "bg-yellow-500",
  severe: "bg-orange-500",
  catastrophic: "bg-red-600",
}

async function analyzePhoto(imageBase64: string): Promise<AnalysisResult> {
  const response = await fetch("/api/ml/analyze-hail-photo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      image_base64: imageBase64,
      include_validation: true,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || "Analysis failed")
  }

  return response.json()
}

export function PhotoAnalyzerPage() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageBase64, setImageBase64] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const analysisMutation = useMutation({
    mutationFn: analyzePhoto,
  })

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      const result = e.target?.result as string
      setImagePreview(result)
      // Extract base64 data (remove data:image/...;base64, prefix)
      const base64 = result.split(",")[1]
      setImageBase64(base64)
    }
    reader.readAsDataURL(file)
  }

  const handleUrlLoad = async () => {
    if (!imageUrl) return

    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const reader = new FileReader()
      reader.onload = (e) => {
        const result = e.target?.result as string
        setImagePreview(result)
        const base64 = result.split(",")[1]
        setImageBase64(base64)
      }
      reader.readAsDataURL(blob)
    } catch (error) {
      console.error("Failed to load image from URL:", error)
    }
  }

  const handleAnalyze = () => {
    if (imageBase64) {
      analysisMutation.mutate(imageBase64)
    }
  }

  const clearImage = () => {
    setImagePreview(null)
    setImageBase64(null)
    setImageUrl("")
    analysisMutation.reset()
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const result = analysisMutation.data
  const sizeInfo = result?.size_category ? SIZE_CATEGORIES[result.size_category as keyof typeof SIZE_CATEGORIES] : null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Hail Photo Analyzer"
        description="AI-powered analysis to detect hail and estimate size from photos"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Upload Photo
            </CardTitle>
            <CardDescription>
              Upload a photo of hail or paste an image URL to analyze
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs defaultValue="upload" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload File
                </TabsTrigger>
                <TabsTrigger value="url">
                  <LinkIcon className="mr-2 h-4 w-4" />
                  From URL
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="photo">Photo</Label>
                  <Input
                    id="photo"
                    type="file"
                    accept="image/*"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    className="cursor-pointer"
                  />
                </div>
              </TabsContent>

              <TabsContent value="url" className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="url">Image URL</Label>
                  <div className="flex gap-2">
                    <Input
                      id="url"
                      type="url"
                      placeholder="https://example.com/hail-photo.jpg"
                      value={imageUrl}
                      onChange={(e) => setImageUrl(e.target.value)}
                    />
                    <Button onClick={handleUrlLoad} variant="secondary">
                      Load
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Image Preview */}
            {imagePreview && (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="w-full rounded-lg border object-contain max-h-80"
                />
                <Button
                  variant="destructive"
                  size="sm"
                  className="absolute top-2 right-2"
                  onClick={clearImage}
                >
                  Clear
                </Button>
              </div>
            )}

            {/* Analyze Button */}
            <Button
              onClick={handleAnalyze}
              disabled={!imageBase64 || analysisMutation.isPending}
              className="w-full"
              size="lg"
            >
              {analysisMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Analyze Photo
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CloudRain className="h-5 w-5" />
              Analysis Results
            </CardTitle>
            <CardDescription>
              AI-detected hail size and photo authenticity
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
                <CloudRain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Upload a photo and click "Analyze" to get results</p>
              </div>
            )}

            {analysisMutation.isPending && (
              <div className="text-center py-12">
                <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-blue-500" />
                <p className="text-muted-foreground">Analyzing photo with AI...</p>
              </div>
            )}

            {result && (
              <div className="space-y-6">
                {/* Hail Detection */}
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Ruler className="h-4 w-4" />
                    Hail Detection
                  </h4>

                  {result.hail_detected ? (
                    <div className="space-y-3">
                      <Alert className="border-green-500 bg-green-500/10">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                        <AlertTitle>Hail Detected</AlertTitle>
                        <AlertDescription>
                          AI has detected hail in this image
                        </AlertDescription>
                      </Alert>

                      {/* Size Category */}
                      {sizeInfo && (
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted">
                          <div className={`w-4 h-4 rounded-full ${sizeInfo.color}`} />
                          <div>
                            <p className="font-semibold text-lg">{sizeInfo.label}</p>
                            <p className="text-sm text-muted-foreground">
                              Approximately {sizeInfo.range} ({result.estimated_size_inches?.toFixed(2)}" measured)
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Severity */}
                      {result.severity && (
                        <div className="flex items-center gap-2">
                          <span className="text-sm">Severity:</span>
                          <Badge className={SEVERITY_COLORS[result.severity] || "bg-gray-500"}>
                            {result.severity.charAt(0).toUpperCase() + result.severity.slice(1)}
                          </Badge>
                        </div>
                      )}

                      {/* Confidence */}
                      {result.size_confidence !== undefined && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>Confidence</span>
                            <span>{result.size_confidence.toFixed(1)}%</span>
                          </div>
                          <Progress value={result.size_confidence} className="h-2" />
                        </div>
                      )}
                    </div>
                  ) : (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle>No Hail Detected</AlertTitle>
                      <AlertDescription>
                        AI did not detect hail in this image. Try uploading a clearer photo.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>

                {/* Photo Authenticity */}
                {result.analyzed_authenticity && (
                  <div className="space-y-3 pt-4 border-t">
                    <h4 className="font-medium flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      Photo Authenticity
                    </h4>

                    {result.is_authentic ? (
                      <Alert className="border-green-500 bg-green-500/10">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                        <AlertTitle>Appears Authentic</AlertTitle>
                        <AlertDescription>
                          No signs of AI generation or manipulation detected
                        </AlertDescription>
                      </Alert>
                    ) : (
                      <Alert variant="destructive">
                        <XCircle className="h-4 w-4" />
                        <AlertTitle>Potential Issues Detected</AlertTitle>
                        <AlertDescription>
                          This photo may be manipulated or AI-generated
                        </AlertDescription>
                      </Alert>
                    )}

                    {result.authenticity_confidence !== undefined && (
                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>Authenticity Confidence</span>
                          <span>{result.authenticity_confidence.toFixed(1)}%</span>
                        </div>
                        <Progress value={result.authenticity_confidence} className="h-2" />
                      </div>
                    )}

                    {result.manipulation_indicators && result.manipulation_indicators.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-sm text-muted-foreground">Indicators:</span>
                        <div className="flex flex-wrap gap-1">
                          {result.manipulation_indicators.map((indicator, i) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {indicator}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Size Reference Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Hail Size Reference Chart</CardTitle>
          <CardDescription>
            Standard hail size categories used by the National Weather Service
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {Object.entries(SIZE_CATEGORIES).map(([key, info]) => (
              <div
                key={key}
                className="flex items-center gap-2 p-2 rounded-lg border bg-muted/50"
              >
                <div className={`w-3 h-3 rounded-full ${info.color}`} />
                <div>
                  <p className="font-medium text-sm">{info.label}</p>
                  <p className="text-xs text-muted-foreground">{info.range}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
