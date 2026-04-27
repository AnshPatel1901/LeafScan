"use client";

import { useEffect } from "react";
import { setupGlobalErrorHandling } from "@/lib/errorInterceptor";

/**
 * Initializes global error handling on app startup
 */
export function ErrorHandlerInitializer() {
  useEffect(() => {
    setupGlobalErrorHandling();
  }, []);

  return null;
}
