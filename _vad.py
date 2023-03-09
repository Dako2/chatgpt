import numpy as np
import torch

class SileroVAD:
    def __init__(self, vad_theshold=0.6):
        state_dict = torch.load('silero_vad.pt') 
        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad"
        )
        # Load the saved state dictionary        
        self.vad_theshold = vad_theshold
        self.no_voice_counter = 0

    def detect(self, audio_chunk):
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = self.int2float(audio_int16)
        new_confidence = self.vad_model(torch.from_numpy(audio_float32), 16000).item()
        if new_confidence < self.vad_theshold:
            self.no_voice_counter += 1
        else:
            #print('voice detected', flush=True)
            self.no_voice_counter = 0
        return new_confidence

    def int2float(self, sound):
        abs_max = np.abs(sound).max()
        sound = sound.astype('float32')
        if abs_max > 0:
            sound *= 1 / abs_max
        sound = sound.squeeze()
        return sound
if __name__ == "__main__":
     # Load the Silero VAD model
    vad_model, _ = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad'
    )

    # Save the model to a file
    torch.save(vad_model.state_dict(), 'silero_vad.pt')


    # Load the saved state dictionary
    state_dict = torch.load('silero_vad.pt')
    # Load the state dictionary into the model
    vad_model.load_state_dict(state_dict)

    vd = SileroVAD()