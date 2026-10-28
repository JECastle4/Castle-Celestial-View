import { mount } from '@vue/test-utils';
import DateRangePicker from './DateRangePicker.vue';

describe('DateRangePicker', () => {
  it('emits dateRangeChanged when Apply is clicked', async () => {
    const wrapper = mount(DateRangePicker, {
        props: {
            initialStartDate: '2026-02-01',
            initialEndDate: '2026-02-07'
        }
    });
    // Set a valid date range
    //await wrapper.setData({ startDate: '2026-02-01', endDate: '2026-02-07' });
    // Find and click the Apply button
    const applyBtn = wrapper.find('button');
    await applyBtn.trigger('click');
    await wrapper.vm.$nextTick();
    // Check emitted event
    const emitted = wrapper.emitted('update:dates');
    expect(emitted).toBeTruthy();
    const eventPayload = emitted && emitted[0] && emitted[0][0] as { start: Date; end: Date } | undefined;
    expect(eventPayload).not.toBeNull();
    expect(eventPayload).not.toBeUndefined();
    expect(eventPayload && eventPayload.start).toEqual(new Date('2026-02-01'));
    expect(eventPayload && eventPayload.end).toEqual(new Date('2026-02-07'));
  });

  describe('disabled prop reactivity', () => {
    it('should disable date inputs when disabled prop is false initially', () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: false
        }
      });

      const inputs = wrapper.findAll('input[type="date"]');
      expect(inputs).toHaveLength(2);
      expect(inputs[0].attributes('disabled')).toBeUndefined();
      expect(inputs[1].attributes('disabled')).toBeUndefined();
    });

    it('should disable date inputs when disabled prop is true initially', () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: true
        }
      });

      const inputs = wrapper.findAll('input[type="date"]');
      expect(inputs).toHaveLength(2);
      expect(inputs[0].attributes('disabled')).toBeDefined();
      expect(inputs[1].attributes('disabled')).toBeDefined();
    });

    it('should reactively disable inputs when parent updates disabled prop from false to true', async () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: false
        }
      });

      // Initially enabled
      let inputs = wrapper.findAll('input[type="date"]');
      expect(inputs[0].attributes('disabled')).toBeUndefined();
      expect(inputs[1].attributes('disabled')).toBeUndefined();

      // Update prop to disabled=true
      await wrapper.setProps({ disabled: true });
      await wrapper.vm.$nextTick();

      // Should now be disabled
      inputs = wrapper.findAll('input[type="date"]');
      expect(inputs[0].attributes('disabled')).toBeDefined();
      expect(inputs[1].attributes('disabled')).toBeDefined();
    });

    it('should reactively enable inputs when parent updates disabled prop from true to false', async () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: true
        }
      });

      // Initially disabled
      let inputs = wrapper.findAll('input[type="date"]');
      expect(inputs[0].attributes('disabled')).toBeDefined();
      expect(inputs[1].attributes('disabled')).toBeDefined();

      // Update prop to disabled=false
      await wrapper.setProps({ disabled: false });
      await wrapper.vm.$nextTick();

      // Should now be enabled
      inputs = wrapper.findAll('input[type="date"]');
      expect(inputs[0].attributes('disabled')).toBeUndefined();
      expect(inputs[1].attributes('disabled')).toBeUndefined();
    });

    it('should reactively disable Apply button when disabled prop changes to true', async () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: false
        }
      });

      // Initially enabled (if dates are valid)
      let applyBtn = wrapper.find('button');

      // Update prop to disabled=true
      await wrapper.setProps({ disabled: true });
      await wrapper.vm.$nextTick();

      // Button should now be disabled
      applyBtn = wrapper.find('button');
      expect(applyBtn.attributes('disabled')).toBeDefined();
    });

    it('should not prevent Apply button from being enabled based on dates when disabled is false', async () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: false
        }
      });

      const applyBtn = wrapper.find('button');
      // Button should be enabled if dates are valid and disabled=false
      // (it's only disabled if !isValid || disabled)
      expect(applyBtn.attributes('disabled')).toBeUndefined();
    });

    it('should keep Apply button disabled when disabled=true even if dates are valid', async () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: true
        }
      });

      const applyBtn = wrapper.find('button');
      // Button should be disabled because disabled=true
      expect(applyBtn.attributes('disabled')).toBeDefined();
    });

    it('should allow toggling between disabled/enabled multiple times', async () => {
      const wrapper = mount(DateRangePicker, {
        props: {
          initialStartDate: '2026-02-01',
          initialEndDate: '2026-02-07',
          disabled: false
        }
      });

      const getInputDisabledState = () => {
        const inputs = wrapper.findAll('input[type="date"]');
        return inputs[0].attributes('disabled') !== undefined;
      };

      // Start enabled
      expect(getInputDisabledState()).toBe(false);

      // Toggle to disabled
      await wrapper.setProps({ disabled: true });
      await wrapper.vm.$nextTick();
      expect(getInputDisabledState()).toBe(true);

      // Toggle back to enabled
      await wrapper.setProps({ disabled: false });
      await wrapper.vm.$nextTick();
      expect(getInputDisabledState()).toBe(false);

      // Toggle to disabled again
      await wrapper.setProps({ disabled: true });
      await wrapper.vm.$nextTick();
      expect(getInputDisabledState()).toBe(true);
    });
  });
});
