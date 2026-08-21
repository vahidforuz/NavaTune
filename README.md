# NavaTune
AvaTune is a real-time pitch detection and music tuner app built with Flutter. It listens to microphone input and displays note name, frequency (Hz), and tuning accuracy. Future features include melody recording and MIDI export.


front:

main.dart
   ↓
TunerScreen (UI)
   ↓
Services (mic + pitch detection)
   ↓
Models (PitchResult)
   ↓
Utils (math / note conversion)