"""Free text-to-speech via edge-tts (Microsoft Edge voices, no API key)."""
import asyncio
import os
import tempfile
import edge_tts

VOICE = os.environ.get("TTS_VOICE", "tr-TR-EmelNeural")


async def _synth(text: str, path: str):
    await edge_tts.Communicate(text, VOICE).save(path)


def synth(text: str) -> str:
    """Synthesize `text` to an mp3 file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".mp3", dir="/tmp")
    os.close(fd)
    asyncio.run(_synth(text, path))
    return path
