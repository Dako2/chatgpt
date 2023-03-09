"""
GPT-3.5 API is not open yet; Current available models include text-curie-001, text-davinci-002, text-davinci-003, davinci-codex
"""

import os
import openai 
import time 
import sys

class ChatGpt:
    def __init__(self, api_key, enable_chatgpt = False, engine_id = "gpt-3.5-turbo"):
        self.enable_chatgpt = enable_chatgpt #enable cost money
        openai.api_key = api_key
        self.engine_id = engine_id #text-curie-001, text-davinci-002, text-davinci-003, davinci-codex

    def chatgpt_api(self, prompt, role = "You are a helpful assistant replying only Chinese.", timeout=10):
        if not self.enable_chatgpt:
            #print("openai:  " + "\033[91m" + "Known: API disabled." + "\033[0m\n\n", flush=True)
            #return "API没钱打开"
            return prompt

        start_time = time.time()
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                        {"role": "system", "content": role},
                        {"role": "user", "content": prompt},
                    ]
                )
            
            """
            response = openai.Completion.create(
                engine=self.engine_id,
                prompt=prompt,
                max_tokens=100,
                n=1,
                stop=None,
                temperature=0.7,
            )"""
            
            #self.printer(response.choices[0].message.content)
            #self.tmp = response
            return response.choices[0].message.content

        except openai.error.RateLimitError:
            self.enable_chatgpt = False
            return "OpenAI: API limit exceeded. Please wait and try again later."

        except Exception as e:
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout:
                self.enable_chatgpt = False
                return f"Connection: Timeout ({timeout}s) exceeded. GPT disabled"
 

    def printer(self, response):
        sys.stdout.write("openai:  " + "\033[91m" + response + "\033[0m" + "\n\n", flush = True)
        sys.stdout.flush()


if __name__ == "__main__":

    API_KEY = "sk-..."
    gpt = ChatGpt(api_key = API_KEY, enable_chatgpt = True)
    res = gpt.chatgpt_api("I'm living at the Bay Bridge. Is that close to you? ")
    #gpt.printer(res)
    