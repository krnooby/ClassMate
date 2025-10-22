# Sound Effects Library

This directory contains sound effects for enhancing listening comprehension exercises with realistic environmental audio.

## Directory Structure

```
effects/
├── effects_library.json    # JSON catalog of all sound effects
├── README.md              # This file
└── *.mp3                  # Sound effect files
```

## Categories

### 📱 Phone & Messaging (4 effects)
- `phone_ring.mp3` - Classic phone ring
- `smartphone_ring.mp3` - Modern smartphone ringtone
- `text_notification.mp3` - SMS/message notification
- `call_connect.mp3` - Call connecting tone

### 🚪 Door & Entry (3 effects)
- `doorbell.mp3` - Ding-dong doorbell
- `door_knock.mp3` - Three knocks
- `door_open_close.mp3` - Door opening/closing sound

### 🏫 School & Office (3 effects)
- `school_bell.mp3` - School bell/class change
- `keyboard_typing.mp3` - Keyboard typing
- `paper_shuffle.mp3` - Paper shuffling/page turning

### 🛍️ Shop & Cafe (2 effects)
- `cash_register.mp3` - POS payment success
- `coffee_machine.mp3` - Coffee machine/espresso steam

### 🚇 Transportation (2 effects)
- `subway_announcement.mp3` - Subway arrival chime
- `airport_boarding.mp3` - Airport boarding announcement tone

### 🌧️ Nature & Outdoor (2 effects)
- `rain.mp3` - Rain ambient sound
- `birds_chirping.mp3` - Bird chirping

### 🏥 Hospital (1 effect)
- `hospital_ambient.mp3` - Hospital ambient sound

### 🔊 General Ambient (3 effects)
- `cafe_ambient.mp3` - Cafe background noise
- `office_ambient.mp3` - Office ambient sound
- `outdoor_ambient.mp3` - Outdoor ambient sound

### 📝 Exam Cues (2 effects)
- `test_start_tone.mp3` - Test passage start tone
- `test_end_tone.mp3` - Test passage end tone

## Usage in TTS Service

Sound effects are automatically mixed into listening problems when the `[EFFECT]` tag is used in the problem generation prompt.

### Example Usage

```python
from shared.services.tts_service import get_tts_service

# Problem with [EFFECT] tag
content = """
[SPEAKERS]: {"speakers":[{"name":"Emma","gender":"female","voice":"Samantha"}]}
[EFFECT]: phone_ring
[AUDIO]:
Emma: Hello? Yes, I can talk now.
"""

tts_service = get_tts_service()
audio_url = tts_service.create_listening_audio(content)
# Result: Audio with phone ring effect mixed at -20dB
```

### Supported Effect Names

Use these names in `[EFFECT]: <name>` tags:

- `phone_ring`, `smartphone_ring`, `text_notification`, `call_connect`
- `doorbell`, `door_knock`, `door_open_close`
- `school_bell`, `keyboard_typing`, `paper_shuffle`
- `cash_register`, `coffee_machine`
- `subway_announcement`, `airport_boarding`
- `rain`, `birds_chirping`
- `hospital_ambient`
- `cafe_ambient`, `office_ambient`, `outdoor_ambient`
- `test_start_tone`, `test_end_tone`

## Usage Scenarios

### Phone Call
```
[EFFECT]: smartphone_ring
[AMBIENT]: office_ambient
```

### Cafe Meeting
```
[EFFECT]: cafe_ambient
Additional: coffee_machine (manual)
```

### School Scene
```
[EFFECT]: school_bell
Additional: paper_shuffle (manual)
```

### Hospital Visit
```
[EFFECT]: hospital_ambient
Additional: doorbell (manual)
```

### Airport Travel
```
[EFFECT]: airport_boarding
Additional: outdoor_ambient (manual)
```

### Rainy Day
```
[EFFECT]: rain
Additional: door_knock (manual)
```

## Technical Details

- **Format**: MP3, 128kbps
- **Mixing**: Effects are mixed at -20dB below dialogue
- **Duration**: Effects loop/extend to match dialogue length
- **Generation**: Created using ffmpeg with lavfi filters

## Adding New Effects

1. Generate the effect file using ffmpeg
2. Place it in `static/effects/`
3. Add entry to `effects_library.json`
4. Update `tts_service.py` effects dictionary
5. Update this README

### Example ffmpeg Commands

```bash
# Phone ring (800Hz + 1200Hz)
ffmpeg -f lavfi -i "sine=frequency=800:duration=2" -af "volume=0.2" phone_ring.mp3

# Doorbell (ding-dong)
ffmpeg -f lavfi -i "sine=frequency=660:duration=0.3" ding.mp3
ffmpeg -f lavfi -i "sine=frequency=528:duration=0.4" dong.mp3
ffmpeg -i ding.mp3 -i dong.mp3 -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1" doorbell.mp3

# Ambient cafe noise
ffmpeg -f lavfi -i "anoisesrc=duration=10:color=brown:amplitude=0.05" cafe_ambient.mp3

# Rain
ffmpeg -f lavfi -i "anoisesrc=duration=10:color=brown:amplitude=0.08" -af "lowpass=f=2000,highpass=f=200" rain.mp3
```

## File Sizes

Total library size: ~400KB (20 files)
Average file size: ~20KB per effect

## License

These sound effects are generated programmatically for educational use in the ClassMate platform.
