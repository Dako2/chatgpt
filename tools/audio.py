"""
author: chat-gpt.py

"""

import pyaudio
import wave

# Set parameters for audio recording
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280
RECORD_SECONDS = 10
WAVE_OUTPUT_FILENAME = "recording.pcm"

def record():
    # Initialize PyAudio object
    audio = pyaudio.PyAudio()

    # Open audio stream for recording
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    print("Recording audio...")

    # Create empty list to store audio frames
    frames = []

    # Record audio for specified duration
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Finished recording audio.")

    # Close audio stream and PyAudio object
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save audio frames to WAV file
    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()

def play(filename = 'recording.pcm'):

    # Open the PCM file for reading
    with wave.open(filename, 'rb') as file:
        # Initialize the PyAudio library
        p = pyaudio.PyAudio()

        # Open a new PyAudio stream
        stream = p.open(format=p.get_format_from_width(file.getsampwidth()),
                        channels=file.getnchannels(),
                        rate=file.getframerate(),
                        output=True)

        # Read data from the PCM file and play it using the PyAudio stream
        data = file.readframes(1024)
        while data:
            stream.write(data)
            data = file.readframes(1024)

        # Clean up the PyAudio stream and library
        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    record()
    play()