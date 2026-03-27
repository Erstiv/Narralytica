#!/usr/bin/env python3
"""
Narralytica: Whisper Transcription (Run on M5 Mac)

Uses faster-whisper (large-v3) to produce word-level transcription with
precise timestamps. Runs in parallel with gemini_index.py.

Usage:
    python whisper_transcribe.py input/simpsons_s04e17.ogm

Output: processing/output/whisper_transcript.json

Install:
    pip install faster-whisper
"""
import json
import sys
import os
import time
import argparse


def transcribe(input_path: str, output_path: str, model_size: str = "large-v3") -> None:
    from faster_whisper import WhisperModel

    print(f"Loading Whisper {model_size} model...")
    start_time = time.time()

    # int8 is fast on Apple Silicon and uses less memory
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"Model loaded in {time.time() - start_time:.1f}s")
    print(f"Transcribing: {input_path}")

    segments, info = model.transcribe(
        input_path,
        language="en",
        word_timestamps=True,
        vad_filter=True,  # Skip silence for speed
    )

    print(f"Detected language: {info.language} (probability {info.language_probability:.2f})")

    transcript_segments = []
    word_count = 0

    for segment in segments:
        seg_data = {
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
            "words": [],
        }

        if segment.words:
            for word in segment.words:
                seg_data["words"].append({
                    "word": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    "probability": round(word.probability, 3),
                })
                word_count += 1

        transcript_segments.append(seg_data)

    elapsed = time.time() - start_time

    result = {
        "source_file": os.path.basename(input_path),
        "language": info.language,
        "duration_seconds": info.duration,
        "processing_time_seconds": round(elapsed, 1),
        "total_segments": len(transcript_segments),
        "total_words": word_count,
        "segments": transcript_segments,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nDone! {word_count} words in {len(transcript_segments)} segments")
    print(f"Processing time: {elapsed:.1f}s ({info.duration / elapsed:.1f}x realtime)")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio/video with Whisper")
    parser.add_argument("input_path", help="Path to audio or video file")
    parser.add_argument(
        "--output",
        default="processing/output/whisper_transcript.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size (default: large-v3)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input_path):
        print(f"ERROR: File not found: {args.input_path}")
        sys.exit(1)

    transcribe(args.input_path, args.output, args.model)
