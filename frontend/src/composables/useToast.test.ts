import { describe, it, vi, expect, beforeEach } from 'vitest';
import { useToast } from './useToast';

// Mock vue-toast-notification composable
vi.mock('vue-toast-notification', () => {
  return {
    useToast: () => ({
      success: vi.fn((msg, opts) => ({ type: 'success', msg, opts })),
      error: vi.fn((msg, opts) => ({ type: 'error', msg, opts })),
      info: vi.fn((msg, opts) => ({ type: 'info', msg, opts })),
      warning: vi.fn((msg, opts) => ({ type: 'warning', msg, opts })),
    }),
  };
});

describe('useToast', () => {
  let toast: ReturnType<typeof useToast>;

  beforeEach(() => {
    toast = useToast();
  });

  it('shows a success toast with defaults', () => {
    const result = toast.success('Success!');
    expect(result).toMatchObject({ type: 'success', msg: 'Success!' });
  });

  it('shows an error toast with custom duration', () => {
    const result = toast.error('Error!', 1234);
    expect(result).toMatchObject({ type: 'error', msg: 'Error!', opts: expect.objectContaining({ duration: 1234 }) });
  });

  it('shows an info toast', () => {
    const result = toast.info('Info!');
    expect(result).toMatchObject({ type: 'info', msg: 'Info!' });
  });

  it('shows a warning toast', () => {
    const result = toast.warning('Warning!');
    expect(result).toMatchObject({ type: 'warning', msg: 'Warning!' });
  });
});
