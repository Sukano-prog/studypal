"""
Audio player with pause/resume and speed control
"""

import sounddevice as sd
import time


class AudioPlayer:
    def __init__(self):
        self.is_playing = False
        self.audio_data = None
        self.sample_rate = None
        self.start_time = 0
        self.seek_offset = 0
        self.total_samples = 0
    
    def play(self, audio_data, sample_rate):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.total_samples = len(audio_data)
        self.is_playing = True
        self.start_time = time.time()
        self.seek_offset = 0
        sd.play(audio_data, sample_rate)
    
    def pause(self):
        if self.is_playing:
            current_time = self.get_current_time()
            self.seek_offset = current_time
            sd.stop()
            self.is_playing = False
    
    def resume(self):
        if not self.is_playing and self.audio_data is not None:
            self.is_playing = True
            self.start_time = time.time()
            position = int(self.seek_offset * self.sample_rate)
            remaining = self.audio_data[position:]
            if len(remaining) > 0:
                sd.play(remaining, self.sample_rate)
    
    def stop(self):
        if self.is_playing:
            sd.stop()
            self.is_playing = False
            self.seek_offset = 0
    
    def seek(self, position_seconds):
        if self.audio_data is None:
            return
        
        max_duration = self.total_samples / self.sample_rate
        if position_seconds < 0:
            position_seconds = 0
        if position_seconds > max_duration:
            position_seconds = max_duration
        
        self.seek_offset = position_seconds
        
        if self.is_playing:
            sd.stop()
            position = int(position_seconds * self.sample_rate)
            remaining = self.audio_data[position:]
            if len(remaining) > 0:
                sd.play(remaining, self.sample_rate)
                self.start_time = time.time()
    
    def set_speed(self, speed):
        """Change playback speed in real-time"""
        if self.is_playing and self.audio_data is not None:
            current_time = self.get_current_time()
            position = int(current_time * self.sample_rate)
            sd.stop()
            remaining = self.audio_data[position:]
            if len(remaining) > 0:
                new_sr = int(self.sample_rate * speed)
                sd.play(remaining, new_sr)
                self.start_time = time.time()
    
    def get_current_time(self):
        """Get current playback position in seconds"""
        if not self.is_playing:
            return self.seek_offset
        
        elapsed = time.time() - self.start_time
        current = self.seek_offset + elapsed
        
        max_duration = self.total_samples / self.sample_rate if self.sample_rate else 0
        if current > max_duration:
            current = max_duration
        
        return current
