""" 02/23/2023 - WenetGPT
Reference:
https://github.com/wenet-e2e/wenet
https://github.com/openai/openai-openapi
https://github.com/snakers4/silero-vad

GPT-3.5 API is not open yet; Current available models include text-curie-001, text-davinci-002, text-davinci-003, davinci-codex

Setup:
Environment Windows (Full-Duplex Microphone and Speaker)
git clone https://github.com/wenet-e2e/wenet.git
conda create -n wenet python=3.8
conda activate wenet
pip install -r requirements.txt
conda install pytorch=1.10.0 torchvision torchaudio=0.10.0 cudatoolkit=11.1 -c pytorch -c conda-forge

"""

import queue
import threading
import time
import sys
import json

import torch
import numpy as np
import wenetruntime as wenet
import pyaudio
import subprocess

from gpt import ChatGpt

torch.set_num_threads(1)

# call the chcp command using the Windows Command Prompt 中文显示
subprocess.call("chcp 936", shell=True)


# Set parameters for audio recording
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)
RECORD_SECONDS = 30 
SAVE_WAV_FILE = True
WAVE_OUTPUT_FILENAME = "whisper.wav"
VAD_THRESHOLD = 0.4
PRE_WINDOW_THREHOLD = 7 #CHUNKS

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

class WenetAsr:
    def __init__(self, Enable_ChatGPT = True): 
        self.vad = SileroVAD()
        self.decoder = wenet.Decoder(lang='chs', nbest=1)
        self.audio_queue = queue.Queue(maxsize=100)
        self.log_file = open("log.txt", "a", encoding='utf-8')        
        self.prompt_queue = queue.Queue(maxsize=5)

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        self.chatgpt = ChatGpt(enable_chatgpt = Enable_ChatGPT)

        time.sleep(1.7)
        print("Recording Started...\n\n")


    def start(self):
        self.terminate_event = threading.Event()
        record_thread = threading.Thread(target=self.record_audio)
        process_thread = threading.Thread(target=self.process_audio)
        prompt_thread = threading.Thread(target=self.prompt_thread)

        record_thread.start()
        process_thread.start()
        prompt_thread.start()

        while not self.terminate_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("Interrupt received, stopping threads...")
                self.terminate()
    def terminate(self):
        self.terminate_event.set()

        # Wait for all threads to terminate
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        self.log_file.close()

        self.prompt_queue.join()
        self.audio_queue.join()
        
        print("Threads stopped, exiting...")


    def record_audio(self):
        threshold_enabled = False
        last = False
        while not self.terminate_event.is_set():
            audio_chunk = self.stream.read(CHUNK)
            new_confidence = self.vad.detect(audio_chunk)

            if new_confidence >= VAD_THRESHOLD: #voice detected
                threshold_enabled = True
                last = False
                self.audio_queue.put((audio_chunk, last))
                time.sleep(0.01)
            else: # no voice detected
                if threshold_enabled:
                    threshold_enabled = False
                    last = True
                    self.audio_queue.put((audio_chunk, last))
                    time.sleep(0.01)

    def process_audio(self):
        while not self.terminate_event.is_set():
            try:
                chunk_wav, last = self.audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            # process the audio data here
            ans = self.decoder.decode(chunk_wav, last)
            try:
                ans = json.loads(ans)
                if len(ans['nbest'][0]['sentence']):
                    if ans['type'] == 'final_result':
                        sys.stdout.write('\r')
                        sys.stdout.flush()
                        sys.stdout.write("You:     " + ans['nbest'][0]['sentence'] + '.\n')
                        sys.stdout.flush()
                        self.log_file.write(ans['nbest'][0]['sentence'] + '.\n')
                        self.prompt_queue.put(ans['nbest'][0]['sentence'])

                    else: 
                        sys.stdout.write('\r')
                        sys.stdout.flush()
                        sys.stdout.write("You:     " + ans['nbest'][0]['sentence'] + '.')
                        sys.stdout.flush() 
            except:
                pass

            self.audio_queue.task_done()

    def prompt_thread(self):
        prompt0 = ""
        while not self.terminate_event.is_set():
            try:
                prompt = self.prompt_queue.get(timeout=1)
                #prompt = await asyncio.wait_for(prompt_queue.get(), timeout=1)
            except queue.Empty:
                continue
            # Perform ChatGPT inference on the prompt
            response = self.chatgpt.chatgpt_api(prompt)
            self.log_file.write('openai:' + response + '.\n')
            self.prompt_queue.task_done()
                 
if __name__ == "__main__":

    # Enable_ChatGPT cost money

    we = WenetAsr(Enable_ChatGPT = False)
    we.start()
