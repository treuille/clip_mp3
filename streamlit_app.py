import streamlit as st
import numpy as np
import altair as alt
from pydub import AudioSegment
from io import BytesIO
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError  # FIXED import
import pandas as pd
import warnings

# Optional: suppress pydub warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

st.set_page_config(page_title="🎧 MP3 Clipper", layout="wide")
st.title("🎧 MP3 Clipper with Waveform + Auto-Silence Trim")


# --- Helpers ---
@st.cache_resource
def load_audio(file_bytes):
    audio = AudioSegment.from_file(file_bytes, format="mp3")
    return audio


def downsample(samples, max_points=10000):
    """Downsample waveform for efficient plotting."""
    factor = len(samples) // max_points
    if factor <= 1:
        return samples
    return np.mean(samples[: factor * max_points].reshape(-1, factor), axis=1)


def prepare_waveform_data(samples, duration):
    times = np.linspace(0, duration, len(samples))
    return pd.DataFrame({"time": times, "amplitude": samples})


def find_last_nonzero_sec(samples, duration, threshold=0.001):
    normalized = samples / np.max(np.abs(samples))
    nonzero_indices = np.where(np.abs(normalized) > threshold)[0]
    if len(nonzero_indices) == 0:
        return 0.0
    last_sample_index = nonzero_indices[-1]
    return (last_sample_index / len(samples)) * duration


# --- Main App ---
uploaded_file = st.file_uploader("Upload a large MP3 file", type=["mp3"])

if uploaded_file:
    # Load audio and extract waveform
    audio = load_audio(uploaded_file)
    duration = len(audio) / 1000.0
    samples = np.array(audio.get_array_of_samples())
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
        samples = samples.mean(axis=1)

    # Downsample for plotting
    samples_ds = downsample(samples)
    waveform_df = prepare_waveform_data(samples_ds, duration)

    st.audio(uploaded_file)

    # Session state to store slider values
    if "start_sec" not in st.session_state:
        st.session_state["start_sec"] = 0.0
        st.session_state["end_sec"] = duration

    # Auto-clip silence at end
    if st.button("✂️ Auto-clip trailing silence"):
        st.session_state["end_sec"] = round(find_last_nonzero_sec(samples, duration), 2)

    # Clip range slider
    start_sec, end_sec = st.slider(
        "Select clip range (seconds)",
        min_value=0.0,
        max_value=duration,
        value=(st.session_state["start_sec"], st.session_state["end_sec"]),
        step=0.1,
    )
    st.session_state["start_sec"] = start_sec
    st.session_state["end_sec"] = end_sec

    # Plot waveform with Altair
    highlight = pd.DataFrame({"time": [start_sec, end_sec], "label": ["Start", "End"]})

    chart = (
        alt.Chart(waveform_df)
        .mark_line()
        .encode(x="time:Q", y="amplitude:Q")
        .properties(width=800, height=200)
    )

    markers = (
        alt.Chart(highlight)
        .mark_rule(color="red")
        .encode(x="time:Q", tooltip="label:N")
    )

    st.altair_chart(chart + markers)

    # Clip audio to selected range
    clipped_audio = audio[int(start_sec * 1000) : int(end_sec * 1000)]

    # Generate download
    if st.button("📦 Generate Clipped MP3"):
        with st.spinner("Processing clipped MP3..."):
            mp3_info = MP3(uploaded_file)
            bitrate = mp3_info.info.bitrate

            output = BytesIO()
            clipped_audio.export(output, format="mp3", bitrate=f"{bitrate}").seek(0)

            # Copy metadata
            try:
                original_tags = ID3(uploaded_file)
                clipped_tags = ID3()
                for frame in original_tags.values():
                    clipped_tags.add(frame)
                clipped_tags.save(output)
            except ID3NoHeaderError:
                pass

        st.success("✅ Clipped MP3 ready!")
        st.download_button(
            label="📥 Download Clipped MP3",
            data=output,
            file_name="clipped_audio.mp3",
            mime="audio/mpeg",
        )
