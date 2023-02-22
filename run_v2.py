import asyncio
import subprocess
from collections import deque
import io
import json
import numpy as np
import pyaudio
import wave
import torch
import torchaudio
import wenetruntime as wenet

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

async def record_audio(audio_queue, vad):
    #threshold_window_size = int(SAMPLE_RATE / CHUNK * 0.5) # 2 seconds pre window
    #threshold_counter = 0
    #threshold_enabled = False
    
    print("Recording Started...", flush=True)
    while True: 
        audio_data = []
        for i in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
            audio_chunk = stream.read(CHUNK)

            new_confidence = vad.detect(audio_chunk)
            if new_confidence >= VAD_THRESHOLD:
                audio_data.append(audio_chunk)
                #if not threshold_enabled:
                #    print("Voice detected", flush=True)
                #threshold_enabled = True
                #threshold_counter = 0
            else: # no voice detected
                #threshold_enabled = False
                #threshold_counter += 1  # silent counter +1
                audio_data.append(audio_chunk)
                break
        if len(audio_data):
            await audio_queue.put(audio_data)
        await asyncio.sleep(0.01)

async def process_audio(audio_queue):
    log_file = open("log.txt", "a", encoding='utf-8') 
    while True: 
        while audio_queue.empty():
            await asyncio.sleep(0.5)
                
        data = await audio_queue.get()

        # process the audio data here
        for i, chunk_wav in enumerate(data):
            last = False if i < len(data) else True
            ans = decoder.decode(chunk_wav, last)

            try:
                ans = json.loads(ans)
                for x in ans['nbest']:
                    print(x['sentence'], flush=True)
                    log_file.write(x['sentence'])
            except:
                pass
        audio_queue.task_done()

    log_file.close()  # close the log file when the processing is finished
            
if __name__ == "__main__":

    # Set parameters for audio recording
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    SAMPLE_RATE = 16000
    CHUNK = 1024 # int(SAMPLE_RATE / 10)
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "whisper.wav"
    VAD_THRESHOLD = 0.8

    print("run_v2 wenet + vad")
    try:    
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        vad = SileroVAD()
        decoder = wenet.Decoder(lang='chs', nbest=1)
        audio_queue = asyncio.Queue(maxsize=5)
        loop = asyncio.get_event_loop()

        tasks = [
            loop.create_task(record_audio(audio_queue, vad)),
            loop.create_task(process_audio(audio_queue)),
        ]

        loop.run_until_complete(asyncio.gather(*tasks))

    except KeyboardInterrupt:
        # Close the audio stream and PyAudio object
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("Stopped the recording", flush=True)
