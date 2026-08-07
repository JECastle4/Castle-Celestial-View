/**
 * API Response Types
 * Generally match the Pydantic models from the FastAPI backend.
 * Note: Venus fields are modeled as optional for forward compatibility during FE implementation.
 * The backend returns Venus data for all frames; optional typing allows gradual FE adoption.
 */

export interface CelestialPosition {
  altitude: number;
  azimuth: number;
  is_visible: boolean;
  ra_degrees: number;
  dec_degrees: number;
}

export interface MoonPhaseData {
  illumination: number;
  phase_angle: number;
  phase_name: string;
}

export interface VenusPhaseData {
  illumination: number;
  phase_angle: number;
  phase_name: string;
  naked_eye_visible: boolean;
}

export interface MercuryPhaseData {
  illumination: number;
  phase_angle: number;
  phase_name: string;
  naked_eye_visible: boolean;
}

export interface MarsPhaseData {
  illumination: number;
  phase_angle: number;
  phase_name: string;
  retrograde_status: string;
}

export interface OuterPlanetData {
  retrograde_status: string;
}

export interface ObservationFrame {
  datetime: string;
  sun: CelestialPosition;
  moon: CelestialPosition;
  moon_phase: MoonPhaseData;
  venus?: CelestialPosition;
  venus_phase?: VenusPhaseData;
  mercury?: CelestialPosition;
  mercury_phase?: MercuryPhaseData;
  mars?: CelestialPosition;
  mars_phase?: MarsPhaseData;
  jupiter?: CelestialPosition;
  jupiter_data?: OuterPlanetData;
  saturn?: CelestialPosition;
  saturn_data?: OuterPlanetData;
  uranus?: CelestialPosition;
  uranus_data?: OuterPlanetData;
  neptune?: CelestialPosition;
  neptune_data?: OuterPlanetData;
}

export interface LocationModel {
  latitude: number;
  longitude: number;
  elevation: number;
}

export interface BatchMetadata {
  location: LocationModel;
  frame_count: number;
  start_datetime: string;
  end_datetime: string;
  time_span_hours: number;
}

export interface BatchEarthObservationsResponse {
  frames: ObservationFrame[];
  metadata: BatchMetadata;
}

// Astronomical Events (Issue 141 - new/full moons + eclipse detection)
// event_type and eclipse_type are translated strings returned by the API
export type AstronomicalEventType = string;
export type EclipseType = string;

// Lunar keys: p1/u1/u2/u3/u4/p4. Solar keys: eclipse_begins/central_phase_begins/
// central_phase_ends/eclipse_ends. Values are ISO time strings, or null when that
// particular contact doesn't occur.
export type EclipseContactTimes = Record<string, string | null>;

export interface AstronomicalEvent {
  event_type: AstronomicalEventType;
  // Locale-independent discriminator for lunar vs. solar; event_type/eclipse_type
  // are translated display strings and must not be used for branching logic.
  is_lunar: boolean;
  date: string;
  julian_date: number;
  moon_ecl_lat_deg: number;
  eclipse_occurs: boolean;
  eclipse_type: EclipseType;
  greatest_eclipse_time: string | null;
  umbral_magnitude: number | null;
  penumbral_magnitude: number | null;
  size_ratio: number | null;
  contact_times: EclipseContactTimes | null;
}

export interface PaginationInfo {
  page: number;
  page_size: number;
  total_events: number;
  total_pages: number;
}

export interface AstronomicalEventsResponse {
  events: AstronomicalEvent[];
  pagination: PaginationInfo;
}

// Configuration
export interface ApiConfig {
  baseUrl: string;
  timeout: number;
}
