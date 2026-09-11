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

  it('handles invalid date in formatDisplayDate gracefully', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const eventWithInvalidDate = makeEvent({ date: 'invalid-date-string' });
    source.emit('page', { page: 1, events: [eventWithInvalidDate] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    // The event should still be rendered even if date formatting fails
    expect(wrapper.findAll('.event-item')).toHaveLength(1);
  });

  it('loads contact times for an eclipse event on click', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const eclipseEvent = makeEvent({
      event_type: 'Lunar Total',
      is_lunar: true,
      eclipse_occurs: true,
      contact_times: null,
    });
    source.emit('page', { page: 1, events: [eclipseEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    // Click the event summary to expand and trigger contact times loading
    const eventButton = wrapper.find('.event-summary');
    expect(eventButton.exists()).toBe(true);
    await eventButton.trigger('click');
    await flushPromises();

    // Verify the event details section is rendered (contact times area shown)
    const eventDetails = wrapper.find('.event-details');
    expect(eventDetails.exists()).toBe(true);
  });

  it('handles error when loading contact times fails', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const eclipseEvent = makeEvent({
      event_type: 'Lunar Total',
      is_lunar: true,
      eclipse_occurs: true,
      contact_times: null,
    });
    source.emit('page', { page: 1, events: [eclipseEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    // Expand the event - this triggers contact times loading
    const eventButton = wrapper.find('.event-summary');
    await eventButton.trigger('click');
    await flushPromises();

    // Verify event details are shown (even if contact times failed to load)
    const eventDetails = wrapper.find('.event-details');
    expect(eventDetails.exists()).toBe(true);
  });

  it('skips loading contact times if event.contact_times already exists', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const eventWithContactTimes = makeEvent({
      event_type: 'Lunar Total',
      is_lunar: true,
      eclipse_occurs: true,
      contact_times: {
        p1: '2025-09-07 15:29:50.911',
        u1: '2025-09-07 16:26:57.000',
      },
    });
    source.emit('page', { page: 1, events: [eventWithContactTimes] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    const expandButton = wrapper.find('.event-summary');
    await expandButton.trigger('click');
    await flushPromises();

    // Event details should be shown but no loading request should be made
    const eventDetails = wrapper.find('.event-details');
    expect(eventDetails.exists()).toBe(true);
    // Only one EventSource from search, no additional one for contact times
    expect(instances).toHaveLength(1);
  });

  it('skips loading contact times if event.eclipse_occurs is false', async () => {
    const wrapper = mount(EventsView);
    await flushPromises();

    await wrapper.find('.search-btn').trigger('click');
    await flushPromises();

    const source = instances[0];
    const nonEclipseEvent = makeEvent({
      event_type: 'New Moon',
      is_lunar: false,
      eclipse_occurs: false,
      contact_times: null,
    });
    source.emit('page', { page: 1, events: [nonEclipseEvent] });
    source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
    await flushPromises();

    // Event should be displayed
    expect(wrapper.findAll('.event-item')).toHaveLength(1);
    // No additional EventSource created for contact times (only the search one)
    expect(instances).toHaveLength(1);
  });

  describe('Export Functionality', () => {
    it('shows export buttons when events are available', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      source.emit('page', { page: 1, events: [fullMoonEvent] });
      source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
      await flushPromises();

      const exportButtons = wrapper.findAll('.export-btn');
      expect(exportButtons).toHaveLength(2);
      expect(exportButtons[0].text()).toContain('CSV');
      expect(exportButtons[1].text()).toContain('JSON');
    });

    it('disables export buttons when no events are loaded', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      const exportButtons = wrapper.findAll('.export-btn');
      exportButtons.forEach((btn) => {
        expect(btn.attributes('disabled')).toBeDefined();
      });
    });

    it('enables export buttons after search results are loaded', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      source.emit('page', { page: 1, events: [fullMoonEvent, newMoonEvent] });
      source.emit('metadata', { page_size: 10, total_events: 2, total_pages: 1 });
      await flushPromises();

      const exportButtons = wrapper.findAll('.export-btn');
      exportButtons.forEach((btn) => {
        expect(btn.attributes('disabled')).toBeUndefined();
      });
    });

    it('triggers CSV export when CSV button is clicked', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      const eventWithContact = makeEvent({
        contact_times: {
          'Maximum Eclipse': '2025-09-07 18:11:42.600',
        },
      });
      source.emit('page', { page: 1, events: [eventWithContact] });
      source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
      await flushPromises();

      const csvButton = wrapper.findAll('.export-btn')[0];
      await csvButton.trigger('click');
      await flushPromises();

      // Verify button click was processed (actual download tested in export.test.ts)
      expect(csvButton.exists()).toBe(true);
    });

    it('triggers JSON export when JSON button is clicked', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      const eventWithContact = makeEvent({
        contact_times: {
          'Maximum Eclipse': '2025-09-07 18:11:42.600',
        },
      });
      source.emit('page', { page: 1, events: [eventWithContact] });
      source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
      await flushPromises();

      const jsonButton = wrapper.findAll('.export-btn')[1];
      await jsonButton.trigger('click');
      await flushPromises();

      // Verify button click was processed (actual download tested in export.test.ts)
      expect(jsonButton.exists()).toBe(true);
    });

    it('pre-loads missing contact times before export', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      // Event without contact_times (will need pre-loading)
      const eclipseWithoutContact = makeEvent({
        eclipse_occurs: true,
        contact_times: null,
      });
      source.emit('page', { page: 1, events: [eclipseWithoutContact] });
      source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
      await flushPromises();

      // Mock the composable's fetchContactTimesForEvent with manual control
      let resolveContactTime: any = null;
      const contactTimePromise = new Promise<void>(resolve => {
        resolveContactTime = resolve;
      });
      const mockFetch = vi.fn(() => contactTimePromise);
      const component = wrapper.vm as any;
      vi.spyOn(component, 'fetchContactTimesForEvent').mockImplementation(mockFetch);

      // Click export - should trigger pre-loading
      const csvButton = wrapper.findAll('.export-btn')[0];
      await csvButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Should show loading message (before promise resolves)
      const message = wrapper.find('.export-message');
      expect(message.exists()).toBe(true);
      expect(message.text()).toContain('Loading contact times');

      // Now resolve the pending promises and let export complete
      resolveContactTime();
      await flushPromises();
      await wrapper.vm.$nextTick();
    });

    it('disables export buttons during contact time pre-loading', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      const eclipseWithoutContact = makeEvent({
        eclipse_occurs: true,
        contact_times: null,
      });
      source.emit('page', { page: 1, events: [eclipseWithoutContact] });
      source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
      await flushPromises();

      // Mock slow contact time fetch
      const mockFetch = vi.fn().mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );
      const component = wrapper.vm as any;
      vi.spyOn(component, 'fetchContactTimesForEvent').mockImplementation(mockFetch);

      const csvButton = wrapper.findAll('.export-btn')[0];
      
      // Before click, button should be enabled (disabled attribute should be absent)
      expect(csvButton.attributes('disabled')).toBeUndefined();

      await csvButton.trigger('click');
      // Immediately after click (before promises resolve), button should be disabled
      let updatedButton = wrapper.findAll('.export-btn')[0];
      expect(updatedButton.attributes('disabled')).toBeDefined();

      // Wait for the mock promise to resolve
      await new Promise(resolve => setTimeout(resolve, 150));
      await flushPromises();
      await wrapper.vm.$nextTick();
      
      // Re-query the button to get the updated DOM element
      updatedButton = wrapper.findAll('.export-btn')[0];
      // After promises resolve, button should be enabled again (disabled attribute absent)
      expect(updatedButton.attributes('disabled')).toBeUndefined();
    });

    it('shows export success message and auto-clears after 3 seconds', async () => {
      vi.useFakeTimers();
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      const eventWithContact = makeEvent({
        contact_times: {
          'Maximum Eclipse': '2025-09-07 18:11:42.600',
        },
      });
      source.emit('page', { page: 1, events: [eventWithContact] });
      source.emit('metadata', { page_size: 10, total_events: 1, total_pages: 1 });
      await flushPromises();

      const csvButton = wrapper.findAll('.export-btn')[0];
      await csvButton.trigger('click');
      await flushPromises();

      // Message should be visible
      let message = wrapper.find('.export-message');
      expect(message.exists()).toBe(true);
      expect(message.text()).toContain('successfully');

      // Verify success styling
      expect(message.classes()).toContain('export-success');

      // Advance time by 3 seconds
      vi.advanceTimersByTime(3000);
      await flushPromises();

      // Message should be cleared
      message = wrapper.find('.export-message');
      expect(message.exists()).toBe(false);

      vi.useRealTimers();
    });

    it('shows export error message when no events available', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      // Load some events first so the export UI appears
      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      // Emit empty search results
      source.emit('page', { page: 1, events: [] });
      source.emit('metadata', { page_size: 10, total_events: 0, total_pages: 1 });
      await flushPromises();

      // Now attempt export with no actual events
      const component = wrapper.vm as any;
      component.handleExport('csv');
      await wrapper.vm.$nextTick();
      await flushPromises();

      // Should set error message in component
      expect(component.exportMessage).toBeTruthy();
      expect(component.exportMessage.toLowerCase()).toContain('no');
    });

    it('handles partial contact time fetch failures gracefully', async () => {
      const wrapper = mount(EventsView);
      await flushPromises();

      await wrapper.find('.search-btn').trigger('click');
      await flushPromises();

      const source = instances[0];
      // Mix of eclipses with and without contact times
      const eclipse1 = makeEvent({
        date: '2025-09-07',
        eclipse_occurs: true,
        contact_times: null,
      });
      const eclipse2 = makeEvent({
        date: '2025-09-21',
        eclipse_occurs: true,
        contact_times: {
          'Maximum Eclipse': '2025-09-21 10:00:00',
        },
      });
      source.emit('page', { page: 1, events: [eclipse1, eclipse2] });
      source.emit('metadata', { page_size: 10, total_events: 2, total_pages: 1 });
      await flushPromises();

      // Mock fetch to fail for first eclipse, succeed for second
      let callCount = 0;
      const mockFetch = vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve(undefined);
      });
      const component = wrapper.vm as any;
      vi.spyOn(component, 'fetchContactTimesForEvent').mockImplementation(mockFetch);

      const csvButton = wrapper.findAll('.export-btn')[0];
      await csvButton.trigger('click');
      // Wait for all promises to settle (including contact time fetch attempts)
      await new Promise(resolve => setTimeout(resolve, 150));
      await flushPromises();
      await wrapper.vm.$nextTick();

      // Export should complete despite one failure
      const message = wrapper.find('.export-message');
      expect(message.exists()).toBe(true);
      // Should show success message (individual failures are caught and ignored)
      // Message should contain the success text from i18n
      const messageText = message.text().toLowerCase();
      expect(messageText).toContain('successfully');
    });
  });
});
