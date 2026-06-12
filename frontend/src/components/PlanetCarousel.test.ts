import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import PlanetCarousel from './PlanetCarousel.vue';
import { CELESTIAL_BODIES } from '@/config/celestialBodies';

describe('PlanetCarousel', () => {
  describe('rendering', () => {
    it('renders a tab for every celestial body', () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      const tabs = wrapper.findAll('.body-tab');
      expect(tabs).toHaveLength(CELESTIAL_BODIES.length);
    });

    it('renders body names in tabs', () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      expect(wrapper.text()).toContain('Sun');
      expect(wrapper.text()).toContain('Moon');
      expect(wrapper.text()).toContain('Venus');
      expect(wrapper.text()).toContain('Mercury');
    });

    it('renders two navigation buttons', () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      expect(wrapper.findAll('.nav-btn')).toHaveLength(2);
    });

    it('marks the selected body tab as active', () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'moon' } });
      const activeTab = wrapper.find('.body-tab.active');
      expect(activeTab.exists()).toBe(true);
      expect(activeTab.text()).toContain('Moon');
    });

    it('marks only one tab as active at a time', () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'venus' } });
      expect(wrapper.findAll('.body-tab.active')).toHaveLength(1);
    });
  });

  describe('body tab selection', () => {
    it('emits update:selectedBody when clicking a tab', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      await wrapper.findAll('.body-tab')[1].trigger('click'); // moon tab
      expect(wrapper.emitted('update:selectedBody')).toBeTruthy();
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual(['moon']);
    });

    it('emits the correct body id for each tab', async () => {
      for (let i = 0; i < CELESTIAL_BODIES.length; i++) {
        const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
        await wrapper.findAll('.body-tab')[i].trigger('click');
        expect(wrapper.emitted('update:selectedBody')![0]).toEqual([CELESTIAL_BODIES[i].id]);
      }
    });
  });

  describe('next button', () => {
    it('advances to the next body', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      const [, nextBtn] = wrapper.findAll('.nav-btn');
      await nextBtn.trigger('click');
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([CELESTIAL_BODIES[1].id]);
    });

    it('wraps from the last body back to the first', async () => {
      const lastBody = CELESTIAL_BODIES[CELESTIAL_BODIES.length - 1];
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: lastBody.id } });
      const [, nextBtn] = wrapper.findAll('.nav-btn');
      await nextBtn.trigger('click');
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([CELESTIAL_BODIES[0].id]);
    });

    it('falls back to first body when currentId is not found', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'invalid-body' } });
      const [, nextBtn] = wrapper.findAll('.nav-btn');
      await nextBtn.trigger('click');
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([CELESTIAL_BODIES[1].id]);
    });
  });

  describe('prev button', () => {
    it('goes back to the previous body', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'moon' } });
      const [prevBtn] = wrapper.findAll('.nav-btn');
      await prevBtn.trigger('click');
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([CELESTIAL_BODIES[0].id]);
    });

    it('wraps from the first body to the last', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      const [prevBtn] = wrapper.findAll('.nav-btn');
      await prevBtn.trigger('click');
      const lastBody = CELESTIAL_BODIES[CELESTIAL_BODIES.length - 1];
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([lastBody.id]);
    });

    it('falls back to first body when currentId is not found', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'invalid-body' } });
      const [prevBtn] = wrapper.findAll('.nav-btn');
      await prevBtn.trigger('click');
      const lastBody = CELESTIAL_BODIES[CELESTIAL_BODIES.length - 1];
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([lastBody.id]);
    });
  });

  describe('prop reactivity', () => {
    it('updates the active tab when selectedBody prop changes', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      await wrapper.setProps({ selectedBody: 'venus' });
      const activeTab = wrapper.find('.body-tab.active');
      expect(activeTab.text()).toContain('Venus');
    });
  });
});
