// Mirrors the backend ItineraryOut schema (app/schemas/trip.py).

export interface LatLng {
  lat: number;
  lng: number;
}

export interface Place {
  name: string;
  location: LatLng;
  category: string;
  rating?: number | null;
  fee?: number | null;
  description?: string | null;
  source: string;
}

export interface WeatherDay {
  date?: string | null;
  summary: string;
  temp_min_c?: number | null;
  temp_max_c?: number | null;
  precipitation_mm?: number | null;
}

export interface ItineraryDay {
  day: number;
  date?: string | null;
  weather?: WeatherDay | null;
  stops: Place[];
  travel_time_min: number;
}

export interface BudgetBreakdown {
  intercity_transport: number;
  lodging: number;
  local_transport: number;
  attractions: number;
  food: number;
  buffer: number;
  total: number;
  currency: string;
  within_cap: boolean;
  sources: Record<string, string>;
}

export interface BookingSuggestion {
  type: string;
  title: string;
  provider: string;
  url?: string | null;
  price?: number | null;
  currency?: string | null;
  note?: string | null;
}

export interface AgentRun {
  agent: string;
  status: string;
  latency_ms: number;
  detail?: string | null;
}

export interface TripRequest {
  origin: string;
  destination: string;
  days: number;
  travelers: number;
  budget_cap: number;
  currency: string;
  budget_level: string;
  transport_mode: string;
  interests: string[];
}

export interface Itinerary {
  trip_id: string;
  request: TripRequest;
  days: ItineraryDay[];
  budget: BudgetBreakdown;
  bookings: BookingSuggestion[];
  weather: WeatherDay[];
  total_cost: number;
  within_budget: boolean;
  summary: string;
  agent_runs: AgentRun[];
}
