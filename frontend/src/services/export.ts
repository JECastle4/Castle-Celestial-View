/**
 * Export utilities for astronomical data (CSV and JSON formats).
 */

import type { AstronomicalEvent } from '@/types/api.types';

export type ExportFormat = 'csv' | 'json';

/**
 * Export eclipse contact times to CSV format.
 */
export function exportContactTimesToCSV(
  events: AstronomicalEvent[],
  filename: string = 'eclipse-contact-times.csv'
): void {
  const lines: string[] = [];

  // CSV header
  lines.push([
    'Date',
    'Event Type',
    'Is Lunar',
    'Occurs',
    'Contact Type',
    'Time (UTC)',
  ].map(escapeCSVField).join(','));

  // CSV rows - one per contact time
  events.forEach((event) => {
    if (event.eclipse_occurs && event.contact_times) {
      Object.entries(event.contact_times).forEach(([contactType, timeStr]) => {
        lines.push(
          [
            event.date || '',
            event.event_type || '',
            event.is_lunar ? 'Yes' : 'No',
            event.eclipse_occurs ? 'Yes' : 'No',
            contactType,
            timeStr || '',
          ]
            .map(escapeCSVField)
            .join(',')
        );
      });
    } else if (!event.contact_times || Object.keys(event.contact_times).length === 0) {
      // Include event row even if no contact times (for context)
      lines.push(
        [
          event.date || '',
          event.event_type || '',
          event.is_lunar ? 'Yes' : 'No',
          event.eclipse_occurs ? 'Yes' : 'No',
          'N/A',
          'Not available',
        ]
          .map(escapeCSVField)
          .join(',')
      );
    }
  });

  const csvContent = lines.join('\n');
  downloadFile(csvContent, filename, 'text/csv;charset=utf-8;');
}

/**
 * Export eclipse contact times to JSON format.
 */
export function exportContactTimesToJSON(
  events: AstronomicalEvent[],
  filename: string = 'eclipse-contact-times.json'
): void {
  const exportData = {
    exportedAt: new Date().toISOString(),
    count: events.length,
    events: events.map((event) => ({
      date: event.date,
      eventType: event.event_type,
      isLunar: event.is_lunar,
      eclipseOccurs: event.eclipse_occurs,
      contactTimes: event.contact_times || null,
    })),
  };

  const jsonContent = JSON.stringify(exportData, null, 2);
  downloadFile(jsonContent, filename, 'application/json;charset=utf-8;');
}

/**
 * Escape field for CSV format (handle quotes, commas, newlines).
 */
function escapeCSVField(field: string | boolean | null | undefined): string {
  if (field === null || field === undefined) {
    return '';
  }

  const str = String(field);

  // If field contains comma, newline, or quote, wrap in quotes and escape internal quotes
  if (str.includes(',') || str.includes('\n') || str.includes('"')) {
    return `"${str.replace(/"/g, '""')}"`;
  }

  return str;
}

/**
 * Trigger a file download in the browser.
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Generate a timestamp-based filename.
 */
export function generateFilename(format: ExportFormat, prefix: string = 'eclipse-contact-times'): string {
  const timestamp = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const extension = format === 'csv' ? 'csv' : 'json';
  return `${prefix}-${timestamp}.${extension}`;
}
