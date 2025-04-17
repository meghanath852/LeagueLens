from elevenlabs.client import ElevenLabs

client = ElevenLabs(
  api_key="sk_14912fc2a19b78dc9d8885061dd432d09ec7cfa04ace2ff9",
)

from elevenlabs import stream

text = "The errors show that your ElevenLabs free tier quota (10,000 credits) is insufficient for the amount of text being converted to speech. You still have 248 credits, but each request requires more than that (ranging from 255-359 credits per request)."


audio_stream = client.text_to_speech.convert_as_stream(
    text=text,
    voice_id="JJQDkHrp6uKU5Vk0WKhY",
    model_id="eleven_multilingual_v2",
)

# option 1: play the streamed audio locally
stream(audio_stream)

# # option 2: process the audio bytes manually
# for chunk in audio_stream:
#     if isinstance(chunk, bytes):
#         print(chunk)

