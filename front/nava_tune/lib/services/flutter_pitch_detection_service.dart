import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_pitch_detection/flutter_pitch_detection.dart';
import 'package:permission_handler/permission_handler.dart';

import '../models/pitch_result.dart';
import '../utils/note_utils.dart';
import 'pitch_service.dart';

class FlutterPitchDetectionService implements PitchService {
  final FlutterPitchDetection _detector = FlutterPitchDetection();

  final StreamController<PitchResult> _controller =
      StreamController<PitchResult>.broadcast();

  StreamSubscription<Map<String, dynamic>>? _subscription;

  bool _isStarted = false;

  String? _candidateNote;
  int _candidateCount = 0;

  static const int requiredStableFrames = 5;
  static const int _sampleRate = 44100;
  static const double _minPianoFrequency = 27.5;
  static const double _maxPianoFrequency = 4186.01;

  @override
  Stream<PitchResult> get pitchStream => _controller.stream;

  bool get _isAndroid =>
      !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  @override
  Future<void> start() async {
    if (_isStarted) return;

    if (!_isAndroid) {
      throw Exception('Pitch detection only supported on Android for now.');
    }

    final permission = await Permission.microphone.request();

    if (!permission.isGranted) {
      throw Exception('Microphone permission not granted');
    }

    _subscription = _detector.onPitchDetected.listen(
      (data) {
        final frequency =
            (data['frequency'] as num?)?.toDouble() ?? 0.0;

        final rawAccuracy =
            (data['accuracy'] as num?)?.toDouble() ?? 0.0;

        final volume =
            (data['volume'] as num?)?.toDouble() ?? 0.0;

        final noteOctave =
            (data['noteOctave'] as String?)?.trim();

        final accuracy =
            rawAccuracy > 1 ? rawAccuracy / 100.0 : rawAccuracy;

        if (frequency < _minPianoFrequency ||
            frequency > _maxPianoFrequency) {
          return;
        }

        if (accuracy < 0.60 || volume < 1.0) {
          return;
        }

        final pitchNote = NoteUtils.fromFrequency(frequency);

        final detectedNote =
            noteOctave?.isNotEmpty == true ? noteOctave! : pitchNote.note;

        if (_candidateNote == detectedNote) {
          _candidateCount++;
        } else {
          _candidateNote = detectedNote;
          _candidateCount = 1;
        }

        if (_candidateCount >= requiredStableFrames) {
          final result = PitchResult(
            note: detectedNote,
            frequency: frequency,
            cents: pitchNote.cents,
            status: pitchNote.status,
            volume: volume,
            accuracy: rawAccuracy.round(),
          );

          _controller.add(result);
        }
      },
      onError: (error, stackTrace) {
        _controller.addError(error, stackTrace);
      },
    );

    await _detector.startDetection();
    _isStarted = true;

    await _detector.setParameters(
      sampleRate: _sampleRate,
      bufferSize: 8192,
      minPrecision: 0.75,
      toleranceCents: 8,
      a4Reference: 440.0,
    );
  }

  @override
  Future<void> stop() async {
    await _subscription?.cancel();
    _subscription = null;

    if (_isStarted) {
      await _detector.stopDetection();
      _isStarted = false;
    }

    _candidateNote = null;
    _candidateCount = 0;
  }

  @override
  Future<void> dispose() async {
    await stop();
    await _controller.close();
  }
}