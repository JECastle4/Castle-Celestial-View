/**
 * API Response Types
 * These match the Pydantic models from the FastAPI backend
 */

export interface CelestialPosition {
  altitude: number;
  azimuth: number;
  is_visible: boolean;
}

export interface MoonPhaseData {
  illumination: number;
  phase_angle: number;
  phase_name: string;
}

export interface ObservationFrame {
  datetime: string;
  sun: CelestialPosition;
  moon: CelestialPosition;
  moon_phase: MoonPhaseData;
  venus?: CelestialPosition;
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
