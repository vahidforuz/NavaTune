import 'dart:async';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

class MicrophoneService {
  final AudioRecorder _audioRecorder = AudioRecorder();

  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  Future<bool> hasPermission() async {
    final status = await Permission.microphone.status;
    return status.isGranted;
  }

  Future<void> startRecording() async {
    if (!await _audioRecorder.hasPermission()) {
      throw Exception('Microphone permission not granted');
    }

    await _audioRecorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 44100,
        numChannels: 1,
      ),
      path: 'ava_tune_record.wav',
    );
  }

  Future<void> stopRecording() async {
    await _audioRecorder.stop();
  }

  Future<bool> isRecording() async {
    return _audioRecorder.isRecording();
  }

  void dispose() {
    _audioRecorder.dispose();
  }
}