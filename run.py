import asyncio
import io
import json
import numpy as np
import pyaudio
import subprocess
import threading
import wave
from collections import deque

import torch
import torchaudio
import wenetruntime as wenet
import time

torch.set_num_threads(1)
# call the chcp command using the Windows Command Prompt
subprocess.call("chcp 936", shell=True)

class SileroVAD:
    def __init__(self):
        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad"
        )

    def detect(self, audio_chunk):
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = self.int2float(audio_int16)
        new_confidence = self.vad_model(torch.from_numpy(audio_float32), 16000).item()
        return new_confidence

    def int2float(self, sound):
        abs_max = np.abs(sound).max()
        sound = sound.astype('float32')
        if abs_max > 0:
            sound *= 1 / abs_max
        sound = sound.squeeze()
        return sound

class Recorder:
    def __init__(self,):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        ) 

    def _save_wav(self, audio_data):    
        # Save audio frames to WAV file
        waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        waveFile.setnchannels(CHANNELS)
        waveFile.setsampwidth(self.audio.get_sample_size(FORMAT))
        waveFile.setframerate(SAMPLE_RATE)
        waveFile.writeframes(b''.join(audio_data))
        waveFile.close()

    def record_audio_raw(self, vad, decoder):
        threshold_window_size = int(SAMPLE_RATE / CHUNK * 1.5) # 2 seconds pre window
        threshold_counter = 0
        threshold_enabled = False
        
        print("Recording Started...", flush=True)
        audio_data = []
        for i in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
            audio_chunk = self.stream.read(CHUNK)

            new_confidence = vad.detect(audio_chunk)
            if new_confidence >= VAD_THRESHOLD:
                audio_data.append(audio_chunk)
                threshold_counter += 1
                if threshold_counter >= threshold_window_size:
                    self._save_wav(audio_data) #insert here 
                    decoder.process_audio(audio_data)
                    audio_data = []
                    threshold_counter = 0
                    break
            else:
                threshold_counter = 0

        # Close audio stream and PyAudio object
        print("Stopped the recording", flush=True)

    def record_audio(self, vad, decoder):
        threshold_window_size = int(SAMPLE_RATE / CHUNK * 2) # 2 seconds pre window
        threshold_counter = 0
        threshold_enabled = False
        
        print("Recording Started...", flush=True)
        audio_data = []
        for i in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
            audio_chunk = self.stream.read(CHUNK)

            new_confidence = vad.detect(audio_chunk)
            if new_confidence >= VAD_THRESHOLD:
                audio_data.append(audio_chunk)
                threshold_counter += 1
                if threshold_counter >= threshold_window_size:
                    decoder.process_audio(audio_data)
                    audio_data = []
                    threshold_counter = 0
                    break
            else:
                threshold_counter = 0

        # Close audio stream and PyAudio object
        print("Stopped the recording", flush=True)

class WeNetASR:
    def __init__(self):
        self.decoder = wenet.Decoder(lang='chs', nbest=1)
        log_file = open("log.txt", "w", encoding='utf-8')
        log_file.close()


    def process_audio(self, audio_data):
        self._save_wav(audio_data)
        decoder = wenet.Decoder(lang='chs')
        ans = decoder.decode_wav(WAVE_OUTPUT_FILENAME)
        try:
            ans = json.loads(ans)
            for x in ans['nbest']:
                print(x['sentence'], flush=True)
                log_file.write(x['sentence'])
        except:
            pass
        log_file.close()  # close the log file when the processing is finished
            
    def process_audio_streaming(self, audio_data):
        print("Processing...", flush=True)
        log_file = open("log.txt", "a", encoding='utf-8')                 
        # process the audio data here
        for i, chunk_wav in enumerate(audio_data):
            last = False if i < len(audio_data) else True
            ans = self.decoder.decode(chunk_wav, last)
            try:
                ans = json.loads(ans)
                for x in ans['nbest']:
                    print(x['sentence'], flush=True)
                    log_file.write(x['sentence'])
            except:
                pass
        log_file.close()  # close the log file when the processing is finished
            
if __name__ == "__main__":

    # Set parameters for audio recording
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    SAMPLE_RATE = 16000
    CHUNK = 1024 # int(SAMPLE_RATE / 10)
    RECORD_SECONDS = 30
    WAVE_OUTPUT_FILENAME = "whisper.wav"
    VAD_THRESHOLD = 0.8

    vad = SileroVAD()
    recorder = Recorder()
    decoder = WeNetASR()

    try:
        while True:
           recorder.record_audio(vad, decoder)

    except KeyboardInterrupt:
        # Close the audio stream and PyAudio object
        recorder.stream.stop_stream()
        recorder.stream.close()
        recorder.audio.terminate()

