import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.parser import BilibiliParser
from src.core.fetcher import AudioFetcher

def main():
    bvid = "BV16g411M7r2"
    meta = BilibiliParser.parse(bvid)
    cid = meta["parts"][0]["cid"]
    print(f"Target: {meta['title']} P1 (cid={cid})")

    stream_info = AudioFetcher.get_audio_stream_url(bvid=bvid, cid=cid)
    print(f"Got audio url: {stream_info['best_stream_url'][:60]}... quality={stream_info['quality_desc']}")

    test_out = os.path.join(os.path.dirname(__file__), "sample_chunk.m4a")
    saved_path = AudioFetcher.download_audio(stream_info["best_stream_url"], test_out, max_bytes=512 * 1024)
    size = os.path.getsize(saved_path)
    print(f"Successfully downloaded partial test audio: {size} bytes ({saved_path})")
    if os.path.exists(saved_path):
        os.remove(saved_path)

if __name__ == "__main__":
    main()
