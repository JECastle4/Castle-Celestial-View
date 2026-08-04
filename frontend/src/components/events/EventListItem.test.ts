import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import EventListItem from './EventListItem.vue';

describe('EventListItem', () => {
  it('renders a static (non-expandable) row when no eclipse occurs', () => {
    const wrapper = mount(EventListItem, {
      props: {
        date: '2025-09-21 19:54:00.000',
        eventType: 'new_moon',
        eclipseType: 'NONE',
        eclipseOccurs: false,
      },
    });

    expect(wrapper.find('button.event-summary').exists()).toBe(false);
    expect(wrapper.find('.event-summary-static').exists()).toBe(true);
    expect(wrapper.text()).toContain('New Moon');
  });

  it('renders an expandable button when an eclipse occurs', () => {
    const wrapper = mount(EventListItem, {
      props: {
        date: '2025-09-07 18:11:42.600',
        eventType: 'full_moon',
        eclipseType: 'TOTAL',
        eclipseOccurs: true,
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
        eventType: 'full_moon',
        eclipseType: 'TOTAL',
        eclipseOccurs: true,
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
