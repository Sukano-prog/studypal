#!/usr/bin/env python3
"""
Test Read-Along with Audio - Tkinter version
"""

import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import threading
import time
import subprocess
import os
import re
import tempfile
import sounddevice as sd
import soundfile as sf
import numpy as np


class ReadAlongWithAudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Read-Along Player (Test)")
        self.root.geometry("900x700")
        
        # State
        self.alignments = []
        self.current_index = 0
        self.is_playing = False
        self.audio_data = None
        self.sample_rate = None
        self.text_content = ""
        self.audio_file = None
        self.playback_thread = None
        self.stop_flag = False
        
        # UI
        self.setup_ui()
    
    def setup_ui(self):
        # Text display
        self.text_widget = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=("Arial", 14), height=15
        )
        self.text_widget.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        self.text_widget.config(state=tk.DISABLED)
        
        # Buttons frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        self.upload_btn = tk.Button(btn_frame, text="📄 Upload Document", command=self.upload_document)
        self.upload_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = tk.Button(btn_frame, text="▶ Play", command=self.play_audio, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = tk.Label(self.root, text="Ready - Upload a document", fg="blue")
        self.status_label.pack(pady=5)
        
        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Scale(
            self.root, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.progress_var, state=tk.DISABLED, length=400
        )
        self.progress_bar.pack(pady=5)
    
    def upload_document(self):
        """Upload a text document"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.text_content = f.read()
            
            if not self.text_content.strip():
                messagebox.showerror("Error", "File is empty")
                return
            
            # Display text
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", self.text_content)
            self.text_widget.config(state=tk.DISABLED)
            
            self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}", fg="green")
            self.play_btn.config(state=tk.NORMAL)
            self.progress_bar.config(state=tk.NORMAL)
            self.progress_var.set(0)
            
            # Generate audio using Piper
            self.generate_audio()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")
    
    def generate_audio(self):
        """Generate audio using Piper TTS"""
        self.status_label.config(text="Generating speech...", fg="orange")
        self.play_btn.config(state=tk.DISABLED)
        
        def generate():
            try:
                # Create temp file for output
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    output_file = tmp.name
                
                # Write text to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
                    input_file = tmp.name
                    tmp.write(self.text_content)
                
                # Piper model path
                model_path = os.path.expanduser("~/.local/share/piper/en_US-lessac-medium.onnx")
                
                if not os.path.exists(model_path):
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", 
                        "Piper model not found.\nDownload with:\n"
                        "cd ~/.local/share/piper\n"
                        "wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
                    ))
                    self.root.after(0, lambda: self.status_label.config(text="Error: Model not found", fg="red"))
                    return
                
                # Find espeak data
                espeak_data = None
                possible_paths = [
                    "/usr/lib/x86_64-linux-gnu/espeak-ng-data",
                    "/usr/share/espeak-ng-data",
                    "/usr/lib/espeak-ng-data",
                    "/usr/local/share/espeak-ng-data"
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        espeak_data = path
                        break
                
                # Run Piper with espeak_data if found
                cmd = [
                    "piper",
                    "--model", model_path,
                    "--output_file", output_file
                ]
                
                if espeak_data:
                    cmd.extend(["--espeak_data", espeak_data])
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                with open(input_file, 'rb') as f:
                    text_bytes = f.read()
                
                stdout, stderr = process.communicate(text_bytes, timeout=60)
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    raise Exception(f"Piper error: {error_msg}")
                
                # Read audio
                if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                    raise Exception("Piper produced empty audio")
                
                self.audio_data, self.sample_rate = sf.read(output_file)
                
                # Clean up
                try:
                    os.unlink(output_file)
                except:
                    pass
                try:
                    os.unlink(input_file)
                except:
                    pass
                
                # Generate alignments
                self.generate_alignments()
                
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Ready - {len(self.alignments)} words loaded", fg="green"
                ))
                self.root.after(0, lambda: self.play_btn.config(state=tk.NORMAL))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"TTS failed:\n{e}"))
                self.root.after(0, lambda: self.status_label.config(text="Error generating speech", fg="red"))
                self.root.after(0, lambda: self.play_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def generate_alignments(self):
        """Generate word timings based on audio duration"""
        if self.audio_data is None or self.sample_rate is None:
            return
        
        audio_duration = len(self.audio_data) / self.sample_rate
        
        # Split text into words
        words = re.findall(r'\S+', self.text_content)
        
        if not words:
            return
        
        # Calculate time per word
        total_words = len(words)
        time_per_word = audio_duration / total_words
        
        self.alignments = []
        char_pos = 0
        
        for i, word in enumerate(words):
            # Find actual position in text
            start_pos = self.text_content.find(word, char_pos)
            if start_pos == -1:
                continue
            
            self.alignments.append({
                'word': word,
                'start': i * time_per_word,
                'end': (i + 1) * time_per_word,
                'char_start': start_pos,
                'char_end': start_pos + len(word)
            })
            char_pos = start_pos + len(word)
    
    def play_audio(self):
        """Play audio with highlighting"""
        if not self.alignments or self.audio_data is None:
            return
        
        self.is_playing = True
        self.stop_flag = False
        self.current_index = 0
        
        self.play_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Playing...", fg="blue")
        
        def play_loop():
            try:
                # Start audio playback
                sd.play(self.audio_data, self.sample_rate)
                
                # Highlight words based on timing
                while self.is_playing and self.current_index < len(self.alignments):
                    if self.stop_flag:
                        break
                    
                    # Highlight current word
                    self.root.after(0, self.highlight_word)
                    
                    # Wait for next word
                    if self.current_index < len(self.alignments) - 1:
                        duration = self.alignments[self.current_index + 1]['start'] - self.alignments[self.current_index]['start']
                    else:
                        duration = self.alignments[self.current_index]['end'] - self.alignments[self.current_index]['start']
                    
                    # Update progress
                    progress = (self.current_index / len(self.alignments)) * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    
                    time.sleep(max(0.05, duration))
                    self.current_index += 1
                
                # Wait for audio to finish
                sd.wait()
                
                self.root.after(0, self.on_play_finished)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, self.on_play_finished)
        
        self.playback_thread = threading.Thread(target=play_loop, daemon=True)
        self.playback_thread.start()
    
    def highlight_word(self):
        """Highlight current word"""
        if self.current_index >= len(self.alignments):
            return
        
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.tag_remove("highlight", "1.0", tk.END)
        
        alignment = self.alignments[self.current_index]
        start = f"1.0 + {alignment['char_start']} chars"
        end = f"1.0 + {alignment['char_end']} chars"
        
        self.text_widget.tag_add("highlight", start, end)
        self.text_widget.tag_config("highlight", background="yellow", foreground="black")
        self.text_widget.see(start)
        self.text_widget.config(state=tk.DISABLED)
    
    def on_play_finished(self):
        """Called when playback finishes"""
        self.is_playing = False
        self.play_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set(100)
        self.status_label.config(text="Finished", fg="green")
        
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.tag_remove("highlight", "1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)
    
    def stop_audio(self):
        """Stop playback"""
        self.stop_flag = True
        self.is_playing = False
        sd.stop()
        
        self.play_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Stopped", fg="orange")
        
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.tag_remove("highlight", "1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = ReadAlongWithAudio(root)
    root.mainloop()
