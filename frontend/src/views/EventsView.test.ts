import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import EventsView from './EventsView.vue';

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
    event_type: 'full_moon',
    date: '2025-09-07 18:11:42.600',
    julian_date: 2460925.257,
    moon_ecl_lat_deg: -0.1,
    eclipse_occurs: true,
    eclipse_type: 'TOTAL',
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
  event_type: 'new_moon',
  date: '2025-09-21 19:54:00.000',
  julian_date: 2460939.33,
  moon_ecl_lat_deg: 0.2,
  eclipse_occurs: false,
  eclipse_type: 'NONE',
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
});
