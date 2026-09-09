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
    it('renders the Solar System button as active by default', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      const activeBtn = wrapper.find('.mode-btn.active');
      expect(activeBtn.exists()).toBe(true);
      expect(activeBtn.text()).toContain('Solar System');
    });

    it('renders the Eclipses button as active when currentMode is eclipses', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun', currentMode: 'eclipses' } });
      const activeBtn = wrapper.find('.mode-btn.active');
      expect(activeBtn.exists()).toBe(true);
      expect(activeBtn.text()).toContain('Eclipses');
    });

    it('renders only the Transits button as disabled', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      const disabledBtns = wrapper.findAll('.mode-btn[disabled]');
      expect(disabledBtns).toHaveLength(1);
      expect(disabledBtns[0].text()).toContain('Transits');
    });

    it('renders exactly three mode buttons', () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      expect(wrapper.findAll('.mode-btn')).toHaveLength(3);
    });

    it('emits select-mode with "eclipses" when the Eclipses button is clicked', async () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun' } });
      const buttons = wrapper.findAll('.mode-btn');
      await buttons[1].trigger('click');
      expect(wrapper.emitted('select-mode')).toBeTruthy();
      expect(wrapper.emitted('select-mode')![0]).toEqual(['eclipses']);
    });

    it('emits select-mode with "solarSystem" when the Solar System button is clicked', async () => {
      const wrapper = mount(Header, { props: { hasData: false, selectedBody: 'sun', currentMode: 'eclipses' } });
      const buttons = wrapper.findAll('.mode-btn');
      await buttons[0].trigger('click');
      expect(wrapper.emitted('select-mode')).toBeTruthy();
      expect(wrapper.emitted('select-mode')![0]).toEqual(['solarSystem']);
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
