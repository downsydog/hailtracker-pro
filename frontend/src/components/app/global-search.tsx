import * as React from "react"
import { useNavigate } from "react-router-dom"
import { Input } from "@/components/ui/input"
import { searchApi, SearchResult } from "@/api/search"
import { cn } from "@/lib/utils"
import { Search, Briefcase, Users, Car, FileText, Loader2 } from "lucide-react"
import { useDebounce } from "@/hooks/use-debounce"

const typeIcons = {
  job: Briefcase,
  customer: Users,
  vehicle: Car,
  estimate: FileText,
}

const typeLabels = {
  job: "Job",
  customer: "Customer",
  vehicle: "Vehicle",
  estimate: "Estimate",
}

export function GlobalSearch() {
  const navigate = useNavigate()
  const [query, setQuery] = React.useState("")
  const [results, setResults] = React.useState<SearchResult[]>([])
  const [isOpen, setIsOpen] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const [selectedIndex, setSelectedIndex] = React.useState(-1)
  const inputRef = React.useRef<HTMLInputElement>(null)
  const containerRef = React.useRef<HTMLDivElement>(null)

  const debouncedQuery = useDebounce(query, 300)

  React.useEffect(() => {
    async function search() {
      if (!debouncedQuery || debouncedQuery.length < 2) {
        setResults([])
        return
      }

      setIsLoading(true)
      try {
        const data = await searchApi.globalSearch({ query: debouncedQuery })
        setResults(data.results || [])
      } catch (error) {
        console.error("Search error:", error)
        setResults([])
      } finally {
        setIsLoading(false)
      }
    }

    search()
  }, [debouncedQuery])

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) return

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0))
        break
      case "ArrowUp":
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1))
        break
      case "Enter":
        e.preventDefault()
        if (selectedIndex >= 0 && results[selectedIndex]) {
          handleResultClick(results[selectedIndex])
        }
        break
      case "Escape":
        setIsOpen(false)
        inputRef.current?.blur()
        break
    }
  }

  const handleResultClick = (result: SearchResult) => {
    setIsOpen(false)
    setQuery("")
    navigate(result.url)
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="search"
          placeholder="Search jobs, customers, vehicles..."
          className="pl-9 pr-4"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setIsOpen(true)
            setSelectedIndex(-1)
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
        )}
      </div>

      {isOpen && (query.length >= 2 || results.length > 0) && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-popover border rounded-md shadow-lg overflow-hidden z-50">
          {results.length > 0 ? (
            <ul className="py-1 max-h-80 overflow-y-auto">
              {results.map((result, index) => {
                const Icon = typeIcons[result.type as keyof typeof typeIcons] || Search
                return (
                  <li key={`${result.type}-${result.id}`}>
                    <button
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-muted transition-colors",
                        index === selectedIndex && "bg-muted"
                      )}
                      onClick={() => handleResultClick(result)}
                    >
                      <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{result.title}</p>
                        {result.subtitle && (
                          <p className="text-xs text-muted-foreground truncate">
                            {result.subtitle}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {typeLabels[result.type as keyof typeof typeLabels] || result.type}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : query.length >= 2 && !isLoading ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No results found for "{query}"
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
