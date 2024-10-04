import io
from threading import Thread

import pyaudio
from pydub import AudioSegment

DEFAULT = "\033[0m"
DARK_BLUE = "\033[34m"


class Player(Thread):
    def __init__(self, audio_queue):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
        )
        self.audio_queue = audio_queue
        self._interrupted = False

    def run(self):
        self.stream.start_stream()
        self._play_queue()
        self.stream.stop_stream()
        self.stream.close()

    def interrupt(self):
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

        self._interrupted = True

    def _play_queue(self):
        while True:
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                if chunk is None:
                    break

                seg = self._build_segment(chunk)
                self.stream.write(seg.raw_data)
            except Exception:
                pass

    def _build_segment(self, chunk):
        return AudioSegment.from_file(
            io.BytesIO(chunk),
            format="raw",
            sample_width=2,
            frame_rate=16000,
            channels=1,
        )
