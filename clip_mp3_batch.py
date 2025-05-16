import sys
import os
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError


def print_usage():
    print("Usage: python clip_mp3_batch.py input.mp3 output.mp3")
    sys.exit(1)


def find_last_non_silent_ms(audio, silence_thresh_db=-50, chunk_ms=100):
    """
    Scan backward in chunks to find last audio above threshold.
    Returns time (ms) of last non-silent audio plus small buffer.
    """
    total_ms = len(audio)
    print(f"Total duration: {total_ms / 1000:.2f} seconds")

    for i in range(total_ms, 0, -chunk_ms):
        chunk = audio[max(0, i - chunk_ms) : i]
        if chunk.dBFS > silence_thresh_db:
            # Add padding and return
            return min(i + 250, total_ms)

    return 0  # fully silent


def trim_trailing_silence(in_path, out_path):
    print(f"Loading MP3: {in_path}")
    audio = AudioSegment.from_file(in_path, format="mp3")

    print("Scanning for trailing silence...")
    end_ms = find_last_non_silent_ms(audio)

    trimmed = audio[:end_ms]

    # Preserve bitrate
    mp3_info = MP3(in_path)
    bitrate = mp3_info.info.bitrate

    print(f"Trimming at {end_ms / 1000:.2f}s, exporting to: {out_path}")
    trimmed.export(out_path, format="mp3", bitrate=f"{bitrate}")

    try:
        original_tags = ID3(in_path)
        clipped_tags = ID3(out_path)
        for frame in original_tags.values():
            clipped_tags.add(frame)
        clipped_tags.save(out_path)
        print("✔ Metadata copied.")
    except ID3NoHeaderError:
        print("ℹ No metadata found.")

    print("✅ Done.")


# --- Entry point ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print_usage()

    in_mp3 = sys.argv[1]
    out_mp3 = sys.argv[2]

    if not os.path.exists(in_mp3):
        print(f"Error: input file '{in_mp3}' not found.")
        sys.exit(1)

    trim_trailing_silence(in_mp3, out_mp3)
