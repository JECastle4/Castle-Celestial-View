import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import EventsView from './EventsView.vue';
import AppHeader from '@/components/Header.vue';

const pushMock = vi.fn();
vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router');
  return {
    ...actual,
    useRouter: () => ({ push: pushMock }),
  };
});

function makeEvent(overrides: Partial<Record<string, unknown>> = {}) {
  return {
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
    ...overrides,
  };
}

const fullMoonEvent = makeEvent();
const newMoonEvent = makeEvent({
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
});

class MockEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  url: string;
  close = vi.fn();
  onerror: ((event: unknown) => void) | null = null;
  private listeners: Record<string, ((event: { data: string }) => void)[]> = {};

  constructor(url: string) {
    this.url = url;
    instances.push(this);
  }

  addEventListener(type: string, cb: (event: { data: string }) => void) {
    (this.listeners[type] ??= []).push(cb);
  }

  emit(type: string, data: unknown) {
    this.listeners[type]?.forEach((cb) => cb({ data: JSON.stringify(data) }));
  }
}

let instances: MockEventSource[] = [];
let origEventSource: typeof EventSource;

beforeEach(() => {
  instances = [];
  origEventSource = globalThis.EventSource;
  globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
});

afterEach(() => {
  globalThis.EventSource = origEventSource;
});

describe('EventsView', () => {
  it('renders the title and description', () => {
    const wrapper = mount(EventsView);
    expect(wrapper.text()).toContain('Astronomical Events');
  });

  it('fetches and displays events when Search is clicked', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    source.emit('page', { page: 1, events: [fullMoonEvent, newMoonEvent] });
    source.emit('metadata', { page_size: 10, total_events: 2, total_pages: 1 });
    await flushPromises();

    expect(wrapper.findAll('.event-item')).toHaveLength(2);
  });

  it('shows a live event count while the search is in progress', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    source.emit('page', { page: 1, events: [fullMoonEvent] });
    await flushPromises();

    expect(wrapper.find('.loading').text()).toContain('1');
  });

  it('shows an error message when the SSE connection fails', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    source.onerror?.({});
    await flushPromises();

    expect(wrapper.find('.error').text()).toContain('SSE connection error');
  });

  it('shows a no-results message when the search returns no events', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    source.emit('metadata', { page_size: 10, total_events: 0, total_pages: 1 });
    await flushPromises();

    expect(wrapper.find('.empty-state').exists()).toBe(true);
  });

  it('cancels the search when the cancel button is clicked', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    await wrapper.find('.cancel-btn').trigger('click');
    await flushPromises();

    expect(source.close).toHaveBeenCalled();
    expect(wrapper.find('.error').text()).toContain('cancelled');
  });

  it('navigates back to the solar system view when the Solar System mode button is clicked', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    const modeButtons = wrapper.findAll('.mode-btn');
    await modeButtons[0].trigger('click'); // Solar System is the first mode button

    expect(pushMock).toHaveBeenCalledWith('/en-UK/');
  });

  it('paginates client-side across the already-loaded results without a new request', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    // 11 events so the (client-side, page_size=10) pagination has 2 pages
    const firstPage = Array.from({ length: 10 }, (_, i) => makeEvent({ date: `2025-01-0${i + 1}` }));
    const eleventh = makeEvent({ date: '2025-02-01' });

    const source = instances[0];
    source.emit('page', { page: 1, events: firstPage });
    source.emit('page', { page: 2, events: [eleventh] });
    source.emit('metadata', { page_size: 10, total_events: 11, total_pages: 2 });
    await flushPromises();

    expect(wrapper.findAll('.event-item')).toHaveLength(10);

    const [, nextButton] = wrapper.findAll('.pagination button');
    await nextButton.trigger('click');
    await flushPromises();

    expect(instances).toHaveLength(1); // no new EventSource created for pagination
    expect(wrapper.findAll('.event-item')).toHaveLength(1);
  });

  it('re-fetches with the new date range when DateRangePicker emits update:dates', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    const dateRangePicker = wrapper.findComponent({ name: 'DateRangePicker' });
    await dateRangePicker.vm.$emit('update:dates', {
      start: new Date('2027-01-01T00:00:00Z'),
      end: new Date('2027-06-01T00:00:00Z'),
    });

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    expect(source.url).toContain('start_date=2027-01-01');
    expect(source.url).toContain('end_date=2027-06-01');
  });

  it('displays formatted dates in the parameters panel', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    const parametersPanel = wrapper.find('.parameters-panel');
    expect(parametersPanel.text()).toContain('Search Parameters');
    const parameterItems = wrapper.findAll('.parameter-item');
    expect(parameterItems.length).toBeGreaterThan(0);
  });

  it('correctly identifies and renders lunar eclipse events', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const lunarEvent = makeEvent({ event_type: 'Lunar Total', is_lunar: true, eclipse_occurs: true });
    source.emit('page', { page: 1, events: [lunarEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const eventItems = wrapper.findAll('.event-item');
    expect(eventItems.length).toBe(1);
    // Verify the event-type is displayed
    expect(eventItems[0].text()).toContain('Lunar Total');
  });

  it('correctly identifies and renders solar eclipse events', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const solarEvent = makeEvent({ event_type: 'Solar Total', is_lunar: false, eclipse_occurs: true });
    source.emit('page', { page: 1, events: [solarEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const eventItems = wrapper.findAll('.event-item');
    expect(eventItems.length).toBe(1);
    // Verify the event-type is displayed
    expect(eventItems[0].text()).toContain('Solar Total');
  });

  it('correctly identifies and renders full moon events', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const fullMoon = makeEvent({ event_type: 'Full Moon', is_lunar: true, eclipse_occurs: false, eclipse_type: 'No Eclipse' });
    source.emit('page', { page: 1, events: [fullMoon] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const eventItems = wrapper.findAll('.event-item');
    expect(eventItems.length).toBe(1);
    // Verify the event-type is displayed
    expect(eventItems[0].text()).toContain('Full Moon');
  });

  it('correctly identifies and renders new moon events', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const newMoon = makeEvent({ event_type: 'New Moon', is_lunar: false, eclipse_occurs: false });
    source.emit('page', { page: 1, events: [newMoon] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const eventItems = wrapper.findAll('.event-item');
    expect(eventItems.length).toBe(1);
    // Verify the event-type is displayed
    expect(eventItems[0].text()).toContain('New Moon');
  });

  it('expands eclipse event details when clicked', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const lunarEvent = makeEvent({ event_type: 'Lunar Total', is_lunar: true, eclipse_occurs: true });
    source.emit('page', { page: 1, events: [lunarEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const eventButton = wrapper.find('.event-summary');
    expect(eventButton.exists()).toBe(true);
    
    await eventButton.trigger('click');
    await flushPromises();

    const eventDetails = wrapper.find('.event-details');
    expect(eventDetails.exists()).toBe(true);
  });

  it('shows pagination controls when multiple pages exist', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    source.emit('page', { page: 1, events: [fullMoonEvent] });
    source.emit('metadata', { page_size: 10, total_events: 20, total_pages: 2 });
    await flushPromises();

    expect(wrapper.find('.pagination').exists()).toBe(true);
    expect(wrapper.findAll('.pagination button')).toHaveLength(2);
  });

  it('displays results count in parameters panel after search', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    source.emit('page', { page: 1, events: [fullMoonEvent, newMoonEvent] });
    source.emit('metadata', { page_size: 10, total_events: 2, total_pages: 1 });
    await flushPromises();

    const parametersPanel = wrapper.find('.parameters-panel');
    expect(parametersPanel.text()).toContain('Results Found');
    expect(parametersPanel.text()).toContain('2');
  });

  it('handles multiple search queries in sequence', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    // First search
    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    let source = instances[0];
    source.emit('page', { page: 1, events: [fullMoonEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    expect(wrapper.findAll('.event-item')).toHaveLength(1);

    // Update date range
    const dateRangePicker = wrapper.findComponent({ name: 'DateRangePicker' });
    await dateRangePicker.vm.$emit('update:dates', {
      start: new Date('2026-01-01T00:00:00Z'),
      end: new Date('2026-12-31T00:00:00Z'),
    });
    await flushPromises();

    // Second search
    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    source = instances[1];
    source.emit('page', { page: 1, events: [newMoonEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    expect(wrapper.findAll('.event-item')).toHaveLength(1);
    expect(instances).toHaveLength(2);
  });

  it('handles invalid date strings gracefully', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    // Create an event with invalid date format to test the catch block
    const invalidDateEvent = makeEvent({ date: 'invalid-date-string' });
    source.emit('page', { page: 1, events: [invalidDateEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const eventItems = wrapper.findAll('.event-item');
    expect(eventItems.length).toBe(1);
    // Event should still render even with invalid date
    expect(wrapper.findAll('.event-item').length).toBeGreaterThan(0);
  });

  it('does not navigate when eclipse mode is selected', async () => {
    pushMock.mockClear();
    const wrapper = mount(EventsView);
    await flushPromises();

    // Simulate AppHeader emitting select-mode event with 'eclipses'
    const header = wrapper.findComponent(AppHeader);
    await header.vm.$emit('select-mode', 'eclipses');
    await flushPromises();

    // Should not navigate away from eclipses view
    expect(pushMock).not.toHaveBeenCalled();
  });
});
