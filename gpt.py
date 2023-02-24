"""
GPT-3.5 API is not open yet; Current available models include text-curie-001, text-davinci-002, text-davinci-003, davinci-codex
"""

import os
import openai 

API_KEY = "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"

class ChatGpt:
    def __init__(self, api_key = API_KEY, enable_chatgpt = False,):
        self.enable_chatgpt = enable_chatgpt #enable cost money
        openai.api_key = api_key
        self.engine_id = "text-davinci-003" #text-curie-001, text-davinci-002, text-davinci-003, davinci-codex

    def chatgpt_api(self, prompt):

        if not self.enable_chatgpt:
            print("openai:  " + "\033[91m" + "... no response / api diabled" + "\033[0m\n\n", flush = True)
            return ""

        try:
            response = openai.Completion.create(
                engine=self.engine_id,
                prompt=prompt,
                max_tokens=100,
                n=1,
                stop=None,
                temperature=0.7,
            )
            self.output(prompt, response)       
            return response.choices[0].text.strip()
        except openai.error.RateLimitError:
            self.enable_chatgpt = False
            print("Error: API limit exceeded. Please wait and try again later.")
            #sys.exit(1)
            return ""

    def output(self, prompt, response):
        print("openai:  " + "\033[91m" + response.choices[0].text.strip() + "\033[0m" + "\n\n", flush = True)

if __name__ == "__main__":
    gpt = ChatGpt()
    gpt.chatgpt_api("how's going")