import 'dart:async';
import 'dart:typed_data';

import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

class MicrophoneService {
  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<Uint8List>? _audioStreamSubscription;

  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  Future<void> startRecording() async {
    final hasPermission = await requestPermission();
    if (!hasPermission) {
      throw Exception('Microphone permission not granted.');
    }

    if (await _recorder.isRecording()) {
      return;
    }

    final stream = await _recorder.startStream(
      const RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        numChannels: 1,
        sampleRate: 44100,
      ),
    );

    await _audioStreamSubscription?.cancel();
    _audioStreamSubscription = stream.listen((_) {});
  }

  Future<void> stopRecording() async {
    if (!await _recorder.isRecording()) {
      return;
    }

    await _recorder.stop();
    await _audioStreamSubscription?.cancel();
    _audioStreamSubscription = null;
  }

  Future<void> dispose() async {
    await _audioStreamSubscription?.cancel();
    _audioStreamSubscription = null;
    await _recorder.dispose();
  }
}
