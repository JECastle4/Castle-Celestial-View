import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import Header from './Header.vue';

describe('Header', () => {
  describe('app title', () => {
    it('renders the app title', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      expect(wrapper.text()).toContain('Castle Celestial View');
    });

    it('always shows the title regardless of hasData', () => {
      const withData = mount(Header, { props: { hasData: true, selectedBody: 'sun' } });
      const withoutData = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      expect(withData.find('.app-title').text()).toBe('Castle Celestial View');
      expect(withoutData.find('.app-title').text()).toBe('Castle Celestial View');
    });
  });

  describe('mode switcher', () => {
    it('renders the Solar System button as active', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      const activeBtn = wrapper.find('.mode-btn.active');
      expect(activeBtn.exists()).toBe(true);
      expect(activeBtn.text()).toContain('Solar System');
    });

    it('renders Eclipses and Transits buttons as disabled', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      const disabledBtns = wrapper.findAll('.mode-btn[disabled]');
      expect(disabledBtns).toHaveLength(2);
    });

    it('renders exactly three mode buttons', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      expect(wrapper.findAll('.mode-btn')).toHaveLength(3);
    });
  });

  describe('planet carousel visibility', () => {
    it('does not render the carousel when hasData is false', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      expect(wrapper.find('.planet-carousel').exists()).toBe(false);
    });

    it('renders the carousel when hasData is true', () => {
      const wrapper = mount(Header, { props: { hasData: true, selectedBody: 'sun' } });
      expect(wrapper.find('.planet-carousel').exists()).toBe(true);
    });
  });

  describe('emit propagation', () => {
    it('propagates update:selectedBody emitted by the carousel', async () => {
      const wrapper = mount(Header, { props: { hasData: true, selectedBody: 'sun' } });
      await wrapper.findAll('.body-tab')[1].trigger('click'); // click Mercury
      expect(wrapper.emitted('update:selectedBody')).toBeTruthy();
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual(['mercury']);
    });
  });
});
