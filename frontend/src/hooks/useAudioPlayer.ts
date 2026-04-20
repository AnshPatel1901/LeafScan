import { useRef, useState, useCallback, useEffect } from 'react';

/**
 * Custom hook for audio playback control with pause/stop functionality.
 * 
 * Provides:
 * - Play/pause/stop controls
 * - Duration and current time tracking
 * - Volume control
 * - Playback state management
 * - Clean cleanup on unmount
 */

// Get API base URL from environment or use default
const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
};

// Convert relative audio URL to absolute URL
const getAbsoluteAudioUrl = (audioUrl?: string | null): string | null => {
  if (!audioUrl) return null;
  
  // If already absolute, return as-is
  if (audioUrl.startsWith('http://') || audioUrl.startsWith('https://')) {
    return audioUrl;
  }
  
  // If relative path, prepend API base URL (remove /api/v1 suffix and use full domain)
  if (audioUrl.startsWith('/')) {
    const baseUrl = getApiBaseUrl();
    // Extract protocol + domain from baseUrl
    const url = new URL(baseUrl);
    return `${url.protocol}//${url.host}${audioUrl}`;
  }
  
  return audioUrl;
};

export const useAudioPlayer = (audioUrl?: string | null) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update current time as audio plays
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
      setIsLoading(false);
    };

    const handleLoadStart = () => {
      console.log('AudioPlayer: Load started', { src: audio?.src });
      setIsLoading(true);
      setError(null);
    };

    const handleError = () => {
      const audio = audioRef.current;
      const errorMsg = audio?.error?.message || 'Failed to load audio';
      const errorCode = audio?.error?.code || 'UNKNOWN';
      
      // Log detailed error info for debugging
      console.error('AudioPlayer Error:', {
        code: errorCode,
        message: errorMsg,
        currentSrc: audio?.src,
        networkState: audio?.networkState,
        readyState: audio?.readyState,
      });
      
      setError(`Failed to load audio (${errorCode})`);
      setIsLoading(false);
      setIsPlaying(false);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('error', handleError);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  // Update audio src when URL changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audioUrl) {
      const absoluteUrl = getAbsoluteAudioUrl(audioUrl);
      audio.src = absoluteUrl || '';
      setCurrentTime(0);
      setIsPlaying(false);
      setError(null);
    } else {
      audio.src = '';
      setIsPlaying(false);
    }
  }, [audioUrl]);

  // Play
  const play = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;

    try {
      setError(null);
      await audio.play();
      setIsPlaying(true);
    } catch (err) {
      setError('Failed to play audio');
      setIsPlaying(false);
    }
  }, [audioUrl]);

  // Pause
  const pause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.pause();
    setIsPlaying(false);
  }, []);

  // Stop (pause and reset to beginning)
  const stop = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.pause();
    audio.currentTime = 0;
    setCurrentTime(0);
    setIsPlaying(false);
  }, []);

  // Toggle play/pause
  const togglePlayPause = useCallback(async () => {
    if (isPlaying) {
      pause();
    } else {
      await play();
    }
  }, [isPlaying, play, pause]);

  // Seek to specific time
  const seek = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = Math.max(0, Math.min(time, duration));
    setCurrentTime(audio.currentTime);
  }, [duration]);

  // Set volume (0-1)
  const setAudioVolume = useCallback((vol: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    const clampedVolume = Math.max(0, Math.min(1, vol));
    audio.volume = clampedVolume;
    setVolume(clampedVolume);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.src = '';
      }
    };
  }, []);

  return {
    audioRef,
    isPlaying,
    duration,
    currentTime,
    volume,
    isLoading,
    error,
    play,
    pause,
    stop,
    togglePlayPause,
    seek,
    setAudioVolume,
    isReady: !isLoading && !!audioUrl,
  };
};
