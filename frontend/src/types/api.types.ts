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

export interface ObservationFrame {
  datetime: string;
  sun: CelestialPosition;
  moon: CelestialPosition;
  moon_phase: MoonPhaseData;
  venus?: CelestialPosition;
  venus_phase?: VenusPhaseData;
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

// Configuration
export interface ApiConfig {
  baseUrl: string;
  timeout: number;
}
