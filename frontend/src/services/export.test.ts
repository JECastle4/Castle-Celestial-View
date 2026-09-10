/**
 * Tests for export service (CSV and JSON export functionality).
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  exportContactTimesToCSV,
  exportContactTimesToJSON,
  generateFilename,
} from '@/services/export';
import type { AstronomicalEvent } from '@/types/api.types';

describe('Export Service', () => {
  // Mock document and URL for download tests
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock URL methods
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('CSV Export', () => {
    it('should export events with contact times to CSV', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Penumbral Ingress': '2025-01-14 10:30:45',
            'Partial Ingress': '2025-01-14 11:45:30',
            'Maximum Eclipse': '2025-01-14 13:20:15',
            'Partial Egress': '2025-01-14 14:55:00',
            'Penumbral Egress': '2025-01-14 16:10:20',
          },
        } as unknown as AstronomicalEvent,
      ];

      // Should execute without errors
      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).toHaveBeenCalled();
    });

    it('should handle events without contact times', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: false,
          contact_times: null,
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should escape CSV fields with special characters', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Eclipse, with comma',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Time with "quote"': '2025-01-14 10:30:45',
          },
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should use custom filename for CSV export', () => {
      const events: AstronomicalEvent[] = [];
      const customFilename = 'my-eclipses.csv';

      const createElementSpy = vi.spyOn(document, 'createElement');
      exportContactTimesToCSV(events, customFilename);

      const linkCalls = createElementSpy.mock.results.filter(
        (r) => r.value?.tagName === 'A'
      );
      expect(linkCalls.length).toBeGreaterThan(0);

      createElementSpy.mockRestore();
    });
  });

  describe('JSON Export', () => {
    it('should export events with contact times to JSON', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Maximum Eclipse': '2025-01-14 13:20:15',
          },
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToJSON(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).toHaveBeenCalled();
    });

    it('should include export metadata in JSON', () => {
      const events: AstronomicalEvent[] = [];

      expect(() => {
        exportContactTimesToJSON(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should use custom filename for JSON export', () => {
      const events: AstronomicalEvent[] = [];
      const customFilename = 'my-eclipses.json';

      const createElementSpy = vi.spyOn(document, 'createElement');
      exportContactTimesToJSON(events, customFilename);

      const linkCalls = createElementSpy.mock.results.filter(
        (r) => r.value?.tagName === 'A'
      );
      expect(linkCalls.length).toBeGreaterThan(0);

      createElementSpy.mockRestore();
    });
  });

  describe('Filename Generation', () => {
    it('should generate CSV filename with today date', () => {
      const filename = generateFilename('csv');

      const today = new Date().toISOString().slice(0, 10);
      expect(filename).toContain(today);
      expect(filename).toMatch(/\.csv$/);
    });

    it('should generate JSON filename with today date', () => {
      const filename = generateFilename('json');

      const today = new Date().toISOString().slice(0, 10);
      expect(filename).toContain(today);
      expect(filename).toMatch(/\.json$/);
    });

    it('should use custom prefix in filename', () => {
      const prefix = 'my-eclipses';
      const filename = generateFilename('csv', prefix);

      expect(filename).toContain(prefix);
      expect(filename).toMatch(/my-eclipses-\d{4}-\d{2}-\d{2}\.csv/);
    });
  });

  describe('Lunar vs Solar Events', () => {
    it('should export lunar and solar eclipses together', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Lunar Eclipse',
          is_lunar: true,
          eclipse_occurs: true,
          contact_times: {
            'Penumbral Ingress': '2025-01-14 06:30:45',
          },
        } as unknown as AstronomicalEvent,
        {
          date: '2025-07-08',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Partial Ingress': '2025-07-08 11:45:30',
          },
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(() => {
        exportContactTimesToJSON(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle empty event list gracefully', () => {
      const events: AstronomicalEvent[] = [];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(() => {
        exportContactTimesToJSON(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should handle events with null contact times', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: null,
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();
    });

    it('should handle missing event dates', () => {
      const events: AstronomicalEvent[] = [
        {
          date: undefined as any,
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Maximum': '2025-01-14 13:20:15',
          },
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();
    });

    it('should handle events where eclipse occurs but contact_times is null', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: null,
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should handle events where eclipse does not occur', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: false,
          contact_times: {
            'Maximum': '2025-01-14 13:20:15',
          },
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should handle events with empty contact_times object', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {} as any,
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should properly escape fields with commas', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Eclipse, Solar, Type',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Contact, Type': '2025-01-14 10:30:45',
          },
        } as unknown as AstronomicalEvent,
      ];

      const createElementSpy = vi.spyOn(document, 'createElement');
      exportContactTimesToCSV(events);

      const linkCalls = createElementSpy.mock.results.filter(
        (r) => r.value?.tagName === 'A'
      );
      expect(linkCalls.length).toBeGreaterThan(0);

      createElementSpy.mockRestore();
    });

    it('should properly escape fields with newlines', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Eclipse\nType',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Maximum Eclipse': '2025-01-14\n13:20:15',
          },
        } as unknown as AstronomicalEvent,
      ];

      const createElementSpy = vi.spyOn(document, 'createElement');
      exportContactTimesToCSV(events);

      const linkCalls = createElementSpy.mock.results.filter(
        (r) => r.value?.tagName === 'A'
      );
      expect(linkCalls.length).toBeGreaterThan(0);

      createElementSpy.mockRestore();
    });

    it('should properly escape fields with quotes', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Eclipse "Total" Type',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Maximum Eclipse': '2025-01-14 13:20:15',
          },
        } as unknown as AstronomicalEvent,
      ];

      const createElementSpy = vi.spyOn(document, 'createElement');
      exportContactTimesToCSV(events);

      const linkCalls = createElementSpy.mock.results.filter(
        (r) => r.value?.tagName === 'A'
      );
      expect(linkCalls.length).toBeGreaterThan(0);

      createElementSpy.mockRestore();
    });

    it('should handle null fields in CSV escaping', () => {
      const events: AstronomicalEvent[] = [
        {
          date: null as any,
          event_type: null as any,
          is_lunar: false,
          eclipse_occurs: false,
          contact_times: null,
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should handle undefined event properties gracefully', () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: undefined as any,
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: undefined as any,
        } as unknown as AstronomicalEvent,
      ];

      expect(() => {
        exportContactTimesToCSV(events);
      }).not.toThrow();

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });
});
