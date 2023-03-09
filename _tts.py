"""
pip install playsound==1.2.2
"""

import multiprocessing
import os
from gtts import gTTS
import time
from vits_backend.vits_infer_api import VitsInfer
import queue
import threading
from playsound import playsound
import re 
import sounddevice as sd
import multiprocessing as mp
import queue
import sounddevice as sd
from gtts import gTTS
from io import BytesIO
import numpy as np
import logging
logger = logging.getLogger('gpt')  

class TTS():
    def __init__(self, num_processes=4):
        self.pool = mp.Pool(num_processes)
        self.logger = logger
        self.tts_queue = mp.Manager().Queue()
        self.condition = mp.Value('b', True)

    def start(self):
        self.pool.apply_async(self.tts_output)

    def stop(self):
        self.pool.close()
        self.pool.join()
        self.condition.value = False
        self.tts_queue.put(None)

    def speak(self, text):
        self.tts_queue.put(text)

    def tts_output(self):
        while self.condition.value:
            try:
                text = self.tts_queue.get(timeout=1)
            except queue.Empty:
                continue
            if text is None:
                continue
            tts = gTTS(text=text, lang='en')
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            data, _ = sd.decode(fp.read())
            sd.play(data, blocking=True)
        self.logger.debug("Exiting tts_output loop")

def gtts(my_string, MultiProcessorNums = 4): 
    text_data_list, filenames = parse(my_string)
    t0 = time.time() 
    pool = multiprocessing.Pool(processes=MultiProcessorNums) 
    results = pool.map(tts_worker, text_data_list) 
    pool.close() 
    pool.join() 
    print("dt: %.2f ms"%((time.time() - t0) * 1000))
    play_sound_0(filenames)

def tts_worker(text_data): 
    text, filename = text_data
    tts = gTTS(text=text, lang='zh-tw')
    tts.save(filename)
    return filename

def play_sound_0(filenames):
    # Play the resulting audio files in sequence using playsound
    for filename in filenames:
        playsound(filename)

    # Delete the audio files from disk
    #for filename in filenames:
    #    os.remove(filename)

def play_sound_1(filenames):
    import pygame 
    # Initialize the pygame mixer object
    pygame.mixer.init()

    # Load and play the audio files
    for filename in filenames:
        print(filename)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    # Stop and quit the mixer object
    pygame.mixer.music.stop()
    pygame.mixer.quit()

    # Delete the audio files from disk
    for filename in filenames:
        os.remove(filename)

class VitsWrapper:
    def __init__(self, Enable_TTS = True):
        self.vits = VitsInfer()
        self.enable_tts = Enable_TTS
        self.t0 = time.time()
        self.logger = logger
        
    def generate_audio_slow(self, item):
        if not self.enable_tts:
            self.logger.debug("TTS disabled", flush = True)
            return
        audiopath = self.vits.generate_audio(item)
        self.logger.debug("generate_audio_slow: start playsound")
        playsound(audiopath)

    def generate_audio_thread(self, text_data):
        data_size = len(text_data)
        if not self.enable_tts:
            print("TTS disabled")
            self.audio_queue.put(None)
            self.terminate_event.set()
            return 
        for item, filename in text_data:
            #print("generate", item, filename,'\n')
            tmp = self.vits.generate_audio_v2((item, filename))
            #print(type(tmp))
            #time.sleep(0.1)
            self.audio_queue.put(tmp)
        self.complete = True
        
    def play_sound_x(self):
        while not self.terminate_event.is_set():
            try:
                filename = self.audio_queue.get(timeout=1)
            except queue.Empty:
                time.sleep(1)
                continue
            self.logger.debug("play_sound_x: start")
            playsound(filename)
            if self.complete:
                #self.terminate_event.set()
                return
        
    def play_sound_y(self,):
        while not self.terminate_event.is_set():
            try:
                tmp = self.audio_queue.get(timeout=1)
            except queue.Empty:
                time.sleep(0.1)
                continue
            self.logger.debug("play_sound_y: start")
            if self.complete:
                sd.play(tmp, self.vits.hps.data.sampling_rate)
                sd.wait()
                self.terminate_event.set()
                break
            else:
                sd.play(tmp, self.vits.hps.data.sampling_rate)
                sd.wait()
            
    def generate_audio_fast(self, new_string):
        #new_string = new_string[:2] + "," + new_string[2:] # faster 780ms

        text_data_list, filenames = parse(new_string)
        #print(text_data_list)

        self.audio_queue = queue.Queue()
        self.terminate_event = threading.Event()

        p1 = threading.Thread(target=self.generate_audio_thread, args = (text_data_list,))
        p2 = threading.Thread(target=self.play_sound_y,)

        self.complete = False
        p1.start()
        p2.start()
         # Wait for the termination event to be set before terminating the threads
        self.terminate_event.wait()

        # Signal the termination event to the producer and consumer threads
        #print("task done. terminating", flush = True)
        p1.join()
        p2.join()
        while not self.audio_queue.empty():
            _ = self.audio_queue.get()
        #self.cleanup(filenames)

    def cleanup(self, filenames):
        for filename in filenames:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    self.logger.debug(f"remove {filename}")
                except OSError as e:
                    self.logger.debug(f"Error deleting file: {e}")
            else:
                self.logger.debug("File does not exist")

    def english_to_chinese(self, text):
        return
    
def parse(my_string):
    items = re.split('[^\w]+', my_string)
    while "" in items:
        items.remove("")
    filenames = ["tts2_{}.wav".format(x) for x in range(len(items))]
    text_data_list = list(zip(*[items, filenames]))
    return text_data_list, filenames 
 
if __name__ == "__main__":
    import logging

    logger = logging.getLogger(__name__)  
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('sample.log')
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    my_string = "我是人工智能语音助手。我很强我知道!"

    #vits = VitsWrapper()
    #vits.generate_audio_slow(my_string)
 
    #vits = VitsWrapper()
    #vits.generate_audio_fast(new_string = my_string)
    
    tts = TTS(num_processes=1)
    tts.tts_output(my_string)

    tts.start()

    # add some text to the queue
    texts, _ = parse(my_string) 
    for text in texts:
        tts.speak(text)

    # stop the TTS system
    tts.stop()
 