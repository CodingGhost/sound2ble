import numpy as np
import librosa
import sounddevice as sd
import queue
import threading
import logging
import time
import asyncio
from madmom.features.beats import DBNBeatTrackingProcessor, RNNBeatProcessor
from madmom.processors import IOProcessor, process_online

# ✅ Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] (%(threadName)s) - %(message)s",
    level=logging.INFO
)

# Separate loggers for different parts
log_general = logging.getLogger("BeatDetector")
log_audio = logging.getLogger("AudioProcessing")
log_madmom = logging.getLogger("MadmomProcessor")
log_classification = logging.getLogger("BeatClassification")

class BeatDetector:
    def __init__(self, callback=None, loop=None):
        """
        Initializes the Beat Detector with Madmom and Librosa-based processing.
        :param callback: Function to be called when a beat is detected.
        """
        # Parameters
        self.sampleRate = 44100  # Sampling rate
        self.buffer_size = 2048  # FFT window size
        self.hop_length = 512  # Hop length for STFT
        self.buffer_duration = 3  # Length of audio buffer in seconds
        self.loop = loop
        # Hysteresis thresholds
        self.beat_threshold_high = 4.5  # Switch to beats (based on empirical values)
        self.beat_threshold_low = 3.0   # Switch to melody

        # Beat Tracking Configuration
        self.kwargs = dict(
            fps=100,
            correct=True,
            infile=None,
            outfile=None,
            max_bpm=200,
            min_bpm=100,
            num_frames=1,
            online=True,
        )

        self.onset_history = []
        self.audio_queue = queue.Queue()
        self.callback = callback
        self.running = False
        self.classification_state = "beats"
        self.stable_frames = 0
        self.last_update_time = time.time()
        self.avgOnset = 0

        # Initialize Madmom processors
        self.in_processor = RNNBeatProcessor(**self.kwargs)
        self.beat_processor = DBNBeatTrackingProcessor(**self.kwargs)
        self.out_processor = [self.beat_processor, self.beat_callback]
        self.processor = IOProcessor(self.in_processor, self.out_processor)

        # Audio stream setup
        self.stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=self.sampleRate, blocksize=self.buffer_size)

        # Threads
        self.madmomThread = None
        self.beatClassifyThread = None

    def audio_callback(self, indata, frames, time, status):
        """Receives audio data and places it in the queue for processing."""
        if status:
            log_audio.warning(f"Audio stream error: {status}")
        self.audio_queue.put(indata[:, 0].copy())
        log_audio.debug("Audio data received and added to queue.")

    def beat_callback(self, beats, output=None):
        """Callback function when a beat is detected by Madmom."""
        if len(beats) > 0:
            log_madmom.info(f"Detected Beats: {beats} (Onset Strength: {self.avgOnset:.2f})")
            if self.classification_state == "beats" and self.callback:
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self.callback(), self.loop)  # Send event to asyncio
                else:
                    self.callback()

        if not self.running:
            log_madmom.warning("Beat detection stopped unexpectedly.")
            exit()

    def process_audio(self):
        """Processes the audio data in a separate thread for classification."""
        audio_buffer = np.zeros(self.buffer_duration * self.sampleRate)

        with self.stream:
            while self.running:
                if not self.audio_queue.empty():
                    new_data = self.audio_queue.get()
                    audio_buffer = np.roll(audio_buffer, -len(new_data))
                    audio_buffer[-len(new_data):] = new_data

                    # Compute onset strength
                    onset_env = librosa.onset.onset_strength(y=audio_buffer, sr=self.sampleRate, hop_length=self.hop_length)
                    peaks = librosa.util.peak_pick(onset_env, pre_max=10, post_max=10, pre_avg=5, post_avg=5, delta=0.7, wait=10)
                        
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
                                log_classification.info("Switched to BEATS")

                        elif self.classification_state == "beats" and (self.avgOnset < self.beat_threshold_low or len(peaks) < self.buffer_duration * 3):
                            self.stable_frames += 1
                            if self.stable_frames > 3 and (current_time - self.last_update_time) > self.buffer_duration:
                                self.classification_state = "melody"
                                self.stable_frames = 0
                                self.last_update_time = current_time
                                log_classification.info("Switched to MELODY")
                        else:
                            self.stable_frames = 0  # Reset stability counter

    def run(self, useBeatClassification=True):
        """Starts the beat detection process."""
        if not self.running:
            self.running = True
            self.madmomThread = threading.Thread(target=process_online, args=(self.processor,), kwargs=self.kwargs, daemon=True)
            self.beatClassifyThread = threading.Thread(target=self.process_audio, daemon=True)

            self.madmomThread.start()
            log_general.info("Madmom beat detection thread started.")

            if useBeatClassification:
                self.beatClassifyThread.start()
                log_general.info("Beat classification thread started.")

    def stop(self):
        """Stops the beat detection process gracefully."""
        self.running = False
        log_general.info("Stopping BeatDetector...")

        if self.madmomThread:
            self.madmomThread.join()
            log_general.info("Madmom thread stopped.")

        if self.beatClassifyThread:
            self.beatClassifyThread.join()
            log_general.info("Beat classification thread stopped.")

        log_general.info("BeatDetector fully stopped.")


# Example usage if run directly
if __name__ == "__main__":
    import sys

    def beat_callback():
        log_general.info("🔴 Beat detected!")

    detector = BeatDetector(callback=beat_callback)
    detector.run()

    try:
        while True:
            time.sleep(1)  # Keep main thread alive while detector runs
    except KeyboardInterrupt:
        log_general.info("KeyboardInterrupt received, stopping BeatDetector...")
        detector.stop()
        sys.exit(0)
