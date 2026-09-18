# Technical Specification: Professional Audio Engineering & Sound Design Engine (SPEC-AUDIO-EDITING)
**Standardized Architecture, Feature Catalog, and Mathematical Foundations for Digital Audio Workstation (DAW) Processing**

---

## 1. Overview & System Scope
This document specifies the complete functional architecture of the **Audio Engineering & Sound Design Engine**, covering multi-track channel strip mixing, 5-band parametric equalization, dynamic range compression, sidechain auto-ducking, spectral noise restoration, neural voice synthesis, and broadcast loudness compliance.

---

## 2. Comprehensive Feature Matrix

### 2.1 Multi-Track Channel Strip & Mixing Console

```
[DAW Channel Strip Architecture]
 ├── Pre-Amp Gain / Trim (-24 dB to +24 dB)
 ├── Dynamic Processing (Compressor / Limiter / Expander / Gate)
 ├── 5-Band Parametric Equalizer (High-Pass, Peaking, High-Shelf)
 ├── Auxiliary Sends (Reverb & Delay Buses)
 ├── Track Fader (Linear / Logarithmic Volume)
 ├── Pan Potentiometer (Stereo Balance -100% Left to +100% Right)
 ├── Solo (`S`), Mute (`M`), and Record Arm Controls
 └── Stereo Master Output Bus with True Peak Metering
```

1. **Track Assignment**:
   - `Track A1 (Dialogue / Voiceover)`: Primary spoken word track.
   - `Track A2 (Music / BGM)`: Musical underscore with sidechain attenuation.
   - `Track A3 (Sound Effects / SFX)`: Impacts, whooshes, risers, and Foley.
   - `Track A4 (Ambience / Room Tone)`: Atmospheric environmental textures.
2. **Summing & Bus Routing**:
   - 32-bit floating-point summing bus with zero internal clipping overhead.

---

### 2.2 5-Band Parametric Equalizer (EQ)

1. **Biquad IIR Filter Topologies**:
   - **Band 1 (Sub-Bass - 60 Hz)**: High-pass / low-shelf filter for cutting rumble and subsonic microphone thumps.
   - **Band 2 (Low-Mid - 250 Hz)**: Peaking bell filter targeting muddiness and boominess ($Q = 1.41$).
   - **Band 3 (Midrange - 1,000 Hz)**: Peaking bell filter defining core vocal body and intelligibility.
   - **Band 4 (Presence - 4,000 Hz)**: Peaking bell filter for speech clarity and bite.
   - **Band 5 (Air / High - 12,000 Hz)**: High-shelf filter adding sheen, breath, and spatial sparkle.
2. **Mathematical Filter Formulation**:
   - Second-order Direct Form II Transposed Biquad equations:
     $$y[n] = b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2]$$
   - Parameter ranges: Gain $\pm 15\text{ dB}$, Quality factor $Q \in [0.1, 10.0]$.

---

### 2.3 Dynamics Processing & Sidechain Auto-Ducking

1. **Downwards Compressor**:
   - Threshold ($-60\text{ dBFS}$ to $0\text{ dBFS}$), Compression Ratio ($1:1$ to $20:1$), Knee (Hard to Soft $0-10\text{ dB}$), Attack time ($1\text{ ms} - 500\text{ ms}$), Release time ($50\text{ ms} - 2000\text{ ms}$).
2. **Fairlight-Style Sidechain Auto-Ducking**:
   - **Key Signal (Trigger)**: Dialogue vocal track (A1).
   - **Target Track (Compressed)**: Background music track (A2).
   - **Envelope Behavior**:
     - *Attack ($80\text{ ms}$)*: Smooth musical dip as speech begins.
     - *Ducking Depth ($-16\text{ dB}$ to $-20\text{ dB}$)*: Attenuation preventing frequency masking between voice and instruments.
     - *Hold ($100\text{ ms}$)*: Prevents pumping during brief pauses between words.
     - *Release ($450\text{ ms}$)*: Seamless fade back to full music level.

---

### 2.4 Spectral Audio Restoration & AI Clean-up

1. **Spectral De-Noise & De-Hum**:
   - Background hum removal ($50\text{ Hz} / 60\text{ Hz}$ harmonic notch filters).
   - Stationary noise profiling and spectral subtraction for hiss, air conditioning, and fan noise.
2. **AI Dialogue Clarity & De-Reverb**:
   - Deep learning neural speech enhancement separating direct sound from reverberant room reflections.
3. **AI Stem Isolation**:
   - Spleeter / Demucs neural stem separation into 4 isolated stems: `Vocals`, `Drums`, `Bass`, `Other Instruments`.

---

### 2.5 Neural Voiceover Synthesis (TTS)

1. **Multi-Lingual Neural Speech Engine**:
   - Vietnamese Neural Voices (Edge-TTS: Hoài My, Nam Minh; ElevenLabs expressive clone).
   - English Neural Voices (Adam, Rachel, Antoni).
2. **Prosody & Emotional Modulation**:
   - Speech Rate ($0.5\times - 2.0\times$), Pitch shift ($\pm 12$ semitones), Volume gain ($0-200\%$).
   - Phoneme-level timing generation for subtitle synchronization.

---

### 2.6 Broadcast Loudness Standards & Metering

1. **EBU R128 & ITU-R BS.1770-4 Compliance**:
   - **Integrated Loudness ($LUFS$) Target**:
     - *YouTube Standard*: **$-14.0\text{ LUFS}$** ($\pm 1.0\text{ LUFS}$).
     - *TikTok & Instagram Reels*: **$-16.0\text{ LUFS}$** ($\pm 1.0\text{ LUFS}$).
     - *Broadcast TV*: **$-23.0\text{ LUFS}$** (EBU) / **$-24.0\text{ LUFS}$** (ATSC).
2. **True Peak Ceiling**:
   - Intersample True Peak limit: **$-1.0\text{ dBTP}$** preventing DAC reconstruction distortion.
3. **Stereo VU Metering**:
   - Real-time stereo left/right ballistic meters with Green ($-60\text{ dB}$ to $-12\text{ dB}$), Yellow ($-12\text{ dB}$ to $-3\text{ dB}$), and Red ($>-3\text{ dB}$) clipping alerts.

---

## 3. UI Implementation Mapping
All features listed above are mapped directly to the frontend components:
- [AudioLabStudio.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/audio/AudioLabStudio.tsx): 5-Band Parametric EQ Graph, Sidechain Auto-Ducking Faders, Channel Strip Mixer, Neural TTS Studio.
- [DualMonitorPlayer.tsx](file:///c:/Users/ADMIN/OneDrive/Máy tính/GitHub/ai-content-factory/frontend/src/components/timeline/DualMonitorPlayer.tsx): Live Stereo VU Meter, SMPTE Timecode Sync, Waveform Monitoring.
