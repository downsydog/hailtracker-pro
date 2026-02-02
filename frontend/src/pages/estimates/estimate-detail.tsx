import * as React from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useEstimate, useDeleteEstimate } from "@/hooks/use-estimates"
import { estimatesApi, EstimatePhoto } from "@/api/estimates"
import { EstimateLineItem } from "@/types"
import {
  ArrowLeft,
  Edit,
  Trash2,
  Send,
  Check,
  X,
  FileText,
  User,
  Car,
  Download,
  Camera,
  Image as ImageIcon,
} from "lucide-react"

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  DRAFT: "secondary",
  SENT: "outline",
  APPROVED: "default",
  REJECTED: "destructive",
}

export function EstimateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: estimate, isLoading, refetch } = useEstimate(Number(id))
  const deleteEstimate = useDeleteEstimate()
  const [photos, setPhotos] = React.useState<EstimatePhoto[]>([])
  const [photosLoading, setPhotosLoading] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  // Load photos on mount
  React.useEffect(() => {
    if (id) {
      loadPhotos()
    }
  }, [id])

  const loadPhotos = async () => {
    setPhotosLoading(true)
    try {
      const result = await estimatesApi.getPhotos(Number(id))
      setPhotos(result.photos || [])
    } catch {
      console.log("Photos not available")
    } finally {
      setPhotosLoading(false)
    }
  }

  const handleSend = async () => {
    try {
      await estimatesApi.send(Number(id))
      refetch()
    } catch (error) {
      console.error("Failed to send estimate:", error)
    }
  }

  const handleApprove = async () => {
    try {
      await estimatesApi.approve(Number(id))
      refetch()
    } catch (error) {
      console.error("Failed to approve estimate:", error)
    }
  }

  const handleDecline = async () => {
    try {
      await estimatesApi.decline(Number(id))
      refetch()
    } catch (error) {
      console.error("Failed to decline estimate:", error)
    }
  }

  const handleConvertToJob = async () => {
    if (confirm("Convert this estimate to a job?")) {
      try {
        const result = await estimatesApi.convertToJob(Number(id))
        navigate(`/jobs/${result.job_id}`)
      } catch (error) {
        console.error("Failed to convert estimate:", error)
      }
    }
  }

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this estimate?")) {
      try {
        await deleteEstimate.mutateAsync(Number(id))
        navigate("/estimates")
      } catch (error) {
        console.error("Failed to delete estimate:", error)
      }
    }
  }

  const handleExportPdf = async () => {
    try {
      const blob = await estimatesApi.exportPdf(Number(id))
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `estimate-${estimate?.estimate_number || id}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error("Failed to export PDF:", error)
    }
  }

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return

    for (const file of Array.from(files)) {
      try {
        await estimatesApi.uploadPhoto(Number(id), file)
      } catch (error) {
        console.error("Failed to upload photo:", error)
      }
    }
    loadPhotos()
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleDeletePhoto = async (photoId: number) => {
    if (confirm("Delete this photo?")) {
      try {
        await estimatesApi.deletePhoto(Number(id), photoId)
        loadPhotos()
      } catch (error) {
        console.error("Failed to delete photo:", error)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (!estimate) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Estimate not found</h2>
        <Button variant="link" onClick={() => navigate("/estimates")}>
          Back to estimates
        </Button>
      </div>
    )
  }

  const items = (estimate as { items?: EstimateLineItem[] }).items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/estimates")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <PageHeader
            title={`Estimate ${estimate.estimate_number}`}
            description={`Created on ${new Date(estimate.created_at).toLocaleDateString()}`}
          />
          <Badge variant={statusColors[estimate.status] || "outline"}>
            {estimate.status}
          </Badge>
        </div>
        <div className="flex gap-2">
          {estimate.status === "DRAFT" && (
            <Button onClick={handleSend}>
              <Send className="h-4 w-4 mr-2" />
              Send
            </Button>
          )}
          {estimate.status === "SENT" && (
            <>
              <Button onClick={handleApprove} variant="default">
                <Check className="h-4 w-4 mr-2" />
                Approve
              </Button>
              <Button onClick={handleDecline} variant="destructive">
                <X className="h-4 w-4 mr-2" />
                Decline
              </Button>
            </>
          )}
          {estimate.status === "APPROVED" && (
            <Button onClick={handleConvertToJob}>
              <FileText className="h-4 w-4 mr-2" />
              Convert to Job
            </Button>
          )}
          <Button variant="outline" onClick={handleExportPdf}>
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          <Button variant="outline" onClick={() => navigate(`/estimates/${id}/edit`)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Line Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Service</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">Unit Price</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length > 0 ? (
                  items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.service_type}</TableCell>
                      <TableCell>{item.description}</TableCell>
                      <TableCell className="text-right">{item.quantity}</TableCell>
                      <TableCell className="text-right">
                        ${item.unit_price.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right">${item.total.toFixed(2)}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No line items
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            <div className="mt-6 flex justify-end">
              <div className="w-64 space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal:</span>
                  <span>${estimate.subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tax:</span>
                  <span>${estimate.tax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-bold text-lg border-t pt-2">
                  <span>Total:</span>
                  <span>${estimate.total.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent>
              {estimate.customer_id ? (
                <div>
                  <p className="font-medium">{estimate.customer_name}</p>
                  <Button variant="link" className="px-0 mt-2" asChild>
                    <Link to={`/customers/${estimate.customer_id}`}>View customer</Link>
                  </Button>
                </div>
              ) : (
                <p className="text-muted-foreground">No customer assigned</p>
              )}
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
              {estimate.vehicle_id ? (
                <div>
                  <p className="font-medium">
                    {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                  </p>
                  <Button variant="link" className="px-0 mt-2" asChild>
                    <Link to={`/vehicles/${estimate.vehicle_id}`}>View vehicle</Link>
                  </Button>
                </div>
              ) : (
                <p className="text-muted-foreground">No vehicle assigned</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created:</span>
                <span>{new Date(estimate.created_at).toLocaleDateString()}</span>
              </div>
              {estimate.sent_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Sent:</span>
                  <span>{new Date(estimate.sent_at).toLocaleDateString()}</span>
                </div>
              )}
              {estimate.approved_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Approved:</span>
                  <span>{new Date(estimate.approved_at).toLocaleDateString()}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Photos Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Photos
          </CardTitle>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handlePhotoUpload}
              className="hidden"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
            >
              <Camera className="h-4 w-4 mr-2" />
              Upload Photos
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {photosLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : photos.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {photos.map((photo) => (
                <div key={photo.id} className="relative group">
                  <div className="aspect-square rounded-lg overflow-hidden border bg-muted">
                    <img
                      src={photo.url}
                      alt={photo.description || "Estimate photo"}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <Button
                    variant="destructive"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDeletePhoto(photo.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                  {photo.description && (
                    <p className="text-xs text-muted-foreground mt-1 truncate">
                      {photo.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center">
              <ImageIcon className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <p className="font-medium">No photos yet</p>
              <p className="text-sm text-muted-foreground">
                Upload photos of the damage to include with this estimate
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
