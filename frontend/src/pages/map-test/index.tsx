import { useEffect, useRef, useState } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

// Fix Leaflet default marker icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

export function MapTestPage() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [status, setStatus] = useState("Initializing...")

  useEffect(() => {
    if (!mapRef.current) {
      setStatus("ERROR: No map container ref")
      return
    }

    if (mapInstanceRef.current) {
      setStatus("Map already exists")
      return
    }

    const container = mapRef.current
    setStatus(`Container: ${container.offsetWidth}x${container.offsetHeight}`)

    try {
      // Create map
      const map = L.map(container, {
        center: [39.8283, -98.5795],
        zoom: 4,
      })

      // Add tile layer
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap',
      }).addTo(map)

      // Add a marker
      L.marker([39.8283, -98.5795])
        .addTo(map)
        .bindPopup("Center of USA")

      mapInstanceRef.current = map
      setStatus("Map created successfully!")

      // Invalidate size after short delay
      setTimeout(() => {
        map.invalidateSize()
        setStatus("Map ready - invalidateSize called")
      }, 200)

    } catch (error) {
      setStatus(`ERROR: ${error}`)
      console.error("Map init error:", error)
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Map Test Page</h1>
      <p className="mb-4">Status: {status}</p>

      {/* Map container with explicit fixed dimensions */}
      <div
        ref={mapRef}
        style={{
          width: "100%",
          height: "600px",
          border: "2px solid red",
          background: "#ccc",
        }}
      />

      <style>{`
        .leaflet-container {
          width: 100% !important;
          height: 100% !important;
          z-index: 1;
        }
      `}</style>
    </div>
  )
}
