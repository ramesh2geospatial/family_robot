import asyncio
import io
import os
import wave
import pyttsx3
import pyaudio

def synthesize(text):
    engine = pyttsx3.init()
    tmp = "test.wav"
    if os.path.exists(tmp):
        os.remove(tmp)
    engine.save_to_file(text, tmp)
    engine.runAndWait()
    with wave.open(tmp, "rb") as w:
        sr = w.getframerate()
        pcm = w.readframes(w.getnframes())
    os.remove(tmp)
    return pcm, sr

async def main():
    pcm, sr = await asyncio.to_thread(synthesize, "Hello from the thread pool!")
    print(f"Generated {len(pcm)} bytes at {sr} Hz")
    
    # Play
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=sr, output=True)
    stream.write(pcm)
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
