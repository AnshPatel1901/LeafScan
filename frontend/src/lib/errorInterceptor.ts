/**
 * Browser Console Error Interceptor
 * 
 * Improves error logging in the browser console by:
 * - Formatting error objects to readable strings
 * - Extracting useful information from API errors
 * - Adding timestamps and context
 * 
 * This runs automatically in all pages.
 */

export function setupGlobalErrorHandling() {
  // Store original console.error
  const originalError = console.error;

  /**
   * Improved console.error that formats objects better
   */
  console.error = function (...args: any[]) {
    // Call original first
    originalError.apply(console, args);

    // Try to format error objects into readable strings
    const formatted = args.map((arg) => {
      // If it's an Error object
      if (arg instanceof Error) {
        return `${arg.name}: ${arg.message}\nStack: ${arg.stack}`;
      }

      // If it's an Axios error with response
      if (arg && typeof arg === 'object' && 'response' in arg) {
        const axiosErr = arg as any;
        const status = axiosErr.response?.status || 'unknown';
        const statusText = axiosErr.response?.statusText || '';
        const message = axiosErr.response?.data?.message || axiosErr.message || '';
        const detail = axiosErr.response?.data?.detail || '';

        return (
          `Axios Error [${status} ${statusText}]: ${message || detail || 'Unknown error'}` +
          (axiosErr.config ? `\nEndpoint: ${axiosErr.config.method?.toUpperCase()} ${axiosErr.config.url}` : '')
        );
      }

      // If it's a plain object (not Promise or Function), stringify it
      if (
        arg &&
        typeof arg === 'object' &&
        !(arg instanceof Promise) &&
        typeof arg !== 'function'
      ) {
        try {
          return JSON.stringify(arg, null, 2);
        } catch {
          return String(arg);
        }
      }

      // Otherwise return as-is
      return arg;
    });

    // Log the formatted message as well
    if (formatted.some((f) => typeof f === 'string' && f.length > 20)) {
      originalError('[FORMATTED]', ...formatted);
    }
  };
}

// Auto-setup in browser
if (typeof window !== 'undefined') {
  setupGlobalErrorHandling();
}
