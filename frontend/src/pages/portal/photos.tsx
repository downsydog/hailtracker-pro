import * as React from "react"
import { useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { portalApi, PortalPhoto } from "@/api/portal"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog"
import { Image, X, ChevronLeft, ChevronRight } from "lucide-react"

const photoTypeLabels: Record<string, string> = {
  before: "Before Repair",
  during: "During Repair",
  after: "After Repair",
}

const photoTypeColors: Record<string, string> = {
  before: "bg-red-100 text-red-800",
  during: "bg-yellow-100 text-yellow-800",
  after: "bg-green-100 text-green-800",
}

export function PortalPhotosPage() {
  const [searchParams] = useSearchParams()
  const jobFilter = searchParams.get("job_id")
  const [selectedJob, setSelectedJob] = React.useState<string>(jobFilter || "all")
  const [selectedType, setSelectedType] = React.useState<string>("all")
  const [lightboxOpen, setLightboxOpen] = React.useState(false)
  const [currentPhotoIndex, setCurrentPhotoIndex] = React.useState(0)

  // Fetch jobs list
  const { data: jobsData } = useQuery({
    queryKey: ["portal-jobs"],
    queryFn: () => portalApi.getJobs(),
  })
  const jobs = jobsData?.jobs || []

  // Fetch photos for selected job
  const { data: photosData, isLoading: loading } = useQuery({
    queryKey: ["portal-photos", selectedJob],
    queryFn: async () => {
      if (selectedJob !== "all") {
        return portalApi.getPhotos(Number(selectedJob))
      } else {
        // Fetch photos for first 3 jobs
        const allPhotos: PortalPhoto[] = []
        for (const job of jobs.slice(0, 3)) {
          try {
            const result = await portalApi.getPhotos(job.id)
            allPhotos.push(...result.photos)
          } catch {
            // Skip if no photos
          }
        }
        return { photos: allPhotos }
      }
    },
    enabled: selectedJob !== "all" || jobs.length > 0,
  })
  const photos = photosData?.photos || []

  const filteredPhotos = photos.filter((photo) => {
    return selectedType === "all" || photo.type === selectedType
  })

  const openLightbox = (index: number) => {
    setCurrentPhotoIndex(index)
    setLightboxOpen(true)
  }

  const navigatePhoto = (direction: "prev" | "next") => {
    if (direction === "prev") {
      setCurrentPhotoIndex((prev) =>
        prev === 0 ? filteredPhotos.length - 1 : prev - 1
      )
    } else {
      setCurrentPhotoIndex((prev) =>
        prev === filteredPhotos.length - 1 ? 0 : prev + 1
      )
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Photos</h1>
        <p className="text-muted-foreground">
          View before, during, and after photos of your repairs
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Select value={selectedJob} onValueChange={setSelectedJob}>
          <SelectTrigger className="w-full sm:w-[250px]">
            <SelectValue placeholder="Select job" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Jobs</SelectItem>
            {jobs.map((job) => (
              <SelectItem key={job.id} value={job.id.toString()}>
                {job.job_number} - {job.vehicle_year} {job.vehicle_make}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex gap-2">
          {["all", "before", "during", "after"].map((type) => (
            <Button
              key={type}
              variant={selectedType === type ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedType(type)}
              className="capitalize"
            >
              {type === "all" ? "All" : photoTypeLabels[type]}
            </Button>
          ))}
        </div>
      </div>

      {/* Photo Grid */}
      {filteredPhotos.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredPhotos.map((photo, index) => (
            <div
              key={photo.id}
              className="group relative cursor-pointer"
              onClick={() => openLightbox(index)}
            >
              <div className="aspect-square rounded-lg overflow-hidden bg-gray-100 border">
                <img
                  src={photo.url}
                  alt={photo.description || "Repair photo"}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src =
                      "https://via.placeholder.com/400?text=Photo"
                  }}
                />
              </div>
              <Badge
                className={`absolute top-2 left-2 text-xs ${photoTypeColors[photo.type] || "bg-gray-100"}`}
              >
                {photoTypeLabels[photo.type] || photo.type}
              </Badge>
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors rounded-lg" />
            </div>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Image className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="font-medium mb-1">No Photos Found</h3>
            <p className="text-sm text-muted-foreground">
              Photos will appear here as work progresses on your vehicle
            </p>
          </CardContent>
        </Card>
      )}

      {/* Lightbox */}
      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent className="max-w-4xl p-0 bg-black">
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 z-10 text-white hover:bg-white/20"
              onClick={() => setLightboxOpen(false)}
            >
              <X className="h-6 w-6" />
            </Button>

            {filteredPhotos.length > 1 && (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute left-2 top-1/2 -translate-y-1/2 z-10 text-white hover:bg-white/20"
                  onClick={() => navigatePhoto("prev")}
                >
                  <ChevronLeft className="h-8 w-8" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-1/2 -translate-y-1/2 z-10 text-white hover:bg-white/20"
                  onClick={() => navigatePhoto("next")}
                >
                  <ChevronRight className="h-8 w-8" />
                </Button>
              </>
            )}

            <img
              src={filteredPhotos[currentPhotoIndex]?.url}
              alt={filteredPhotos[currentPhotoIndex]?.description || "Photo"}
              className="w-full h-auto max-h-[80vh] object-contain"
            />

            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
              <div className="flex items-center justify-between text-white">
                <div>
                  <Badge className={photoTypeColors[filteredPhotos[currentPhotoIndex]?.type] || ""}>
                    {photoTypeLabels[filteredPhotos[currentPhotoIndex]?.type] ||
                      filteredPhotos[currentPhotoIndex]?.type}
                  </Badge>
                  <p className="mt-2 text-sm">
                    {filteredPhotos[currentPhotoIndex]?.description}
                  </p>
                  <p className="text-xs text-white/70 mt-1">
                    {new Date(filteredPhotos[currentPhotoIndex]?.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
                <p className="text-sm">
                  {currentPhotoIndex + 1} / {filteredPhotos.length}
                </p>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
