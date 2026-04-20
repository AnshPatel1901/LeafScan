import { useEffect } from 'react';

/**
 * Custom hook for keyboard shortcuts in audio player.
 * 
 * Supports:
 * - Space: Play/Pause
 * - S: Stop
 * 
 * Only works when a text input/textarea is not focused.
 */
export const useAudioKeyboardShortcuts = (
  onPlayPause: () => void,
  onStop: () => void,
  enabled: boolean = true
) => {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        onPlayPause();
      } else if (e.code === 'KeyS' || e.key === 's' || e.key === 'S') {
        e.preventDefault();
        onStop();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onPlayPause, onStop, enabled]);
};
