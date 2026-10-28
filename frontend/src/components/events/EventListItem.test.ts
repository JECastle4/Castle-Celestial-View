import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import EventListItem from './EventListItem.vue';

const mockEvent = {
  event_type: 'Full Moon',
  is_lunar: true,
  date: '2025-09-07 18:11:42.600',
  julian_date: 2460925.257,
  moon_ecl_lat_deg: -0.1,
  eclipse_occurs: true,
  eclipse_type: 'Total',
  greatest_eclipse_time: '2025-09-07 18:11:42.600',
  umbral_magnitude: 1.36,
  penumbral_magnitude: 2.4,
  size_ratio: null,
  contact_times: null,
};

const mockNonEclipseEvent = {
  event_type: 'New Moon',
  is_lunar: false,
  date: '2025-09-21 19:54:00.000',
  julian_date: 2460939.33,
  moon_ecl_lat_deg: 0.2,
  eclipse_occurs: false,
  eclipse_type: 'No Eclipse',
  greatest_eclipse_time: null,
  umbral_magnitude: null,
  penumbral_magnitude: null,
  size_ratio: null,
  contact_times: null,
};

describe('EventListItem', () => {
  it('renders a static (non-expandable) row when no eclipse occurs', () => {
    const wrapper = mount(EventListItem, {
      props: {
        date: '2025-09-21 19:54:00.000',
        eventType: 'New Moon',
        eclipseOccurs: false,
        event: mockNonEclipseEvent,
      },
    });

    const btn = wrapper.find('button.event-summary');
    expect(btn.exists()).toBe(true);
    expect(btn.classes()).toContain('event-summary-static');
    expect(btn.attributes('aria-label')).toBe('21 Sept 2025, 19:54 - New Moon. No Eclipse');
    expect(wrapper.text()).toContain('New Moon');
    // Check that a circle icon is rendered for non-eclipse items
    expect(wrapper.find('i.fa-circle').exists()).toBe(true);
  });

  it('renders an expandable button when an eclipse occurs', () => {
    const wrapper = mount(EventListItem, {
      props: {
        date: '2025-09-07 18:11:42.600',
        eventType: 'Full Moon',
        eclipseOccurs: true,
        event: mockEvent,
      },
    });

    const btn = wrapper.find('button.event-summary');
    expect(btn.exists()).toBe(true);
    expect(btn.attributes('aria-expanded')).toBe('false');
  });

  it('expands to reveal slot content when clicked', async () => {
    const wrapper = mount(EventListItem, {
      props: {
        date: '2025-09-07 18:11:42.600',
        eventType: 'Full Moon',
        eclipseOccurs: true,
        event: mockEvent,
      },
      slots: {
        default: '<div class="slot-content">Details</div>',
      },
    });

    expect(wrapper.find('.slot-content').exists()).toBe(false);

    await wrapper.find('button.event-summary').trigger('click');

    expect(wrapper.find('.slot-content').exists()).toBe(true);
    expect(wrapper.find('button.event-summary').attributes('aria-expanded')).toBe('true');
  });
});
