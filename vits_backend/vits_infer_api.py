import os
import numpy as np
import stat

import torch
import utils

from scipy.io import wavfile
from text.symbols import symbols
from text import cleaned_text_to_sequence
from vits_pinyin import VITS_PinYin
from playsound import playsound
import time
import sounddevice as sd

def save_wav(wav, path, rate):
    wav *= 32767 / max(0.01, np.max(np.abs(wav))) * 0.6
    wavfile.write(path, rate, wav.astype(np.int16))
    print(f"write the file {path}")
    return

class VitsInfer:
    def __init__(self,):    
        # device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        file_path = os.path.abspath(__file__)
        self.module_dir = os.path.dirname(file_path)

        # pinyin
        self.tts_front = VITS_PinYin(self.module_dir+'/bert', self.device)

        # config
        self.hps = utils.get_hparams_from_file(self.module_dir+"/configs/bert_vits.json")
        # hps = utils.get_hparams_from_file(args.config)

        # model
        self.net_g = utils.load_class(self.hps.train.eval_class)(
            len(symbols),
            self.hps.data.filter_length // 2 + 1,
            self.hps.train.segment_size // self.hps.data.hop_length,
            **self.hps.model)

        utils.load_model(self.module_dir+'/vits_bert_model.pth', self.net_g)
        self.net_g.eval()
        self.net_g.to(self.device)

        os.makedirs(self.module_dir+"/vits_infer_out/", exist_ok=True)
        os.chmod(self.module_dir+"/vits_infer_out/", stat.S_IWUSR)

        print("VITS initialized...")

    def generate_audio(self, item):
        phonemes, char_embeds = self.tts_front.chinese_to_phonemes(item)
        input_ids = cleaned_text_to_sequence(phonemes)
        with torch.no_grad():
            x_tst = torch.LongTensor(input_ids).unsqueeze(0).to(self.device)
            x_tst_lengths = torch.LongTensor([len(input_ids)]).to(self.device)
            x_tst_prosody = torch.FloatTensor(char_embeds).unsqueeze(0).to(self.device)
            audio = self.net_g.infer(x_tst, x_tst_lengths, x_tst_prosody, noise_scale=0.5,
                                length_scale=1)[0][0, 0].data.cpu().float().numpy()
            #save_wav(audio, self.module_dir + "/vits_infer_out/bert_vits.wav", self.hps.data.sampling_rate)
            audio_path = self.module_dir + "/vits_infer_out/bert_vits.wav"
            save_wav(audio, audio_path, self.hps.data.sampling_rate)
            #playsound(audio_path)
            return audio_path

    def generate_audio_v1(self, text_item):
        text, filename = text_item
        phonemes, char_embeds = self.tts_front.chinese_to_phonemes(text)
        input_ids = cleaned_text_to_sequence(phonemes)
        with torch.no_grad():
            x_tst = torch.LongTensor(input_ids).unsqueeze(0).to(self.device)
            x_tst_lengths = torch.LongTensor([len(input_ids)]).to(self.device)
            x_tst_prosody = torch.FloatTensor(char_embeds).unsqueeze(0).to(self.device)
            audio = self.net_g.infer(x_tst, x_tst_lengths, x_tst_prosody, noise_scale=0.5,
                                length_scale=1)[0][0, 0].data.cpu().float().numpy()
            audio_path = self.module_dir + "/vits_infer_out/" + filename
            save_wav(audio, audio_path, self.hps.data.sampling_rate)
            #playsound(audio_path)
            return audio_path
       
    def generate_audio_v2(self, text_item):
        text, filename = text_item
        phonemes, char_embeds = self.tts_front.chinese_to_phonemes(text)
        input_ids = cleaned_text_to_sequence(phonemes)
        with torch.no_grad():
            x_tst = torch.LongTensor(input_ids).unsqueeze(0).to(self.device)
            x_tst_lengths = torch.LongTensor([len(input_ids)]).to(self.device)
            x_tst_prosody = torch.FloatTensor(char_embeds).unsqueeze(0).to(self.device)
            audio = self.net_g.infer(x_tst, x_tst_lengths, x_tst_prosody, noise_scale=0.5,
                                length_scale=1)[0][0, 0].data.cpu().float().numpy()
            audio = audio / np.max(np.abs(audio))
            # play the audio using sounddevice
            return audio
               
if __name__ == "__main__": 
    prompt = "我是人工智能语音助手。我很强我知道！"
    t0 = time.time()
    vits = VitsInfer()
    t1 = time.time()
    vits.generate_audio(prompt)
 