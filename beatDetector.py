import numpy as np
import librosa
import librosa.display
import sounddevice as sd
import matplotlib.pyplot as plt
import queue
import threading
from madmom.features.beats import DBNBeatTrackingProcessor, RNNBeatProcessor
from madmom.processors import IOProcessor, process_online
import time


class BeatDetector:
    def __init__(self, callback=None):
        # Parameters
        self.sampleRate = 44100  # Sampling rate
        self.buffer_size = 2048  # FFT window size
        self.hop_length = 512  # Hop length for STFT
        self.buffer_duration = 3  # Length of audio buffer in seconds

        # Hysteresis thresholds (raw values)
        self.beat_threshold_high = 4.5  # Switch to beats (based on empirical values)
        self.beat_threshold_low = 3.0   # Switch to melody

        # Beat Tracking Configuration
        self.kwargs = dict(
            fps = 100,
            correct = True,
            infile = None,
            outfile = None,
            max_bpm = 200,
            min_bpm = 100,
            num_frames = 1,
            online = True,
        )
        self.onset_history = []
        self.audio_queue = queue.Queue()
        self.last_update_time = time.time()
        self.callback = callback
        self.in_processor = RNNBeatProcessor(**self.kwargs)
        self.beat_processor = DBNBeatTrackingProcessor(**self.kwargs)
        self.out_processor = [self.beat_processor, self.beat_callback]
        self.processor = IOProcessor(self.in_processor, self.out_processor)
        #variables
        self.callback = callback  # Function to call when a beat is detected
        self.audio_queue = queue.Queue()
        self.running = False
        self.madmomThread = None
        self.beatClassifyThread = None
        self.classification_state = "beats"
        self.stable_frames = 0
        self.last_update_time = time.time()
        self.onset_history = []
        self.avgOnset = 0
        self.stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=self.sampleRate, blocksize=self.buffer_size)

    def audio_callback(self, indata, frames, time, status):
        self.audio_queue.put(indata[:, 0].copy())

    def beat_callback(self,beats, output=None):
        if len(beats) > 0:
            if self.classification_state == "beats":
                self.callback()
                print(f"Detected Beats: {beats} (Onset Strength: {self.avgOnset:.2f})")
        if not self.running:
            exit()

    def process_audio(self):
        """Processes the audio data in a separate thread."""
        audio_buffer = np.zeros(self.buffer_duration * self.sampleRate)

        with self.stream:
            while self.running:
                if not self.audio_queue.empty():
                    new_data = self.audio_queue.get()
                    audio_buffer = np.roll(audio_buffer, -len(new_data))
                    audio_buffer[-len(new_data):] = new_data

                    # Compute onset strength (raw values)
                    onset_env = librosa.onset.onset_strength(y=audio_buffer, sr=self.sampleRate, hop_length=self.hop_length)
                    peaks = librosa.util.peak_pick(
                        onset_env, pre_max=10, post_max=10, pre_avg=5, post_avg=5, delta=0.7, wait=10
                    )
                    if len(peaks) > 0:
                        self.avgOnset = onset_env[peaks].mean()
                        self.onset_history.append(self.avgOnset)

                        # Keep only the latest 100 values
                        if len(self.onset_history) > 100:
                            self.onset_history.pop(0)

                        current_time = time.time()
                        # Beat detection with hysteresis
                        if self.classification_state == "melody" and self.avgOnset > self.beat_threshold_high:
                            self.stable_frames += 1
                            if self.stable_frames > 3 and (current_time - self.last_update_time) > self.buffer_duration:
                                self.classification_state = "beats"
                                self.stable_frames = 0
                                self.last_update_time = current_time
                                print("Switched to BEATS")

                        elif self.classification_state == "beats" and (self.avgOnset < self.beat_threshold_low or len(peaks) < self.buffer_duration * 3):
                            self.stable_frames += 1
                            if self.stable_frames > 3 and (current_time - self.last_update_time) > self.buffer_duration:
                                self.classification_state = "melody"
                                self.stable_frames = 0
                                self.last_update_time = current_time
                                print("Switched to MELODY")
                        else:
                            self.stable_frames = 0  # Reset stability counter


    def run(self,useBeatClassification=True):
        if not self.running:
            self.running = True
            self.madmomThread = threading.Thread(target=process_online, args=(self.processor,), kwargs=self.kwargs)
            self.beatClassifyThread = threading.Thread(target=self.process_audio, daemon=True)
            self.madmomThread.start()
            if(useBeatClassification):
                self.beatClassifyThread.start()
            print("BeatDetector started.")

    def stop(self):
        self.running = False
        if self.madmomThread:
            self.madmomThread.join()
        if self.beatClassifyThread:
            self.beatClassifyThread.join()
        print("BeatDetector stopped.")


# Example usage if run directly
if __name__ == "__main__":
    def beat_callback():
        print("Beat detected!")
    detector = BeatDetector(callback=beat_callback)
    detector.run()

    try:
        while True:
            time.sleep(1)  # Keep main thread alive while detector runs
    except KeyboardInterrupt:
        detector.stop()