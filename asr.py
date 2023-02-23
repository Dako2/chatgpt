import asyncio
import subprocess
import queue
from collections import deque
import io
import json
import numpy as np
import pyaudio
import wave
import torch
import torchaudio
import wenetruntime as wenet
import time
import sys

torch.set_num_threads(1)

# call the chcp command using the Windows Command Prompt
subprocess.call("chcp 936", shell=True)
# Set parameters for audio recording
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)
RECORD_SECONDS = 5
SAVE_WAV_FILE = True
WAVE_OUTPUT_FILENAME = "whisper.wav"
VAD_THRESHOLD = 0.6
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

    def __init__(self,):
        print("run_v2 wenet + vad")

        self.vad = SileroVAD()
        self.decoder = wenet.Decoder(lang='chs', nbest=1)
        self.audio_queue = asyncio.Queue(maxsize=100)
        self.sliding_window = asyncio.Queue(maxsize=5)
        
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        time.sleep(1.7)
        print("Recording Started...")
        self.log_file = open("log.txt", "a", encoding='utf-8')        

    def start(self):
        try:
            loop = asyncio.get_event_loop()

            tasks = [
                loop.create_task(self.record_audio(self.audio_queue, self.vad)),
                loop.create_task(self.process_audio(self.audio_queue)),
            ]

            loop.run_until_complete(asyncio.gather(*tasks))

        except KeyboardInterrupt:
            self.terminate()

    def terminate(self):
        self.log_file.close()  # close the log file when the processing is finished
        # Close the audio stream and PyAudio object
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        print("Stopped the recording", flush=True)  


    async def record_audio(self, audio_queue, vad):
        
        threshold_enabled = False
        last = False
        while True: 
            audio_chunk = self.stream.read(CHUNK)
            new_confidence = self.vad.detect(audio_chunk)

            if new_confidence >= VAD_THRESHOLD: #voice detected
                #if not threshold_enabled:
                #   print("voice detected", flush = True)

                threshold_enabled = True
                last = False
                await self.audio_queue.put((audio_chunk, last))
                #print(len(audio_chunk), last, flush = True)
                await asyncio.sleep(0.01)
            else: # no voice detected
                if threshold_enabled:
                    threshold_enabled = False
                    last = True
                    await self.audio_queue.put((audio_chunk, last))
                    #print(len(audio_chunk), last, flush = True)
                    await asyncio.sleep(0.01)

    async def process_audio(self, audio_queue):
        
        while True: 
            while self.audio_queue.empty():
                await asyncio.sleep(0.5)
            #chunk_wav, last = await audio_queue.get()
            chunk_wav, last = self.audio_queue.get_nowait()

            # process the audio data here
            ans = self.decoder.decode(chunk_wav, last)
            try:
                #print(ans, flush = True)
                ans = json.loads(ans)
                if len(ans['nbest'][0]['sentence']):
                    if ans['type'] == 'final_result':
                        sys.stdout.write('\r')
                        sys.stdout.flush()
                        sys.stdout.write(ans['nbest'][0]['sentence'] + '.\n')
                        sys.stdout.flush()
                        self.log_file.write(ans['nbest'][0]['sentence'] + '.\n')
                    else:
                        sys.stdout.write('\r')
                        sys.stdout.flush()
                        sys.stdout.write(ans['nbest'][0]['sentence'])
                        sys.stdout.flush()        
            except:
                pass

            self.audio_queue.task_done()


if __name__ == "__main__":
    we = WenetAsr()
    we.start()