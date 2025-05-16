import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pydub import AudioSegment
from io import BytesIO
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

st.set_page_config(page_title="MP3 Clipper", layout="centered")
st.title("🎵 MP3 Clipper")

uploaded_file = st.file_uploader("Upload an MP3 file", type=["mp3"])

if uploaded_file:
    # Load audio
    audio = AudioSegment.from_file(uploaded_file, format="mp3")
    audio_duration = len(audio) / 1000  # milliseconds to seconds
    st.audio(uploaded_file)

    # Convert to waveform data
    samples = np.array(audio.get_array_of_samples())
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
        samples = samples.mean(axis=1)  # mono mixdown

    time_axis = np.linspace(0, audio_duration, num=len(samples))

    # Slider for clipping
    start_sec, end_sec = st.slider(
        "Select clip range",
        min_value=0.0,
        max_value=audio_duration,
        value=(0.0, audio_duration),
        step=0.1,
    )

    # Display waveform with clipping region
    fig, ax = plt.subplots()
    ax.plot(time_axis, samples, linewidth=0.5)
    ax.axvline(x=start_sec, color='green', linestyle='--', label='Start')
    ax.axvline(x=end_sec, color='red', linestyle='--', label='End')
    ax.set_title("Waveform with Clip Range")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()
    st.pyplot(fig)

    # Clip the audio
    start_ms = int(start_sec * 1000)
    end_ms = int(end_sec * 1000)
    clipped_audio = audio[start_ms:end_ms]

    # Button to download
    if st.button("Generate clipped MP3"):
        # Get original metadata and bitrate
        original_mp3 = MP3(uploaded_file)
        bitrate = original_mp3.info.bitrate

        output_io = BytesIO()
        clipped_audio.export(output_io, format="mp3", bitrate=f"{bitrate}").seek(0)

        # Re-apply metadata using mutagen
        try:
            original_tags = ID3(uploaded_file)
            clipped_tags = ID3()
            for frame in original_tags.values():
                clipped_tags.add(frame)
            clipped_tags.save(output_io)
        except error.ID3NoHeaderError:
            pass  # No metadata to copy

        st.download_button(
            label="Download Clipped MP3",
            data=output_io,
            file_name="clipped_audio.mp3",
            mime="audio/mpeg"
        )
