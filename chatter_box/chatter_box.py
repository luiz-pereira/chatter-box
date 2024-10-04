import base64
import json
import os
import sys
from queue import Queue
from threading import Thread

from websockets.sync.client import connect

from audio_capture import AudioCapture
from audio_player import Player

SAMPLE_RATE = 16000
CHUNK_SIZE = 100  # 100ms

LIGHT_GREEN = "\033[92m"
DEFAULT = "\033[0m"


class ChatterBox:
    def __init__(self) -> None:
        self.socket = None
        self.audio_queue = Queue()
        self.player = Player(self.audio_queue)

    def run(self):
        headers = {
            "Authorization": "Bearer " + os.getenv("OPENAI_API_KEY"),
            "OpenAI-Beta": "realtime=v1",
        }
        self.socket = connect(
            "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01", additional_headers=headers
        )

        os.system("clear")
        print(
            LIGHT_GREEN
            + "Type or paste some instructions below or leave it blank for default. (press 'Enter' with an empty line to move ahead)"
            + DEFAULT
        )
        instructions = ""
        while data := input():
            instructions += data + "\n"

        if instructions:
            self.socket.send(json.dumps(self.session_update(instructions)))

        Thread(target=self.capture_voice).start()
        self.player.start()
        self._receive_loop()

    def _receive_loop(self):
        while True:
            try:
                msg = self.socket.recv()
                json_msg = json.loads(msg)
                if json_msg.get("type") == "response.audio.delta":
                    audio_response = base64.b64decode(json_msg["delta"])
                    self.audio_queue.put(audio_response)
                elif json_msg.get("type") == "input_audio_buffer.speech_started":
                    print("Speech started - INTERRUPTING")
                    self.player.interrupt()

                print(json_msg)
            except Exception as e:
                print(e)
                break

    def capture_voice(self):
        "opens audio stream and serves responses through a generator."
        audio_capture = AudioCapture(SAMPLE_RATE, CHUNK_SIZE)

        # opens the audio stream and starts recording
        with audio_capture as stream:
            os.system("clear")
            print("Listening:\n\n")
            stream.audio_input = []
            audio_generator = stream.generator()

            while not stream.closed:
                for audio_chunk in audio_generator:
                    payload = self._create_payload(audio_chunk)
                    self.socket.send(json.dumps(payload))

    def _create_payload(self, audio_chunk):
        b64_audio = base64.b64encode(audio_chunk).decode("utf-8")
        return {
            "type": "input_audio_buffer.append",
            "audio": b64_audio,
        }

    def session_update(self, instructions):
        return {
            "type": "session.update",
            "session": {
                "instructions": instructions,
                "voice": "alloy",
            },
        }


if __name__ == "__main__":
    playground = ChatterBox()
    playground.run()
