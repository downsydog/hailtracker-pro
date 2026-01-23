/**
 * Mock API handlers for testing
 */

export const mockSalespeople = [
  {
    id: 1,
    first_name: 'Mike',
    last_name: 'Johnson',
    email: 'mike@example.com',
    phone: '555-0101',
    employee_id: 'EMP001',
    status: 'ACTIVE',
    hire_date: '2024-01-15',
    commission_rate: 0.1,
    created_at: '2024-01-15T00:00:00Z',
  },
  {
    id: 2,
    first_name: 'Sarah',
    last_name: 'Williams',
    email: 'sarah@example.com',
    phone: '555-0102',
    employee_id: 'EMP002',
    status: 'ACTIVE',
    hire_date: '2024-02-01',
    commission_rate: 0.12,
    created_at: '2024-02-01T00:00:00Z',
  },
]

export const mockFieldLeads = [
  {
    id: 1,
    salesperson_id: 1,
    latitude: 32.7767,
    longitude: -96.797,
    address: '123 Main St, Dallas, TX',
    customer_name: 'John Doe',
    phone: '555-1234',
    email: 'john@example.com',
    lead_quality: 'HOT',
    notes: 'Interested in hail repair',
    synced_to_crm: false,
    created_at: '2024-01-20T10:00:00Z',
  },
  {
    id: 2,
    salesperson_id: 1,
    latitude: 32.78,
    longitude: -96.8,
    address: '456 Oak Ave, Dallas, TX',
    customer_name: 'Jane Smith',
    phone: '555-5678',
    email: 'jane@example.com',
    lead_quality: 'WARM',
    notes: 'Follow up next week',
    synced_to_crm: true,
    crm_lead_id: 101,
    created_at: '2024-01-21T14:30:00Z',
  },
  {
    id: 3,
    salesperson_id: 1,
    latitude: 32.785,
    longitude: -96.79,
    address: '789 Pine Rd, Dallas, TX',
    customer_name: 'Bob Wilson',
    phone: '555-9999',
    lead_quality: 'COLD',
    synced_to_crm: false,
    created_at: '2024-01-22T09:00:00Z',
  },
]

export const mockCompetitorActivity = [
  {
    id: 1,
    salesperson_id: 1,
    competitor_name: 'ABC Roofing',
    activity_type: 'CANVASSING',
    location_lat: 32.77,
    location_lon: -96.79,
    address: '100 Elm St, Dallas, TX',
    notes: 'Team of 3 canvassing',
    spotted_at: '2024-01-20T11:00:00Z',
  },
  {
    id: 2,
    salesperson_id: 1,
    competitor_name: 'XYZ Restoration',
    activity_type: 'TRUCK_PARKED',
    location_lat: 32.78,
    location_lon: -96.8,
    address: '200 Cedar Ln, Dallas, TX',
    notes: 'Truck with signage',
    spotted_at: '2024-01-21T15:00:00Z',
  },
]

export const mockDNKList = [
  {
    id: 1,
    address: '999 No Soliciting St, Dallas, TX',
    latitude: 32.775,
    longitude: -96.795,
    reason: 'NO_SOLICITING',
    notes: 'Large sign on door',
    reported_by: 1,
    added_at: '2024-01-19T10:00:00Z',
  },
  {
    id: 2,
    address: '888 Private Dr, Dallas, TX',
    latitude: 32.782,
    longitude: -96.805,
    reason: 'REQUESTED',
    notes: 'Homeowner asked not to return',
    reported_by: 1,
    added_at: '2024-01-20T14:00:00Z',
  },
]

export const mockAchievements = [
  {
    id: 1,
    salesperson_id: 1,
    achievement_type: 'FIRST_LEAD',
    points: 10,
    earned_at: '2024-01-15T12:00:00Z',
  },
  {
    id: 2,
    salesperson_id: 1,
    achievement_type: 'HOT_STREAK',
    points: 50,
    earned_at: '2024-01-18T16:00:00Z',
  },
]

export const mockLeaderboard = [
  {
    id: 1,
    first_name: 'Mike',
    last_name: 'Johnson',
    leads_today: 5,
    hot_leads_today: 2,
    points: 150,
  },
  {
    id: 2,
    first_name: 'Sarah',
    last_name: 'Williams',
    leads_today: 4,
    hot_leads_today: 1,
    points: 120,
  },
]

export const mockScript = {
  script: {
    category: 'DOOR_APPROACH',
    opening: 'Hi there! My name is [Name] with HailTracker Pro.',
    response: null,
    key_points: ['Make eye contact', 'Stand back from door', 'Have clipboard ready'],
    tips: ['Best times are 4-7pm weekdays', 'Avoid meal times'],
  },
}
