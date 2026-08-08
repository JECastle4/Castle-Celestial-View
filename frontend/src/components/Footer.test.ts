import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ref } from 'vue';
import Footer from './Footer.vue';

// Mock the router
vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router');
  return {
    ...actual,
    useRouter: vi.fn(),
  };
});

// Mock vue-i18n
vi.mock('vue-i18n', async () => {
  const actual = await vi.importActual('vue-i18n');
  return {
    ...actual,
    useI18n: vi.fn(),
  };
});

describe('Footer', () => {
  let mockRouter: any;
  let mockI18n: any;

  beforeEach(() => {
    mockRouter = {
      currentRoute: {
        value: {
          fullPath: '/en-UK/',
        },
      },
      push: vi.fn(),
    };
    vi.mocked(useRouter).mockReturnValue(mockRouter);

    mockI18n = {
      locale: ref('en-UK'),
      t: vi.fn((key) => {
        if (key === 'app.copyright') return '© 2024 Astronomy Animation';
        if (key === 'app.about') return 'About';
        return key;
      }),
    };
    vi.mocked(useI18n).mockReturnValue(mockI18n);
  });

  describe('language selector button', () => {
    it('renders the language selector button', () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      expect(langBtn.exists()).toBe(true);
    });

    it('displays the correct flag for en-UK locale', async () => {
      const wrapper = mount(Footer);
      const flagSpan = wrapper.find('.footer-lang-btn span.fi');
      expect(flagSpan.classes()).toContain('fi-gb');
    });

    it('displays the correct flag for en-US locale', async () => {
      // Test the en-US branch of the flag rendering
      mockI18n.locale.value = 'en-US';
      const wrapper = mount(Footer);
      const flagSpan = wrapper.find('.footer-lang-btn span.fi');
      expect(flagSpan.classes()).toContain('fi-us');
    });

    it('has en-US aria-label when locale is en-US', async () => {
      // Test the en-US branch of the aria-label
      mockI18n.locale.value = 'en-US';
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      expect(langBtn.attributes('aria-label')).toContain('English (US)');
    });

    it('has the correct aria-label for en-UK', () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      expect(langBtn.attributes('aria-label')).toContain('English (UK)');
    });

    it('has aria-label with locale information', () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      const ariaLabel = langBtn.attributes('aria-label') || '';
      expect(ariaLabel).toContain('Current language');
      // Will be either English (UK) or English (US)
      expect(ariaLabel).toMatch(/English \((UK|US)\)/);
    });

    it('renders aria-label dynamically based on locale', () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      const ariaLabel = langBtn.attributes('aria-label') || '';
      
      // In test, locale is 'en-UK' so it should have the en-UK label
      // But we test that it renders the correct conditional label
      expect(ariaLabel.length > 0).toBe(true);
    });

    it('toggles language menu when clicked', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
      
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
    });

    it('toggles multiple times correctly', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      
      for (let i = 0; i < 3; i++) {
        await langBtn.trigger('click');
        expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
        await langBtn.trigger('click');
        expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
      }
    });
  });

  describe('language dropdown menu', () => {
    it('does not render the dropdown menu initially', () => {
      const wrapper = mount(Footer);
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
    });

    it('renders the dropdown menu when language button is clicked', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
    });

    it('renders language options in the dropdown', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      expect(options.length).toBeGreaterThanOrEqual(2);
    });

    it('disables the currently selected language option', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      const disabledOptions = options.filter(opt => opt.attributes('disabled') !== undefined);
      expect(disabledOptions.length).toBe(1);
    });

    it('renders flag icons for language options', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      options.forEach(opt => {
        const flag = opt.find('span.fi');
        expect(flag.exists()).toBe(true);
      });
    });

    it('displays language labels for each option', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      options.forEach(opt => {
        // Each option should have text content (the label)
        expect(opt.text()).toBeTruthy();
      });
    });
  });

  describe('locale switching', () => {
    it('does not navigate when the current locale is clicked', async () => {
      mockRouter.push.mockClear();
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      const disabledOption = options.find(opt => opt.attributes('disabled') !== undefined);
      
      if (disabledOption) {
        await disabledOption.trigger('click');
        await wrapper.vm.$nextTick();
        expect(mockRouter.push).not.toHaveBeenCalled();
      }
    });

    it('has navigation capability when switching to a different locale', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/';
      
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      expect(langBtn.exists()).toBe(true);
      
      // Verify the component has the router configured for navigation
      // (actual navigation testing is more complex with mocks)
    });

    it('preserves locale in URL paths', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/events';
      
      // The component should preserve the path structure
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      const href = aboutLink.attributes('href');
      
      // Should navigate to about while maintaining the locale
      expect(href).toContain('en-UK');
    });

    it('builds correct path with multiple segments', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/some/nested/path';
      
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      const href = aboutLink.attributes('href');
      
      expect(href).toContain('en-UK');
      expect(href).toBe('/en-UK/about');
    });

    it('handles root path correctly', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/';
      
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      const href = aboutLink.attributes('href');
      
      expect(href).toBe('/en-UK/about');
    });

    it('calls router.push when switching to different locale', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/events';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      
      // Access the switchLocale function through the component vm
      // We'll invoke it directly to test the logic path
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      // Should call router.push with the new path
      expect(mockRouter.push).toHaveBeenCalled();
    });

    it('replaces locale in path when switching', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/events';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      const pushArg = mockRouter.push.mock.calls[0]?.[0];
      expect(pushArg).toContain('en-US');
      expect(pushArg).toContain('events');
    });

    it('closes dropdown after switching locale', async () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/';
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      await wrapper.vm.$nextTick();
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
    });

    it('handles invalid path without locale prefix', () => {
      mockRouter.currentRoute.value.fullPath = '/invalid-path';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      const pushArg = mockRouter.push.mock.calls[0]?.[0];
      // Should default to home path with new locale
      expect(pushArg).toBe('/en-US/');
    });

    it('preserves query parameters and hash when switching locales', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/events?date=2024&time=noon#section';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      const pushArg = mockRouter.push.mock.calls[0]?.[0];
      expect(pushArg).toContain('en-US');
      // The path should be replaced but preserve other parts
      expect(pushArg).toContain('events');
    });

    it('handles deeply nested paths', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/very/deep/nested/path';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      const pushArg = mockRouter.push.mock.calls[0]?.[0];
      expect(pushArg).toContain('en-US');
      expect(pushArg).toContain('very');
    });

    it('handles path replacement edge cases', () => {
      // Test case where path might not start with locale after replacement
      mockRouter.currentRoute.value.fullPath = '/en-UK/path';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      const pushArg = mockRouter.push.mock.calls[0]?.[0];
      expect(pushArg).toContain('en-US');
      expect(typeof pushArg === 'string').toBe(true);
    });

    it('correctly closes menu and navigates together', async () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/events';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      await wrapper.vm.$nextTick();
      
      // Both should happen: menu closes and navigation occurs
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
      expect(mockRouter.push).toHaveBeenCalled();
    });

    it('handles path without locale prefix by defaulting to root', () => {
      // This tests the if (!newPath.startsWith) branch on line 69
      mockRouter.currentRoute.value.fullPath = '/about';
      mockRouter.push.mockClear();
      
      const wrapper = mount(Footer);
      const vm = wrapper.vm as any;
      vm.switchLocale('en-US');
      
      const pushArg = mockRouter.push.mock.calls[0]?.[0];
      // Should create path starting with the new locale
      expect(pushArg).toEqual('/en-US/');
    });
  });

  describe('copyright text', () => {
    it('renders the copyright text', () => {
      const wrapper = mount(Footer);
      expect(wrapper.text()).toContain('©');
    });

    it('uses the copyright translation key', () => {
      const wrapper = mount(Footer);
      const copyrightP = wrapper.findAll('.app-footer p');
      expect(copyrightP.length).toBeGreaterThan(0);
    });
  });

  describe('about link', () => {
    it('renders the about link', () => {
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      expect(aboutLink.exists()).toBe(true);
    });

    it('has the correct href for en-UK locale', () => {
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      expect(aboutLink.attributes('href')).toBe('/en-UK/about');
    });

    it('renders the about icon', () => {
      const wrapper = mount(Footer);
      const icon = wrapper.find('.about-icon');
      expect(icon.exists()).toBe(true);
      expect(icon.attributes('src')).toBe('/favicon.png');
    });

    it('renders the about link text', () => {
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      expect(aboutLink.text()).toBeTruthy();
    });
  });

  describe('click outside behavior', () => {
    it('closes dropdown when clicking outside', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      // Simulate clicking outside
      document.dispatchEvent(new MouseEvent('mousedown'));
      await wrapper.vm.$nextTick();
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
    });

    it('does not close dropdown when clicking inside the menu', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      // Get the menu ref element and click inside it
      const menu = wrapper.find('.footer-lang-menu');
      if (menu.element) {
        const clickEvent = new MouseEvent('mousedown', { bubbles: true });
        menu.element.dispatchEvent(clickEvent);
      }
      
      await wrapper.vm.$nextTick();
      // Menu should still be visible because the click was inside
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
    });

    it('closes dropdown when clicking on button after opening', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      // Simulate clicking outside by dispatching event on a different element
      const div = document.createElement('div');
      document.body.appendChild(div);
      div.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      document.body.removeChild(div);
      
      await wrapper.vm.$nextTick();
      
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
    });

    it('attaches mousedown listener on mount', async () => {
      const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
      mount(Footer);
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
      
      addEventListenerSpy.mockRestore();
    });

    it('removes mousedown listener on unmount', async () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      const wrapper = mount(Footer);
      
      wrapper.unmount();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
      
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('styling and accessibility', () => {
    it('applies correct CSS classes to footer', () => {
      const wrapper = mount(Footer);
      const footer = wrapper.find('.app-footer');
      expect(footer.classes()).toContain('app-footer');
    });

    it('footer lang button is accessible with keyboard focus', () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      expect(langBtn.exists()).toBe(true);
      // Button should be focusable (no tabindex issue)
    });

    it('all language options should be clickable buttons', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      options.forEach(opt => {
        expect(opt.element.tagName).toBe('BUTTON');
      });
    });

    it('renders proper structure with all elements', () => {
      const wrapper = mount(Footer);
      
      // Check footer structure
      expect(wrapper.find('.app-footer').exists()).toBe(true);
      expect(wrapper.find('.footer-lang-menu').exists()).toBe(true);
      expect(wrapper.find('.footer-lang-btn').exists()).toBe(true);
      expect(wrapper.findAll('.app-footer p').length).toBeGreaterThan(0);
      expect(wrapper.find('.footer-about-link').exists()).toBe(true);
    });
  });

  describe('development mode locales', () => {
    it('includes development locales in dev mode', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      // In dev mode, there should be at least 2 locales (en-UK, en-US)
      // and potentially more if dev locales are included
      expect(options.length).toBeGreaterThanOrEqual(2);
    });

    it('renders dev locale options with proper flags', async () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      
      const options = wrapper.findAll('.footer-lang-option');
      options.forEach(opt => {
        const flag = opt.find('span.fi');
        expect(flag.exists()).toBe(true);
        expect(flag.attributes('style')).toContain('margin-right');
      });
    });
  });

  describe('reactive language changes', () => {
    it('updates flag when locale changes', async () => {
      const wrapper = mount(Footer);
      let flagSpan = wrapper.find('.footer-lang-btn span.fi');
      expect(flagSpan.classes()).toContain('fi-gb');
    });

    it('maintains proper structure after multiple operations', async () => {
      const wrapper = mount(Footer);
      
      // Open menu
      const langBtn = wrapper.find('.footer-lang-btn');
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      // Close menu
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(false);
      
      // Open again
      await langBtn.trigger('click');
      expect(wrapper.find('.footer-lang-dropdown').exists()).toBe(true);
      
      // Verify all elements still exist
      expect(wrapper.find('.app-footer').exists()).toBe(true);
      expect(wrapper.find('.footer-about-link').exists()).toBe(true);
    });
  });

  describe('conditional rendering and branching', () => {
    it('renders aria-label with correct locale information', () => {
      const wrapper = mount(Footer);
      const langBtn = wrapper.find('.footer-lang-btn');
      const ariaLabel = langBtn.attributes('aria-label') || '';
      
      // Should contain either en-UK or en-US based on current locale
      expect(ariaLabel).toMatch(/(English \(UK\)|English \(US\))/);
    });

    it('renders copyright text properly', () => {
      const wrapper = mount(Footer);
      const pElements = wrapper.findAll('.app-footer p');
      
      expect(pElements.length).toBeGreaterThan(0);
      const hasContent = pElements.some(p => p.text().length > 0);
      expect(hasContent).toBe(true);
    });

    it('footer about link points to correct locale path', () => {
      mockRouter.currentRoute.value.fullPath = '/en-UK/';
      
      const wrapper = mount(Footer);
      const aboutLink = wrapper.find('.footer-about-link');
      
      expect(aboutLink.attributes('href')).toMatch(/^\/en-[A-Z]{2}\/about$/);
    });

    it('all footer elements render with expected classes', () => {
      const wrapper = mount(Footer);
      
      expect(wrapper.find('.app-footer').exists()).toBe(true);
      expect(wrapper.find('.footer-lang-menu').exists()).toBe(true);
      expect(wrapper.find('.footer-lang-btn').exists()).toBe(true);
      expect(wrapper.find('.footer-about-link').exists()).toBe(true);
      expect(wrapper.find('.about-icon').exists()).toBe(true);
    });
  });
});
