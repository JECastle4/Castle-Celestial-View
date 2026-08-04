import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import LunarEclipseDetails from './LunarEclipseDetails.vue';
import type { AstronomicalEvent } from '@/types/api.types';

const baseEvent: AstronomicalEvent = {
  event_type: 'full_moon',
  date: '2025-09-07 18:11:42.600',
  julian_date: 2460925.257,
  moon_ecl_lat_deg: -0.1,
  eclipse_occurs: true,
  eclipse_type: 'TOTAL',
  greatest_eclipse_time: '2025-09-07 18:11:42.600',
  umbral_magnitude: 1.3635,
  penumbral_magnitude: 2.4123,
  size_ratio: null,
  contact_times: {
    p1: '2025-09-07 15:29:50.911',
    u1: '2025-09-07 16:26:57.000',
    u2: '2025-09-07 17:30:41.000',
    u3: '2025-09-07 18:52:43.000',
    u4: '2025-09-07 19:56:27.000',
    p4: '2025-09-07 20:53:34.000',
  },
};

describe('LunarEclipseDetails', () => {
  it('renders magnitudes and all contact times in order', () => {
    const wrapper = mount(LunarEclipseDetails, { props: { event: baseEvent } });

    expect(wrapper.text()).toContain('1.3635');
    expect(wrapper.text()).toContain('2.4123');

    const rows = wrapper.findAll('.detail-row dt');
    const labels = rows.map((r) => r.text());
    // p1..p4 contact labels should appear after the magnitude rows, in chronological order
    const p1Index = labels.findIndex((l) => l.startsWith('P1'));
    const p4Index = labels.findIndex((l) => l.startsWith('P4'));
    expect(p1Index).toBeGreaterThan(-1);
    expect(p4Index).toBeGreaterThan(p1Index);
  });

  it('omits missing contact times', () => {
    const partialEvent: AstronomicalEvent = {
      ...baseEvent,
      contact_times: { u2: '2025-09-07 17:30:41.000', u3: '2025-09-07 18:52:43.000' },
    };
    const wrapper = mount(LunarEclipseDetails, { props: { event: partialEvent } });

    const labels = wrapper.findAll('.detail-row dt').map((r) => r.text());
    expect(labels.some((l) => l.startsWith('U2'))).toBe(true);
    expect(labels.some((l) => l.startsWith('P1'))).toBe(false);
  });

  it('handles null magnitudes and contact times gracefully', () => {
    const emptyEvent: AstronomicalEvent = {
      ...baseEvent,
      umbral_magnitude: null,
      penumbral_magnitude: null,
      contact_times: null,
    };
    const wrapper = mount(LunarEclipseDetails, { props: { event: emptyEvent } });
    expect(wrapper.findAll('.detail-row')).toHaveLength(1); // just greatest eclipse time
  });

  it('omits the greatest eclipse row when null', () => {
    const noGreatestEvent: AstronomicalEvent = {
      ...baseEvent,
      greatest_eclipse_time: null,
      contact_times: null,
    };
    const wrapper = mount(LunarEclipseDetails, { props: { event: noGreatestEvent } });
    expect(wrapper.findAll('.detail-row')).toHaveLength(2); // just the two magnitudes
  });

  it('falls back to the raw value when a contact time cannot be parsed', () => {
    const invalidEvent: AstronomicalEvent = {
      ...baseEvent,
      greatest_eclipse_time: 'not-a-real-date',
    };
    const wrapper = mount(LunarEclipseDetails, { props: { event: invalidEvent } });
    expect(wrapper.text()).toContain('not-a-real-date');
  });
});
