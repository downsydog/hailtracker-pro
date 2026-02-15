import { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Circle, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
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

interface CalendarDay {
  count: number;
  max_hail_size: number;
  max_severity: string;
  events: Array<{
    id: number;
    event_name: string;
    hail_size: number;
    severity: string;
    lat: number;
    lon: number;
    bbox_min_lat?: number;
    bbox_max_lat?: number;
    bbox_min_lon?: number;
    bbox_max_lon?: number;
  }>;
}

function MapFitter({ events }: { events: HailEvent[] }) {
  const map = useMap();
  useEffect(() => {
    if (events.length === 0) return;
    const lats: number[] = [];
    const lons: number[] = [];
    for (const ev of events) {
      const lat = ev.center_lat ?? ev.latitude;
      const lon = ev.center_lon ?? ev.longitude;
      if (lat && lon) {
        lats.push(lat);
        lons.push(lon);
      }
    }
    if (lats.length === 0) return;
    const bounds = L.latLngBounds(
      [Math.min(...lats) - 0.5, Math.min(...lons) - 0.5],
      [Math.max(...lats) + 0.5, Math.max(...lons) + 0.5]
    );
    map.fitBounds(bounds, { maxZoom: 10 });
  }, [events, map]);
  return null;
}

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DAY_NAMES = ['Su','Mo','Tu','We','Th','Fr','Sa'];
const SEVERITY_COLORS: Record<string, string> = {
  CATASTROPHIC: '#7c3aed',
  SEVERE: '#dc2626',
  MODERATE: '#f59e0b',
  MINOR: '#22c55e',
};

export default function SimpleHailMap() {
  const now = new Date();
  const [calYear, setCalYear] = useState(now.getFullYear());
  const [calMonth, setCalMonth] = useState(now.getMonth() + 1);
  const [calDays, setCalDays] = useState<Record<string, CalendarDay>>({});
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [events, setEvents] = useState<HailEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [minConfidence, setMinConfidence] = useState<number>(45);
  const [fitKey, setFitKey] = useState(0);

  const loadCalendar = useCallback(async (year: number, month: number) => {
    try {
      const res = await fetch(
        `/api/hail-events/calendar?year=${year}&month=${month}&min_conf=${minConfidence}`,
        { credentials: 'include' }
      );
      const data = await res.json();
      setCalDays(data.days || {});
    } catch (err) {
      console.error('Failed to load calendar:', err);
    }
  }, [minConfidence]);

  useEffect(() => {
    loadCalendar(calYear, calMonth);
  }, [calYear, calMonth, loadCalendar]);

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
      setFitKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to load events:', err);
    }
    setLoading(false);
  };

  const handleDayClick = (dateStr: string) => {
    setSelectedDate(dateStr);
    loadEvents(dateStr);
  };

  const prevMonth = () => {
    if (calMonth === 1) { setCalYear(y => y - 1); setCalMonth(12); }
    else { setCalMonth(m => m - 1); }
  };
  const nextMonth = () => {
    if (calMonth === 12) { setCalYear(y => y + 1); setCalMonth(1); }
    else { setCalMonth(m => m + 1); }
  };

  const filteredEvents = events.filter(e => {
    const conf = e.confidence_score ?? 100;
    return conf >= minConfidence;
  });

  // Build calendar grid
  const firstDow = new Date(calYear, calMonth - 1, 1).getDay();
  const daysInMonth = new Date(calYear, calMonth, 0).getDate();
  const calCells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) calCells.push(null);
  for (let d = 1; d <= daysInMonth; d++) calCells.push(d);

  return (
    <div className="h-screen flex flex-col">
      <div className="p-3 bg-gray-100 flex gap-4 items-start flex-wrap">
        {/* Mini calendar */}
        <div className="bg-white rounded shadow p-2 text-xs" style={{ minWidth: 220 }}>
          <div className="flex items-center justify-between mb-1">
            <button onClick={prevMonth} className="px-1 hover:bg-gray-200 rounded">&lt;</button>
            <span className="font-semibold">{MONTH_NAMES[calMonth - 1]} {calYear}</span>
            <button onClick={nextMonth} className="px-1 hover:bg-gray-200 rounded">&gt;</button>
          </div>
          <div className="grid grid-cols-7 gap-px text-center">
            {DAY_NAMES.map(d => <div key={d} className="font-medium text-gray-500">{d}</div>)}
            {calCells.map((day, i) => {
              if (day === null) return <div key={`e${i}`} />;
              const dateStr = `${calYear}-${String(calMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
              const dayData = calDays[dateStr];
              const isSelected = dateStr === selectedDate;
              const sev = dayData?.max_severity;
              const bgColor = sev ? SEVERITY_COLORS[sev] || '#e5e7eb' : undefined;
              return (
                <button
                  key={dateStr}
                  onClick={() => handleDayClick(dateStr)}
                  className={`rounded p-0.5 leading-tight ${isSelected ? 'ring-2 ring-blue-500' : ''}`}
                  style={{
                    backgroundColor: bgColor,
                    color: bgColor ? '#fff' : undefined,
                  }}
                  title={dayData ? `${dayData.count} storms, max ${dayData.max_hail_size}"` : undefined}
                >
                  {day}
                  {dayData && <div className="text-[9px] leading-none">{dayData.count}</div>}
                </button>
              );
            })}
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-col gap-2">
          <div className="flex gap-2 items-center">
            <label className="text-sm">Min Confidence:</label>
            <input
              type="range"
              min={0}
              max={100}
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-32"
            />
            <span className="text-sm font-mono">{minConfidence}</span>
          </div>
          <div className="text-sm text-gray-600">
            {loading ? 'Loading...' : selectedDate
              ? `${filteredEvents.length}/${events.length} storms on ${selectedDate}`
              : 'Click a calendar day to load storms'}
          </div>
          {/* Legend */}
          <div className="flex gap-2 text-xs">
            {Object.entries(SEVERITY_COLORS).map(([label, color]) => (
              <span key={label} className="flex items-center gap-1">
                <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: color }} />
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <MapContainer center={[39, -98]} zoom={4} className="flex-1">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapFitter key={fitKey} events={filteredEvents} />
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
