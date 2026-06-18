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
      await wrapper.findAll('.body-tab')[1].trigger('click'); // mercury tab
      expect(wrapper.emitted('update:selectedBody')).toBeTruthy();
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual(['mercury']);
    });

    it('emits the correct body id for each enabled tab', async () => {
      for (let i = 0; i < CELESTIAL_BODIES.length; i++) {
        const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
        const body = CELESTIAL_BODIES[i];
        if (body.enabled) {
          await wrapper.findAll('.body-tab')[i].trigger('click');
          expect(wrapper.emitted('update:selectedBody')![0]).toEqual([body.id]);
        }
      }
    });

    it('does not emit when clicking a disabled tab', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      // Earth is disabled (index 3)
      const earthTab = wrapper.findAll('.body-tab')[3];
      expect(earthTab.classes()).toContain('disabled');
      await earthTab.trigger('click');
      expect(wrapper.emitted('update:selectedBody')).toBeFalsy();
    });
  });

  describe('next button', () => {
    it('advances to the next body', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      const [, nextBtn] = wrapper.findAll('.nav-btn');
      await nextBtn.trigger('click');
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual([CELESTIAL_BODIES[1].id]);
    });

    it('skips disabled bodies when navigating forward', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'venus' } });
      const [, nextBtn] = wrapper.findAll('.nav-btn');
      await nextBtn.trigger('click');
      // Venus is index 2, next enabled should be Moon (index 4), skipping Earth (index 3)
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual(['moon']);
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

    it('cycles through all enabled bodies', async () => {
      let wrapper = mount(PlanetCarousel, { props: { selectedBody: 'sun' } });
      const [, nextBtn] = wrapper.findAll('.nav-btn');
      const enabledBodies = CELESTIAL_BODIES.filter(b => b.enabled);

      for (let i = 1; i < enabledBodies.length; i++) {
        await nextBtn.trigger('click');
        expect(wrapper.emitted('update:selectedBody')![i - 1]).toEqual([enabledBodies[i].id]);
      }
    });
  });

  describe('prev button', () => {
    it('goes back to the previous body', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'moon' } });
      const [prevBtn] = wrapper.findAll('.nav-btn');
      await prevBtn.trigger('click');
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual(['venus']);
    });

    it('skips disabled bodies when navigating backward', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'moon' } });
      const [prevBtn] = wrapper.findAll('.nav-btn');
      await prevBtn.trigger('click');
      // Moon is index 4, previous enabled should be Venus (index 2), skipping Earth (index 3)
      expect(wrapper.emitted('update:selectedBody')![0]).toEqual(['venus']);
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

    it('cycles through all enabled bodies backward', async () => {
      const wrapper = mount(PlanetCarousel, { props: { selectedBody: 'mars' } });
      const [prevBtn] = wrapper.findAll('.nav-btn');
      const enabledBodies = CELESTIAL_BODIES.filter(b => b.enabled);

      for (let i = enabledBodies.length - 2; i >= 0; i--) {
        await prevBtn.trigger('click');
        expect(wrapper.emitted('update:selectedBody')).toBeTruthy();
        const emissions = wrapper.emitted('update:selectedBody') || [];
        const lastEmission = emissions[emissions.length - 1];
        expect(lastEmission).toEqual([enabledBodies[i].id]);
      }
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
