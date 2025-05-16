import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pydub import AudioSegment
from io import BytesIO
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, error
import warnings

# Optional: suppress pydub warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

st.set_page_config(page_title="MP3 Clipper", layout="centered")
st.title("🎵 MP3 Clipper")

def load_audio(file_bytes):
    audio = AudioSegment.from_file(file_bytes, format="mp3")
    samples = np.array(audio.get_array_of_samples())
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
        samples = samples.mean(axis=1)  # mono mixdown
    duration = len(audio) / 1000.0
    return audio, samples, duration

def plot_waveform(samples, duration, start, end):
    time_axis = np.linspace(0, duration, num=len(samples))
    fig, ax = plt.subplots()
    ax.plot(time_axis, samples, linewidth=0.5)
    ax.axvline(x=start, color='green', linestyle='--', label='Start')
    ax.axvline(x=end, color='red', linestyle='--', label='End')
    ax.set_title("Waveform with Clip Range")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()
    return fig

uploaded_file = st.file_uploader("Upload an MP3 file", type=["mp3"])

if uploaded_file:
    # Save uploaded bytes to session state to avoid re-processing
    if "audio_data" not in st.session_state or st.session_state["filename"] != uploaded_file.name:
        st.session_state["filename"] = uploaded_file.name
        st.session_state["audio"], st.session_state["samples"], st.session_state["duration"] = load_audio(uploaded_file)

    audio = st.session_state["audio"]
    samples = st.session_state["samples"]
    duration = st.session_state["duration"]

    st.audio(uploaded_file)

    start_sec, end_sec = st.slider(
        "Select clip range (seconds)",
        min_value=0.0,
        max_value=duration,
        value=(0.0, duration),
        step=0.1,
    )

    st.pyplot(plot_waveform(samples, duration, start_sec, end_sec))

    clipped_audio = audio[int(start_sec * 1000):int(end_sec * 1000)]

    if st.button("Generate Clipped MP3"):
        # Get original bitrate
        mp3_info = MP3(uploaded_file)
        bitrate = mp3_info.info.bitrate

        # Export clipped audio
        output = BytesIO()
        clipped_audio.export(output, format="mp3", bitrate=f"{bitrate}").seek(0)

        # Copy tags if available
        try:
            original_tags = ID3(uploaded_file)
            clipped_tags = ID3()
            for frame in original_tags.values():
                clipped_tags.add(frame)
            clipped_tags.save(output)
        except error.ID3NoHeaderError:
            pass

        st.download_button(
            label="📥 Download Clipped MP3",
            data=output,
            file_name="clipped_audio.mp3",
            mime="audio/mpeg"
        )
