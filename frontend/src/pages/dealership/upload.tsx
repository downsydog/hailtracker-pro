import * as React from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { dealershipApi, BatchUploadResult, DealerLocation } from "@/api/dealership"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
  Upload,
  FileSpreadsheet,
  Download,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Loader2,
} from "lucide-react"

const DEMO_LOCATIONS: DealerLocation[] = [
  { id: 1, dealership_id: 1, name: "Main Lot - Downtown", address: "123 Main St", city: "Denver", state: "CO", zip: "80202", is_primary: true, vehicles_count: 28, active_jobs: 5 },
  { id: 2, dealership_id: 1, name: "North Campus", address: "456 North Ave", city: "Denver", state: "CO", zip: "80203", is_primary: false, vehicles_count: 12, active_jobs: 3 },
]

const REQUIRED_COLUMNS = [
  { name: "stock_number", description: "Unique stock/inventory number", example: "A12345" },
  { name: "vin", description: "17-character Vehicle Identification Number", example: "1HGBH41JXMN109186" },
  { name: "year", description: "Model year (4 digits)", example: "2024" },
  { name: "make", description: "Vehicle manufacturer", example: "Honda" },
  { name: "model", description: "Vehicle model name", example: "Accord" },
]

const OPTIONAL_COLUMNS = [
  { name: "trim", description: "Trim level", example: "EX-L" },
  { name: "color", description: "Exterior color", example: "White" },
  { name: "mileage", description: "Odometer reading", example: "12500" },
  { name: "damage_type", description: "Type of damage", example: "Hail Damage" },
  { name: "damage_description", description: "Detailed damage description", example: "Light dents on hood" },
  { name: "estimated_repair_cost", description: "Estimated repair cost", example: "1250.00" },
]

export function DealershipUploadPage() {
  const dealershipId = 1
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
  const [selectedLocation, setSelectedLocation] = React.useState<string>("")
  const [uploadResult, setUploadResult] = React.useState<BatchUploadResult | null>(null)
  const [dragActive, setDragActive] = React.useState(false)

  const { data: locationsData } = useQuery({
    queryKey: ["dealership", dealershipId, "locations"],
    queryFn: () => dealershipApi.getLocations(dealershipId),
    placeholderData: { locations: DEMO_LOCATIONS },
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file, locationId }: { file: File; locationId?: number }) =>
      dealershipApi.uploadVehicles(dealershipId, file, locationId),
    onSuccess: (result) => {
      setUploadResult(result)
      setSelectedFile(null)
    },
  })

  const downloadTemplateMutation = useMutation({
    mutationFn: () => dealershipApi.downloadTemplate(),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "vehicle_upload_template.csv"
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const locations = locationsData?.locations ?? DEMO_LOCATIONS

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = (file: File) => {
    const validTypes = [
      "text/csv",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]
    if (!validTypes.includes(file.type) && !file.name.endsWith(".csv")) {
      alert("Please upload a CSV or Excel file")
      return
    }
    setSelectedFile(file)
    setUploadResult(null)
  }

  const handleUpload = () => {
    if (!selectedFile) return

    uploadMutation.mutate({
      file: selectedFile,
      locationId: selectedLocation ? parseInt(selectedLocation) : undefined,
    })
  }

  const resetUpload = () => {
    setSelectedFile(null)
    setUploadResult(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <div className="space-y-6">
      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            Batch Vehicle Upload
          </CardTitle>
          <CardDescription>
            Upload multiple vehicles at once using a CSV or Excel file
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                Download our template to ensure your data is formatted correctly
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => downloadTemplateMutation.mutate()}
              disabled={downloadTemplateMutation.isPending}
            >
              <Download className="h-4 w-4 mr-2" />
              Download Template
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Upload Area */}
      {!uploadResult && (
        <Card>
          <CardContent className="pt-6">
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? "border-primary bg-primary/5"
                  : selectedFile
                  ? "border-green-500 bg-green-50"
                  : "border-muted-foreground/25 hover:border-primary/50"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              {selectedFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center gap-3">
                    <FileText className="h-8 w-8 text-green-600" />
                    <div className="text-left">
                      <p className="font-medium">{selectedFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(selectedFile.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-4">
                    <Select value={selectedLocation} onValueChange={setSelectedLocation}>
                      <SelectTrigger className="w-[250px]">
                        <SelectValue placeholder="Assign to location (optional)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">No location</SelectItem>
                        {locations.map((loc) => (
                          <SelectItem key={loc.id} value={loc.id.toString()}>
                            {loc.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center justify-center gap-3">
                    <Button variant="outline" onClick={resetUpload}>
                      Choose Different File
                    </Button>
                    <Button onClick={handleUpload} disabled={uploadMutation.isPending}>
                      {uploadMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          Upload Vehicles
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
                      <Upload className="h-8 w-8 text-muted-foreground" />
                    </div>
                  </div>
                  <div>
                    <p className="text-lg font-medium">
                      Drag and drop your file here
                    </p>
                    <p className="text-sm text-muted-foreground">
                      or click to browse
                    </p>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    className="hidden"
                    onChange={handleFileSelect}
                  />
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Select File
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Supported formats: CSV, XLSX, XLS
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Result */}
      {uploadResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {uploadResult.success ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
              )}
              Upload Complete
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary */}
            <div className="grid gap-4 sm:grid-cols-4">
              <div className="p-4 bg-muted rounded-lg text-center">
                <div className="text-2xl font-bold">{uploadResult.total_rows}</div>
                <div className="text-sm text-muted-foreground">Total Rows</div>
              </div>
              <div className="p-4 bg-green-100 rounded-lg text-center">
                <div className="text-2xl font-bold text-green-700">
                  {uploadResult.imported}
                </div>
                <div className="text-sm text-green-600">Imported</div>
              </div>
              <div className="p-4 bg-red-100 rounded-lg text-center">
                <div className="text-2xl font-bold text-red-700">
                  {uploadResult.failed}
                </div>
                <div className="text-sm text-red-600">Failed</div>
              </div>
              <div className="p-4 bg-muted rounded-lg text-center">
                <Progress
                  value={((uploadResult.imported ?? 0) / (uploadResult.total_rows ?? 1)) * 100}
                  className="mt-2"
                />
                <div className="text-sm text-muted-foreground mt-1">
                  {(((uploadResult.imported ?? 0) / (uploadResult.total_rows ?? 1)) * 100).toFixed(0)}% Success
                </div>
              </div>
            </div>

            {/* Errors */}
            {(uploadResult.errors?.length ?? 0) > 0 && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Import Errors</AlertTitle>
                <AlertDescription>
                  <div className="mt-2 max-h-40 overflow-y-auto">
                    {uploadResult.errors?.map((error, index) => (
                      <div key={index} className="text-sm">
                        {typeof error === 'string' ? error : `Row ${error.row}: ${error.error}`}
                      </div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Imported Vehicles Preview */}
            {(uploadResult.vehicles?.length ?? 0) > 0 && (
              <div>
                <h3 className="font-medium mb-2">Imported Vehicles</h3>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Stock #</TableHead>
                        <TableHead>Vehicle</TableHead>
                        <TableHead>VIN</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {uploadResult.vehicles?.slice(0, 5).map((vehicle) => (
                        <TableRow key={vehicle.id}>
                          <TableCell className="font-medium">
                            {vehicle.stock_number}
                          </TableCell>
                          <TableCell>
                            {vehicle.year} {vehicle.make} {vehicle.model}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {vehicle.vin}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">Imported</Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {(uploadResult.vehicles?.length ?? 0) > 5 && (
                    <div className="p-3 text-center text-sm text-muted-foreground bg-muted">
                      And {(uploadResult.vehicles?.length ?? 0) - 5} more vehicles...
                    </div>
                  )}
                </div>
              </div>
            )}

            <Button onClick={resetUpload}>Upload Another File</Button>
          </CardContent>
        </Card>
      )}

      {/* Column Reference */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Required Columns</CardTitle>
            <CardDescription>
              These columns must be present in your file
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Example</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {REQUIRED_COLUMNS.map((col) => (
                  <TableRow key={col.name}>
                    <TableCell className="font-mono text-sm font-medium">
                      {col.name}
                    </TableCell>
                    <TableCell className="text-sm">{col.description}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {col.example}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Optional Columns</CardTitle>
            <CardDescription>
              Additional data you can include
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Example</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {OPTIONAL_COLUMNS.map((col) => (
                  <TableRow key={col.name}>
                    <TableCell className="font-mono text-sm font-medium">
                      {col.name}
                    </TableCell>
                    <TableCell className="text-sm">{col.description}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {col.example}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
