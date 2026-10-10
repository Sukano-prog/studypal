"""
Audio player - Manual position tracking
"""

import sounddevice as sd
import time


class AudioPlayer:
    def __init__(self):
        self.audio_data = None
        self.sample_rate = None
        self.is_playing = False
        self.is_paused = False
        self.position = 0.0  # current position in seconds
        self.duration = 0.0
        self.speed = 1.0
        self.start_time = 0.0
        self.last_stream_time = 0.0
    
    def load(self, audio_data, sample_rate):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.base_duration = len(audio_data) / sample_rate   # unscaled
        self.duration = self.base_duration / self.speed      # perceived
        self.position = 0.0
        self.is_playing = False
        self.is_paused = False
    
    def play(self):
        if self.audio_data is None:
            return
        
        if self.is_playing and not self.is_paused:
            return
        
        if self.is_paused:
            # Resume from paused position
            self.is_paused = False
            self.is_playing = True
            start_sample = int(self.position * self.sample_rate)
            remaining = self.audio_data[start_sample:]
            if len(remaining) > 0:
                new_sr = int(self.sample_rate * self.speed)
                sd.play(remaining, new_sr)
                self.start_time = time.time()
                self.last_stream_time = 0
            return
        
        # Start fresh
        self.is_playing = True
        self.is_paused = False
        self.position = 0.0
        sd.play(self.audio_data, int(self.sample_rate * self.speed))
        self.start_time = time.time()
        self.last_stream_time = 0
    
    def play_from(self, position):
        """Start playing from a specific position (does NOT reset to 0)."""
        if self.audio_data is None:
            return
        if position < 0:
            position = 0
        if position > self.duration:
            position = self.duration

        self.position = position
        self.is_playing = True
        self.is_paused = False

        start_sample = int(position * self.sample_rate)
        remaining = self.audio_data[start_sample:]
        if len(remaining) > 0:
            new_sr = int(self.sample_rate * self.speed)
            sd.play(remaining, new_sr)
            self.start_time = time.time()

    def pause(self):
        if not self.is_playing or self.is_paused:
            return
        
        # Calculate position manually
        elapsed = time.time() - self.start_time
        self.position = elapsed + self.position
        
        sd.stop()
        self.is_paused = True
        self.is_playing = False
        print(f"Paused at: {self.position:.2f}s")
    
    def stop(self):
        sd.stop()
        self.is_playing = False
        self.is_paused = False
        self.position = 0.0
    
    def seek(self, position):
        if self.audio_data is None:
            return
        
        if position < 0:
            position = 0
        if position > self.duration:
            position = self.duration
        
        self.position = position
        
        if self.is_playing and not self.is_paused:
            sd.stop()
            start_sample = int(position * self.sample_rate)
            remaining = self.audio_data[start_sample:]
            if len(remaining) > 0:
                new_sr = int(self.sample_rate * self.speed)
                sd.play(remaining, new_sr)
                self.start_time = time.time()
                self.last_stream_time = 0
    
    def set_speed(self, speed):
        if speed < 0.5:
            speed = 0.5
        if speed > 2.0:
            speed = 2.0
        
        old_speed = getattr(self, "speed", 1.0)
        self.speed = speed
        # Recompute perceived duration
        if getattr(self, "base_duration", None) is not None:
            self.duration = self.base_duration / speed
        
        if self.is_playing and not self.is_paused:
            # Get current position (in perceived seconds)
            elapsed = time.time() - self.start_time
            current_pos = elapsed + self.position
            
            # Clamp
            if current_pos >= self.duration:
                self.is_playing = False
                self.is_paused = False
                return
            
            sd.stop()
            start_sample = int(current_pos * self.sample_rate * speed)
            if start_sample > len(self.audio_data):
                start_sample = len(self.audio_data)
            remaining = self.audio_data[start_sample:]
            if len(remaining) > 0:
                new_sr = int(self.sample_rate * speed)
                sd.play(remaining, new_sr)
                self.start_time = time.time()
                self.position = current_pos
                self.last_stream_time = 0
    
    def get_position(self):
        """Get current position in seconds, clamped at duration.
        Auto-marks playback as finished when position >= duration."""
        if self.is_playing and not self.is_paused:
            elapsed = time.time() - self.start_time
            pos = elapsed * self.speed + self.position
            # Clamp at duration
            if pos >= self.duration:
                pos = self.duration
                # Playback finished
                self.is_playing = False
                self.is_paused = False
                self.position = self.duration
                # Also stop sounddevice (safe even if already done)
                try:
                    sd.stop()
                except Exception:
                    pass
                return pos
            return pos
        return self.position
