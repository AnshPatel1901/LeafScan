import React, { FC } from "react";
import {
  Play,
  Pause,
  StopCircle,
  Volume2,
  AlertCircle,
  Loader,
} from "lucide-react";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";
import { useAudioKeyboardShortcuts } from "@/hooks/useAudioKeyboardShortcuts";

interface AudioPlayerProps {
  audioUrl?: string | null;
  language?: string;
  title?: string;
  className?: string;
}

/**
 * AudioPlayer Component
 *
 * Provides controls to play, pause, and stop TTS audio playback.
 * Features:
 * - Play/Pause toggle
 * - Stop button (returns to beginning)
 * - Progress bar with seek support
 * - Volume control
 * - Current time and duration display
 * - Loading and error states
 *
 * Usage:
 * ```tsx
 * <AudioPlayer audioUrl={audio_url} language="hi" title="Disease Treatment Advice" />
 * ```
 */
const AudioPlayer: FC<AudioPlayerProps> = ({
  audioUrl,
  language = "en",
  title = "Treatment Advice (Audio)",
  className = "",
}) => {
  const {
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
    isReady,
  } = useAudioPlayer(audioUrl);

  // Enable keyboard shortcuts
  useAudioKeyboardShortcuts(togglePlayPause, stop, isReady);

  // Format time in MM:SS
  const formatTime = (time: number): string => {
    if (!isFinite(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  // If no audio URL, don't render anything
  if (!audioUrl) {
    return null;
  }

  return (
    <div
      className={`
        w-full bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-700
        rounded-lg border border-blue-200 dark:border-slate-600
        p-4 space-y-3 shadow-sm
        ${className}
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Volume2 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {title}
        </h3>
        {isLoading && (
          <Loader className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin ml-auto" />
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
          <span className="text-sm text-red-700 dark:text-red-300">
            {error}
          </span>
        </div>
      )}

      {/* Progress bar */}
      <div className="space-y-1">
        <input
          type="range"
          min="0"
          max={duration || 0}
          value={currentTime}
          onChange={(e) => seek(Number(e.target.value))}
          disabled={!isReady}
          className="w-full h-1.5 bg-slate-300 dark:bg-slate-600 rounded-full appearance-none cursor-pointer
                     disabled:opacity-50 disabled:cursor-not-allowed
                     [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5
                     [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-webkit-slider-thumb]:shadow-md
                     [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:rounded-full
                     [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:border-none"
          aria-label="Audio progress"
        />
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {/* Play/Pause button */}
        <button
          onClick={togglePlayPause}
          disabled={!isReady}
          className="
            flex items-center justify-center gap-2 px-3 py-2
            bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700
            text-white font-medium rounded-lg transition-colors
            disabled:bg-slate-300 dark:disabled:bg-slate-600 disabled:cursor-not-allowed
            shadow-sm hover:shadow-md
          "
          aria-label={isPlaying ? "Pause audio" : "Play audio"}
          title={isPlaying ? "Pause (Space)" : "Play (Space)"}
        >
          {isPlaying ? (
            <>
              <Pause className="w-4 h-4" />
              <span className="hidden sm:inline">Pause</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              <span className="hidden sm:inline">Play</span>
            </>
          )}
        </button>

        {/* Stop button */}
        <button
          onClick={stop}
          disabled={!isReady || currentTime === 0}
          className="
            flex items-center justify-center gap-2 px-3 py-2
            bg-slate-300 hover:bg-slate-400 dark:bg-slate-600 dark:hover:bg-slate-700
            text-slate-700 dark:text-slate-200 font-medium rounded-lg transition-colors
            disabled:bg-slate-200 dark:disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed
            shadow-sm hover:shadow-md
          "
          aria-label="Stop audio"
          title="Stop (Return to beginning)"
        >
          <StopCircle className="w-4 h-4" />
          <span className="hidden sm:inline">Stop</span>
        </button>

        {/* Volume control */}
        <div className="ml-auto flex items-center gap-2">
          <Volume2 className="w-4 h-4 text-slate-600 dark:text-slate-400" />
          <input
            type="range"
            min="0"
            max="100"
            value={volume * 100}
            onChange={(e) => setAudioVolume(Number(e.target.value) / 100)}
            disabled={!isReady}
            className="w-16 h-1.5 bg-slate-300 dark:bg-slate-600 rounded-full appearance-none cursor-pointer
                       disabled:opacity-50 disabled:cursor-not-allowed
                       [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3
                       [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-slate-600 dark:[&::-webkit-slider-thumb]:bg-slate-400
                       [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-moz-range-thumb]:w-3 [&::-moz-range-thumb]:h-3 [&::-moz-range-thumb]:rounded-full
                       [&::-moz-range-thumb]:bg-slate-600 dark:[&::-moz-range-thumb]:bg-slate-400 [&::-moz-range-thumb]:cursor-pointer
                       [&::-moz-range-thumb]:border-none"
            aria-label="Volume control"
            title={`Volume: ${Math.round(volume * 100)}%`}
          />
          <span className="text-xs text-slate-600 dark:text-slate-400 w-6 text-right">
            {Math.round(volume * 100)}%
          </span>
        </div>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} crossOrigin="anonymous" />

      {/* Keyboard shortcuts help (optional, visible on hover) */}
      <div className="text-xs text-slate-500 dark:text-slate-400 opacity-0 hover:opacity-100 transition-opacity">
        <p>Keyboard: Space = Play/Pause | S = Stop</p>
      </div>
    </div>
  );
};

export default AudioPlayer;
