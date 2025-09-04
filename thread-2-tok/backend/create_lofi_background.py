import numpy as np
from scipy.io.wavfile import write
import os

def create_simple_lofi_background(duration=300, filename="static/lofi_background.wav"):
    """Create a simple ambient background track."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Create a simple ambient sound with multiple sine waves
        # Low frequency bass
        bass = 0.3 * np.sin(2 * np.pi * 55 * t)  # A1 note
        
        # Mid frequency ambient tones
        mid1 = 0.2 * np.sin(2 * np.pi * 220 * t)  # A3 note
        mid2 = 0.15 * np.sin(2 * np.pi * 330 * t)  # E4 note
        
        # High frequency subtle tones
        high = 0.1 * np.sin(2 * np.pi * 440 * t)  # A4 note
        
        # Add some gentle modulation
        modulation = 0.05 * np.sin(2 * np.pi * 0.1 * t)
        
        # Combine all frequencies
        audio = bass + mid1 + mid2 + high + modulation
        
        # Apply gentle fade in/out
        fade_samples = int(sample_rate * 2)  # 2 second fade
        audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
        audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        # Normalize and convert to 16-bit
        audio = np.clip(audio, -1, 1)
        audio_16bit = (audio * 32767).astype(np.int16)
        
        # Save as WAV file
        write(filename, sample_rate, audio_16bit)
        print(f"Created ambient background track: {filename}")
        return filename
        
    except Exception as e:
        print(f"Error creating background music: {e}")
        return None

if __name__ == "__main__":
    create_simple_lofi_background()