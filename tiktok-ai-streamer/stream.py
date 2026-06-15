"""Streams a looping avatar video + spoken replies to TikTok via RTMP (ffmpeg).

Approach (CPU-friendly, no GPU): a single ffmpeg process loops the avatar video
as the picture and reads audio (raw PCM s16le mono 24kHz) from a named pipe.
A feeder thread writes silence when idle, and the decoded PCM of each reply when
one is queued — so the live audio track is continuous.

Needs `ffmpeg` installed on the server (apt-get install -y ffmpeg).
v1: works in theory; tune buffer sizes on the real server.
"""
import os
import queue
import subprocess
import threading

RATE = 24000          # audio sample rate
SILENCE = b"\x00\x00" * (RATE // 10)  # 100ms of silence (s16le mono)
FIFO = "/tmp/ai_audio.pcm"


class StreamManager:
    def __init__(self):
        self.avatar = os.environ.get("AVATAR_VIDEO", "avatar.mp4")
        self.rtmp = os.environ["RTMP_URL"].rstrip("/") + "/" + os.environ["STREAM_KEY"]
        self.q = queue.Queue()
        self._stop = False

    def _decode_to_pcm(self, mp3_path: str) -> bytes:
        """Decode an mp3 reply to raw s16le mono PCM at RATE."""
        out = subprocess.run(
            ["ffmpeg", "-v", "quiet", "-i", mp3_path, "-f", "s16le",
             "-ar", str(RATE), "-ac", "1", "-"],
            capture_output=True,
        )
        return out.stdout

    def _feeder(self):
        """Continuously write audio to the fifo: silence when idle, replies when queued."""
        with open(FIFO, "wb") as pipe:
            while not self._stop:
                try:
                    mp3 = self.q.get(timeout=0.05)
                    pcm = self._decode_to_pcm(mp3)
                    try:
                        os.remove(mp3)
                    except OSError:
                        pass
                    pipe.write(pcm)
                    pipe.flush()
                except queue.Empty:
                    pipe.write(SILENCE)
                    pipe.flush()

    def enqueue(self, mp3_path: str):
        self.q.put(mp3_path)

    def start(self):
        if os.path.exists(FIFO):
            os.remove(FIFO)
        os.mkfifo(FIFO)
        threading.Thread(target=self._feeder, daemon=True).start()
        cmd = [
            "ffmpeg",
            "-stream_loop", "-1", "-re", "-i", self.avatar,          # looping avatar video
            "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", FIFO,  # audio from fifo
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2000k",
            "-pix_fmt", "yuv420p", "-g", "60",
            "-c:a", "aac", "-b:a", "128k", "-ar", str(RATE),
            "-f", "flv", self.rtmp,
        ]
        print("Starting ffmpeg → TikTok RTMP ...")
        self.proc = subprocess.Popen(cmd)
        return self.proc

    def stop(self):
        self._stop = True
        if hasattr(self, "proc"):
            self.proc.terminate()
