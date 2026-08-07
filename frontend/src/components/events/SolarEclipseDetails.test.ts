import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import SolarEclipseDetails from './SolarEclipseDetails.vue';
import type { AstronomicalEvent } from '@/types/api.types';

const baseEvent: AstronomicalEvent = {
  event_type: 'New Moon',
  is_lunar: false,
  date: '2026-02-17 12:12:00.000',
  julian_date: 2461088.0,
  moon_ecl_lat_deg: -0.05,
  eclipse_occurs: true,
  eclipse_type: 'Annular',
  greatest_eclipse_time: '2026-02-17 12:12:00.000',
  umbral_magnitude: null,
  penumbral_magnitude: null,
  size_ratio: 0.9612,
  contact_times: {
    eclipse_begins: '2026-02-17 10:00:00.000',
    central_phase_begins: '2026-02-17 11:00:00.000',
    central_phase_ends: '2026-02-17 13:00:00.000',
    eclipse_ends: '2026-02-17 14:00:00.000',
  },
};

describe('SolarEclipseDetails', () => {
  it('renders size ratio and all contact times in order', () => {
    const wrapper = mount(SolarEclipseDetails, { props: { event: baseEvent } });

    expect(wrapper.text()).toContain('0.9612');

    const labels = wrapper.findAll('.detail-row dt').map((r) => r.text());
    const beginsIndex = labels.findIndex((l) => l === 'Eclipse Begins');
    const endsIndex = labels.findIndex((l) => l === 'Eclipse Ends');
    expect(beginsIndex).toBeGreaterThan(-1);
    expect(endsIndex).toBeGreaterThan(beginsIndex);
  });

  it('handles null size ratio and contact times gracefully', () => {
    const emptyEvent: AstronomicalEvent = {
      ...baseEvent,
      size_ratio: null,
      contact_times: null,
    };
    const wrapper = mount(SolarEclipseDetails, { props: { event: emptyEvent } });
    expect(wrapper.findAll('.detail-row')).toHaveLength(1); // just greatest eclipse time
  });

  it('omits the greatest eclipse row when null', () => {
    const noGreatestEvent: AstronomicalEvent = {
      ...baseEvent,
      greatest_eclipse_time: null,
      contact_times: null,
    };
    const wrapper = mount(SolarEclipseDetails, { props: { event: noGreatestEvent } });
    expect(wrapper.findAll('.detail-row')).toHaveLength(1); // just size ratio
  });

  it('falls back to the raw value when a contact time cannot be parsed', () => {
    const invalidEvent: AstronomicalEvent = {
      ...baseEvent,
      greatest_eclipse_time: 'not-a-real-date',
    };
    const wrapper = mount(SolarEclipseDetails, { props: { event: invalidEvent } });
    expect(wrapper.text()).toContain('not-a-real-date');
  });
});
