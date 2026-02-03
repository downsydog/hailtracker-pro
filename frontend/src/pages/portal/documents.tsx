import * as React from "react"
import { portalApi, PortalDocument } from "@/api/portal"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  FileText,
  Download,
  Search,
  FileSpreadsheet,
  FileImage,
  File,
  Shield,
  Receipt,
} from "lucide-react"

const documentTypeIcons: Record<string, React.ElementType> = {
  estimate: FileSpreadsheet,
  invoice: Receipt,
  insurance: Shield,
  photo: FileImage,
  other: File,
}

const documentTypeColors: Record<string, string> = {
  estimate: "bg-blue-100 text-blue-600",
  invoice: "bg-green-100 text-green-600",
  insurance: "bg-purple-100 text-purple-600",
  photo: "bg-orange-100 text-orange-600",
  other: "bg-gray-100 text-gray-600",
}

export function PortalDocumentsPage() {
  const [documents, setDocuments] = React.useState<PortalDocument[]>([])
  const [loading, setLoading] = React.useState(true)
  const [search, setSearch] = React.useState("")
  const [filter, setFilter] = React.useState<string>("all")

  React.useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const result = await portalApi.getDocuments()
        setDocuments(result.documents)
      } catch {
        // Demo data
        setDocuments([
          {
            id: 1,
            type: "estimate",
            name: "Initial Estimate - JOB-2025-001",
            url: "#",
            created_at: "2025-01-20",
          },
          {
            id: 2,
            type: "insurance",
            name: "Insurance Authorization",
            url: "#",
            created_at: "2025-01-21",
          },
          {
            id: 3,
            type: "estimate",
            name: "Supplement Estimate - JOB-2025-001",
            url: "#",
            created_at: "2025-01-22",
          },
          {
            id: 4,
            type: "invoice",
            name: "Final Invoice - JOB-2024-089",
            url: "#",
            created_at: "2024-12-15",
          },
          {
            id: 5,
            type: "insurance",
            name: "Insurance Claim Summary",
            url: "#",
            created_at: "2024-12-10",
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchDocuments()
  }, [])

  const handleDownload = async (doc: PortalDocument) => {
    try {
      const blob = await portalApi.downloadDocument(doc.id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = doc.name + ".pdf"
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error("Failed to download document:", error)
    }
  }

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.name.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === "all" || doc.type === filter
    return matchesSearch && matchesFilter
  })

  const documentTypes = ["all", ...new Set(documents.map((d) => d.type))]

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
        <h1 className="text-2xl font-bold">Documents</h1>
        <p className="text-muted-foreground">
          Access your estimates, invoices, and other documents
        </p>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
          {documentTypes.map((type) => (
            <Button
              key={type}
              variant={filter === type ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(type)}
              className="capitalize whitespace-nowrap"
            >
              {type}
            </Button>
          ))}
        </div>
      </div>

      {/* Documents List */}
      <Card>
        <CardContent className="p-0">
          {filteredDocuments.length > 0 ? (
            <div className="divide-y">
              {filteredDocuments.map((doc) => {
                const Icon = documentTypeIcons[doc.type] || FileText
                const colorClass = documentTypeColors[doc.type] || documentTypeColors.other

                return (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-4 hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${colorClass}`}>
                        <Icon className="h-6 w-6" />
                      </div>
                      <div>
                        <h3 className="font-medium">{doc.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="capitalize text-xs">
                            {doc.type}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(doc.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDownload(doc)}
                    >
                      <Download className="h-5 w-5" />
                    </Button>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="py-12 text-center">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <h3 className="font-medium mb-1">No Documents Found</h3>
              <p className="text-sm text-muted-foreground">
                {search || filter !== "all"
                  ? "Try adjusting your search or filters"
                  : "Your documents will appear here"}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
