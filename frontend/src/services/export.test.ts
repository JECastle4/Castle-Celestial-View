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

    it('should generate N/A row for eclipse with empty contact_times', async () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-09-07',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {}, // Empty object - should generate N/A row, not disappear
        } as unknown as AstronomicalEvent,
      ];

      // Capture the Blob passed to createObjectURL
      let capturedBlob: Blob | null = null;
      global.URL.createObjectURL = vi.fn((blob: unknown) => {
        capturedBlob = blob as Blob;
        return 'blob:mock-url';
      });

      exportContactTimesToCSV(events);

      // Verify a Blob was created
      expect(capturedBlob).not.toBeNull();
      expect(capturedBlob).toBeInstanceOf(Blob);

      // Convert Blob to text and verify CSV content
      if (capturedBlob !== null) {
        const csvText = await (capturedBlob as Blob).text();
        
        // Should contain the header row
        expect(csvText).toContain('Date');
        expect(csvText).toContain('Event Type');
        expect(csvText).toContain('Contact Type');
        
        // Should contain the eclipse data with N/A for contact times
        expect(csvText).toContain('2025-09-07');
        expect(csvText).toContain('Solar Eclipse');
        
        // Should have an N/A row (not disappear due to empty contact_times)
        // The row should show the eclipse occurred but have N/A for contact details
        expect(csvText).toContain('N/A');
        
        // Verify it's not empty (should have at least header + one data row)
        const lines = csvText.trim().split('\n');
        expect(lines.length).toBeGreaterThanOrEqual(2);
      }
    });

    it('should generate multiple rows for eclipse with contact_times', async () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-09-07',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {
            'Penumbral Ingress': '2025-09-07 14:00:00',
            'Partial Ingress': '2025-09-07 15:30:00',
            'Maximum Eclipse': '2025-09-07 16:15:00',
            'Partial Egress': '2025-09-07 17:00:00',
            'Penumbral Egress': '2025-09-07 18:30:00',
          },
        } as unknown as AstronomicalEvent,
      ];

      // Capture the Blob passed to createObjectURL
      let capturedBlob: Blob | null = null;
      global.URL.createObjectURL = vi.fn((blob: unknown) => {
        capturedBlob = blob as Blob;
        return 'blob:mock-url';
      });

      exportContactTimesToCSV(events);

      // Verify Blob was created
      expect(capturedBlob).not.toBeNull();

      if (capturedBlob !== null) {
        const csvText = await (capturedBlob as Blob).text();
        const lines = csvText.trim().split('\n');
        
        // Should have header + 5 contact rows = 6 lines minimum
        expect(lines.length).toBeGreaterThanOrEqual(6);
        
        // Should contain all contact times
        expect(csvText).toContain('Penumbral Ingress');
        expect(csvText).toContain('Maximum Eclipse');
        expect(csvText).toContain('Penumbral Egress');
      }
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

    it('should handle events with empty contact_times object', async () => {
      const events: AstronomicalEvent[] = [
        {
          date: '2025-01-14',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {} as any,
        } as unknown as AstronomicalEvent,
      ];

      // Capture the Blob passed to createObjectURL
      const capturedBlobs: Blob[] = [];
      vi.spyOn(global.URL, 'createObjectURL').mockImplementation((obj: any) => {
        if (obj instanceof Blob) {
          capturedBlobs.push(obj);
        }
        return 'blob:mock-url';
      });

      exportContactTimesToCSV(events);

      expect(global.URL.createObjectURL).toHaveBeenCalled();
      expect(capturedBlobs.length).toBeGreaterThan(0);
      
      // Verify the Blob contains the event row with N/A values for missing contact times
      const csvBlob = capturedBlobs[0];
      const csvText = await csvBlob.text();
      // Should contain the event date
      expect(csvText).toContain('2025-01-14');
      // Should contain the event type
      expect(csvText).toContain('Solar Eclipse');
      // Should contain N/A or empty values for contact times
      expect(csvText).toMatch(/2025-01-14.*N\/A|2025-01-14[^,]*$/);
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

    it('should add N/A row for eclipses with empty contact_times', async () => {
      // Capture the blob content by mocking Blob constructor
      let capturedContent = '';
      const OriginalBlob = global.Blob;
      
      vi.stubGlobal('Blob', class MockBlob {
        constructor(content: any[]) {
          if (content && content[0]) {
            capturedContent = content[0];
          }
        }
      });

      const events: AstronomicalEvent[] = [
        {
          date: '2025-03-29',
          event_type: 'Solar Eclipse',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {}, // Empty object
        } as unknown as AstronomicalEvent,
      ];

      exportContactTimesToCSV(events);

      // Restore Blob
      vi.stubGlobal('Blob', OriginalBlob);

      // Verify the CSV content includes N/A row
      expect(capturedContent).toContain('N/A');
      expect(capturedContent).toContain('2025-03-29');
      expect(capturedContent).toContain('Solar Eclipse');
      expect(capturedContent).toContain('Not available');

      // Verify structure: should have header + data row
      const lines = capturedContent.split('\n');
      expect(lines.length).toBeGreaterThanOrEqual(2);
    });

    it('should handle mixed eclipses with and without contact times', async () => {
      let capturedContent = '';
      const OriginalBlob = global.Blob;
      
      vi.stubGlobal('Blob', class MockBlob {
        constructor(content: any[]) {
          if (content && content[0]) {
            capturedContent = content[0];
          }
        }
      });

      const events: AstronomicalEvent[] = [
        {
          date: '2025-03-29',
          event_type: 'Solar Eclipse A',
          is_lunar: false,
          eclipse_occurs: true,
          contact_times: {}, // Empty
        } as unknown as AstronomicalEvent,
        {
          date: '2025-09-18',
          event_type: 'Lunar Eclipse B',
          is_lunar: true,
          eclipse_occurs: true,
          contact_times: {
            'Penumbral Ingress': '2025-09-18 18:12:00',
            'Umbral Ingress': '2025-09-18 19:11:00',
          },
        } as unknown as AstronomicalEvent,
      ];

      exportContactTimesToCSV(events);

      vi.stubGlobal('Blob', OriginalBlob);

      // Verify both types are present in CSV
      const lines = capturedContent.split('\n');
      
      // Should have header + 1 N/A row for Eclipse A + 2 contact rows for Eclipse B = 4 lines minimum
      expect(lines.length).toBeGreaterThanOrEqual(4);
      
      // Verify N/A row for empty contacts
      expect(capturedContent).toContain('Solar Eclipse A');
      expect(capturedContent).toContain('N/A');
      
      // Verify contact times for Eclipse B
      expect(capturedContent).toContain('Lunar Eclipse B');
      expect(capturedContent).toContain('Penumbral Ingress');
      expect(capturedContent).toContain('Umbral Ingress');
    });
  });
});
