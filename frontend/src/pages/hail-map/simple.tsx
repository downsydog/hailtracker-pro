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
}

export default function SimpleHailMap() {
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [events, setEvents] = useState<HailEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const loadEvents = async (date: string) => {
    if (!date) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/hail-events?event_date=${date}&limit=500`, {
        credentials: 'include'
      });
      const data = await res.json();
      console.log('Loaded events:', data.events?.length, 'for date:', date);
      console.log('Event dates:', [...new Set(data.events?.map((e: HailEvent) => e.event_date?.slice(0,10)))]);
      setEvents(data.events || []);
    } catch (err) {
      console.error('Failed to load events:', err);
    }
    setLoading(false);
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="p-4 bg-gray-100 flex gap-4 items-center">
        <label>Select Date:</label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => {
            setSelectedDate(e.target.value);
            loadEvents(e.target.value);
          }}
          className="border p-2 rounded"
        />
        <span>{loading ? 'Loading...' : `${events.length} storms`}</span>
      </div>

      <MapContainer center={[39, -98]} zoom={4} className="flex-1">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {events.map(event => {
          const lat = event.center_lat ?? event.latitude;
          const lon = event.center_lon ?? event.longitude;
          if (!lat || !lon) return null;

          return (
            <Circle
              key={event.id}
              center={[lat, lon]}
              radius={Math.max((event.max_hail_size || 1) * 5000, 5000)}
              pathOptions={{
                color: 'red',
                fillColor: 'red',
                fillOpacity: 0.3,
              }}
            >
              <Popup>
                <div>
                  <strong>{event.event_name || event.location_name || 'Storm'}</strong><br/>
                  Date: {event.event_date}<br/>
                  Hail: {event.max_hail_size || 'N/A'}"
                </div>
              </Popup>
            </Circle>
          );
        })}
      </MapContainer>
    </div>
  );
}
