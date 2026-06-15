"""Orchestrator: read TikTok LIVE chat -> AI reply -> voice -> live stream.

Run on a (free) cloud server while your TikTok account is LIVE.
  1) Start your TikTok LIVE (so there is a stream to attach to + chat to read).
  2) python main.py
The avatar video loops and speaks AI replies to incoming comments.
"""
import os
import threading

from dotenv import load_dotenv  # optional convenience; see note below
load_dotenv()  # loads .env if python-dotenv is installed; otherwise set env vars manually

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

import brain
import voice
from stream import StreamManager

USERNAME = os.environ["TIKTOK_USERNAME"]

stream = StreamManager()


def handle_comment(user: str, comment: str):
    """Generate a spoken reply for one comment (runs off the event loop)."""
    reply = brain.reply_to(user, comment)
    print(f"💬 {user}: {comment}\n🤖 {reply}")
    mp3 = voice.synth(reply)
    stream.enqueue(mp3)


def main():
    # Start the outbound stream (avatar + audio) to TikTok.
    stream.start()

    client = TikTokLiveClient(unique_id=f"@{USERNAME}")

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        print(f"Connected to @{USERNAME}'s LIVE chat.")

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        # offload blocking work (LLM + TTS) to a thread so the chat loop stays responsive
        threading.Thread(
            target=handle_comment, args=(event.user.nickname, event.comment), daemon=True
        ).start()

    try:
        client.run()
    finally:
        stream.stop()


if __name__ == "__main__":
    main()
