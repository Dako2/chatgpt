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
conda install pytorch=1.10.0 torchvision torchau3edsr34e4r5tfdrt43=-41 
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
import multiprocessing as mp

from _vad import SileroVAD
from _gpt import ChatGpt
from _tts import VitsWrapper
import logging


#logging.disable(logging.CRITICAL)
logger = logging.getLogger('gpt')
logger.propagate = False
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('gpt.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# call the chcp command using the Windows Command Prompt 中文显示
subprocess.call("chcp 936", shell=True)

torch.set_num_threads(1)

# Set parameters for ASR 
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = 1024
RECORD_SECONDS = 30 
SAVE_WAV_FILE = True
VAD_THRESHOLD = 0.4
NO_VOICE_WINDOW_THREHOLD = 30 #CHUNKS

class WenetGpt:
    def __init__(self, Enable_ChatGPT = False, Enable_TTS = False): 

        self.vad = SileroVAD()
        self.decoder = wenet.Decoder(lang='chs', nbest=1)
        self.enable_tts = Enable_TTS

        self.audio_queue = queue.Queue(maxsize=100) #thread queue
        self.prompt_queue = queue.Queue(maxsize=5) #thread queue
        #self.tts_queue = queue.Queue(maxsize=3) #thread queue

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        time.sleep(1)

        self.chatgpt = ChatGpt(api_key = API_KEY, enable_chatgpt = Enable_ChatGPT)
        if Enable_TTS:
            self.tts = VitsWrapper()   
        self.start() #start

    def start(self) -> None:
        self.lock = threading.Lock() 

        self.terminate_event = threading.Event()
        self.record_thread  = threading.Thread(target=self.record_audio)
        self.process_thread = threading.Thread(target=self.process_audio) #producer
        self.prompt_thread  = threading.Thread(target=self.prompt_gpt) #consumer

        self.record_thread.start()
        sys.stdout.write("Recording Started...\n\n")
        sys.stdout.flush()
        self.process_thread.start()
        self.prompt_thread.start()
        
        while not self.terminate_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                sys.stdout.write("Interrupt received, stopping threads...")
                sys.stdout.flush()
                self.terminate()
        
    def terminate(self) -> None:
        self.terminate_event.set()
        # Wait for all threads to terminate
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        self.record_thread.join()
        self.process_thread.join()
        self.prompt_thread.join()
 
        sys.stdout.write("Successful exit...")
        sys.stdout.flush()
        
    def record_audio(self) -> None:
        threshold_enabled = False
        last = False
        complete = False

        while not self.terminate_event.is_set():            
            self.lock.acquire()
            audio_chunk = self.stream.read(CHUNK)
            new_confidence = self.vad.detect(audio_chunk)
            self.lock.release()

            if new_confidence >= VAD_THRESHOLD: #voice detected
                threshold_enabled = True
                last = False
                complete = False
                self.audio_queue.put((audio_chunk, last, complete))
                #time.sleep(0.01)
            else: # no voice detected
                if threshold_enabled: #voice detected in prev. chunk
                    threshold_enabled = False
                    complete = False
                    last = True #this is the last chunk or maybe a pause
                    self.audio_queue.put((audio_chunk, last, complete))
                    #ime.sleep(0.01)
                if self.vad.no_voice_counter > NO_VOICE_WINDOW_THREHOLD: #no voice for 3 seconds => complete sentence
                    complete = True
                    self.audio_queue.put((audio_chunk, last, complete))  
                    complete = False
                    last = False

    def process_audio(self):
        tmp_string = "" 
        while not self.terminate_event.is_set():
            try:
                chunk_wav, last, complete = self.audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            # process the audio data here
            if not complete:
                ans = self.decoder.decode(chunk_wav, last)
                if len(ans) < 5: #just no nbest, sentence ...
                    continue
                try:
                    ans = json.loads(ans)
                    ans_string = ans['nbest'][0]['sentence']
                    if len(ans_string):
                        if ans['type'] == 'final_result':
                            sys.stdout.write('\r')
                            sys.stdout.flush()
                            sys.stdout.write("You:     " + ans_string + '.\n')
                            sys.stdout.flush()
                            tmp_string = tmp_string + ans_string + "." #punctuation
                            logger.info("You:     " + ans_string)
                            continue
                        else: 
                            sys.stdout.write('\r')
                            sys.stdout.flush()
                            sys.stdout.write("You:     " + ans_string + '.')
                            sys.stdout.flush() 
                except:
                    sys.stdout.write("Error: Json format", flush = True)
                    sys.stdout.flush()
                    continue
            else:
                # send the text to prompt for gpt inference
                if tmp_string:
                    self.prompt_queue.put(tmp_string)
                    tmp_string = ""

            #self.audio_queue.task_done()

    def prompt_gpt(self):
        #call chatgpt
        while not self.terminate_event.is_set():
            try:
                prompt = self.prompt_queue.get(timeout=1)
            except queue.Empty:
                continue

            # Perform ChatGPT inference on the prompt
            response = self.chatgpt.chatgpt_api(prompt, role = role)
            sys.stdout.write("openai:  " + "\033[91m" + response + "\033[0m" + "\n\n")
            sys.stdout.flush()
            logger.info("openai:  " + response)

            if self.enable_tts:
                if len(response.strip()):
                    self.lock.acquire()
                    self.tts.generate_audio_fast(response)
                    self.lock.release()

            self.prompt_queue.task_done()

"""
def try_multiprocess_but_torchmodel_cannot_serialize():
    pass

    vits = VitsWrapper()
    tts_queue = mp.Queue()
    tts_process = mp.Process(target=tts_output, args=(tts_queue, vits,))
    tts_process.start()
    tts_process.join()
"""
if __name__ == "__main__":
    # Enable_ChatGPT can cost money
    API_KEY = "sk-..."
    role = "You are a helpful assistant replying only Chinese."
    we = WenetGpt(Enable_ChatGPT = True, Enable_TTS = True)
