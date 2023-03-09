import queue
import threading
import time
import sys
import json

import torch
import numpy as np
import wenetruntime as wenet
import pyaudio

from _vad import SileroVAD

import subprocess
# call the chcp command using the Windows Command Prompt 中文显示
subprocess.call("chcp 936", shell=True)

FORMAT         = pyaudio.paInt16
CHANNELS       = 1
SAMPLE_RATE    = 16000
CHUNK          = int(1024)
RECORD_SECONDS = 30
SAVE_WAV_FILE  = True
WAVE_OUTPUT_FILENAME = "record.wav"
VAD_THRESHOLD        = 0.4

NOVOICE_WINDOW_THREHOLD = 1 #CHUNKS

class AudioRecorderThread(threading.Thread):
    def __init__(self, audio_queue, pause_lock):
        super(AudioRecorderThread, self).__init__()
        self.audio_queue = audio_queue
        self.pause_lock = pause_lock
        self.paused = False
        self.terminate_event = threading.Event()

        self.decoder = wenet.Decoder(lang='chs', nbest=1)
        self.vad = SileroVAD(vad_theshold=VAD_THRESHOLD)
 
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

    def run(self):
        voice_detected = False
        last_chunk = False

        while not self.terminate_event.is_set():
            with self.pause_lock:
                if self.paused:
                    self.pause_lock.wait()

            # Your audio recording code here
            audio_chunk    = self.stream.read(CHUNK)
            new_confidence = self.vad.detect(audio_chunk)

            if new_confidence >= VAD_THRESHOLD: #voice detected
                voice_detected = True
                last_chunk = False
                self.audio_queue.put((audio_chunk, last_chunk))
                time.sleep(0.01)
            else: # no voice detected
                if self.vad.no_voice_counter > NOVOICE_WINDOW_THREHOLD:
                    self.vad.no_voice_counter = 0
                    voice_detected = False
                    last_chunk = True
                    self.audio_queue.put((audio_chunk, last_chunk))
                    time.sleep(0.01)
                    break

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        with self.pause_lock:
            self.pause_lock.notify_all()            

    def terminate(self):
        self.terminate_event.set()
        # Wait for all threads to terminate
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

class AudioProcessorThread(threading.Thread):
    def __init__(self, audio_queue, prompt_queue, pause_lock):
        super(AudioProcessorThread, self).__init__()
        self.audio_queue = audio_queue
        self.prompt_queue = prompt_queue
        self.pause_lock = pause_lock
        self.paused = False

    def run(self):
        while True:
            with self.pause_lock:
                if self.paused:
                    self.pause_lock.wait()

                # Your audio processing code here
                audio = self.audio_queue.get()
                prompt = None
                self.prompt_queue.put(prompt)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        with self.pause_lock:
            self.pause_lock.notify_all()


class WenetGpt:
    def __init__(self,):        
        self.decoder = wenet.Decoder(lang='chs', nbest=1)
        self.vad = SileroVAD(vad_theshold=VAD_THRESHOLD)
 
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        self.terminate_event = threading.Event()
        self.record_thread  = threading.Thread(target=self.record_audio)
        self.process_thread = threading.Thread(target=self.process_audio) #producer

        self.start()

    def logging(self, message):
        if not self.log_enable:
            return
        try:
            with open("wenet_log.txt", "a", encoding='utf-8') as logfile:
                logfile.write(message + '\n')
        except:
            print("Error: Logging error")

    def start(self):
        self.record_thread.start()
        self.process_thread.start()
        print("Recording Started...\n\n")

        while not self.terminate_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("Interrupt received, stopping threads...")
                self.terminate()
                break

    def terminate(self):
        # gracefully terminate all events, empty queue, and close audio and stream
        self.terminate_event.set()
 
        self.record_thread.join()
        self.process_thread.join()

        while not self.audio_queue.empty():
            self.audio_queue.get()

        # Wait for all threads to terminate
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        print("Successful exit...")

    def run(self,):
        pass

    def pause(self,):
        self.pause_event.set()

    def resume(self,):
        self.pasue_event.clear()


    def record_audio(self,):
        # if vad detect record audio put queue if not check if over window and put the queue with last chunk
        voice_detected = False
        last_chunk = False
        while not self.terminate_event.is_set():
            audio_chunk = self.stream.read(CHUNK)
            new_confidence = self.vad.detect(audio_chunk)

            if new_confidence >= VAD_THRESHOLD: #voice detected
                voice_detected = True
                last_chunk = False
                self.audio_queue.put((audio_chunk, last_chunk))
                time.sleep(0.001)
            else: # no voice detected
                if self.vad.no_voice_counter > NOVOICE_WINDOW_THREHOLD:
                    self.vad.no_voice_counter = 0
                    voice_detected = False
                    last_chunk = True
                    self.audio_queue.put((audio_chunk, last_chunk))
                    time.sleep(0.001)
                    break

    def process_audio(self):
        while not self.terminate_event.is_set():
            try:
                chunk_wav, last = self.audio_queue.get()
            except queue.Empty:
                time.sleep(0.1)
                continue

            # process the audio data here
            self.tmp = self.decoder.decode(chunk_wav, last)
            print(int(time.time()), len(self.tmp), flush = True)
            try:
                ans = json.loads(ans)
            except:
                print("Error: Json format")
                print(ans, flush = True)
                continue

            if len(ans['nbest'][0]['sentence']):
                if ans['type'] == 'final_result':
                    sys.stdout.write('\r')
                    sys.stdout.flush()
                    sys.stdout.write("You:     " + ans['nbest'][0]['sentence'] + '.\n')
                    sys.stdout.flush()
                    self.logging(ans['nbest'][0]['sentence'])
                    self.prompt_queue.put(ans['nbest'][0]['sentence'])

                else: 
                    sys.stdout.write('\r')
                    sys.stdout.flush()
                    sys.stdout.write("You:     " + ans['nbest'][0]['sentence'] + '.')
                    sys.stdout.flush() 
 
            self.audio_queue.task_done()

if __name__ == "__main__":
    we = WenetGpt()
