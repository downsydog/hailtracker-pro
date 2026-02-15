import { useState } from 'react';
import { MapContainer, TileLayer, Circle, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface HailEvent {
  id: number;
  latitude: number;
  longitude: number;
  center_lat?: number;
  center_lon?: number;
  event_date: string;
  event_name?: string;
  location_name?: string;
  max_hail_size?: number;
  confidence_score?: number;
  evidence_mrms?: number;
  evidence_dualpol?: number;
  evidence_multi_radar?: number;
  evidence_persistence?: number;
  data_source?: string;
}

export default function SimpleHailMap() {
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [events, setEvents] = useState<HailEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [minConfidence, setMinConfidence] = useState<number>(45);

  const loadEvents = async (date: string) => {
    if (!date) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/hail-events?event_date=${date}&limit=500`, {
        credentials: 'include'
      });
      const data = await res.json();
      console.log('Loaded events:', data.events?.length, 'for date:', date);
      setEvents(data.events || []);
    } catch (err) {
      console.error('Failed to load events:', err);
    }
    setLoading(false);
  };

  const filteredEvents = events.filter(e => {
    const conf = e.confidence_score ?? 100;
    return conf >= minConfidence;
  });

  return (
    <div className="h-screen flex flex-col">
      <div className="p-4 bg-gray-100 flex gap-4 items-center flex-wrap">
        <label>Date:</label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => {
            setSelectedDate(e.target.value);
            loadEvents(e.target.value);
          }}
          className="border p-2 rounded"
        />
        <label>Min Confidence:</label>
        <input
          type="range"
          min={0}
          max={100}
          value={minConfidence}
          onChange={(e) => setMinConfidence(Number(e.target.value))}
          className="w-32"
        />
        <span className="text-sm font-mono">{minConfidence}</span>
        <span className="text-sm text-gray-600">
          {loading ? 'Loading...' : `${filteredEvents.length}/${events.length} storms`}
        </span>
      </div>

      <MapContainer center={[39, -98]} zoom={4} className="flex-1">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {filteredEvents.map(event => {
          const lat = event.center_lat ?? event.latitude;
          const lon = event.center_lon ?? event.longitude;
          if (!lat || !lon) return null;

          const conf = event.confidence_score ?? 0;
          const color = conf >= 70 ? '#dc2626' : conf >= 45 ? '#f59e0b' : '#9ca3af';

          return (
            <Circle
              key={event.id}
              center={[lat, lon]}
              radius={Math.max((event.max_hail_size || 1) * 5000, 5000)}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: 0.3,
              }}
            >
              <Popup>
                <div className="text-sm">
                  <strong>{event.event_name || event.location_name || 'Storm'}</strong><br/>
                  Date: {event.event_date}<br/>
                  Hail: {event.max_hail_size || 'N/A'}"<br/>
                  Confidence: {conf}<br/>
                  {event.evidence_mrms ? 'MRMS ' : ''}
                  {event.evidence_dualpol ? 'DualPol ' : ''}
                  {event.evidence_multi_radar ? 'MultiRadar ' : ''}
                  {event.evidence_persistence ? 'Persistent ' : ''}
                </div>
              </Popup>
            </Circle>
          );
        })}
      </MapContainer>
    </div>
  );
}
