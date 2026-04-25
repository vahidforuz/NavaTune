import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_pitch_detection/flutter_pitch_detection.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:record_platform_interface/record_platform_interface.dart';

import '../models/pitch_result.dart';
import '../utils/note_utils.dart';
import 'pitch_service.dart';

class FlutterPitchDetectionService implements PitchService {
  final FlutterPitchDetection _detector = FlutterPitchDetection();
  final AudioRecorder _recorder = AudioRecorder();

  final StreamController<PitchResult> _controller =
      StreamController<PitchResult>.broadcast();

  StreamSubscription<Map<String, dynamic>>? _subscription;
  StreamSubscription<Uint8List>? _recordingSubscription;
  StreamSubscription<Amplitude>? _amplitudeSubscription;
  bool _isStarted = false;
  PitchResult _lastResult = PitchResult.empty;
  int _pcmCalibrationFramesRemaining = 0;
  double _pcmNoiseFloor = 0;
  int _amplitudeCalibrationSamplesRemaining = 0;
  double _amplitudeNoiseFloor = 0;

  static const int _sampleRate = 44100;
  static const double _minPianoFrequency = 27.5;
  static const double _maxPianoFrequency = 4186.01;
  static const int _pcmCalibrationFrameTarget = 24;
  static const int _amplitudeCalibrationSamplesTarget = 8;

  @override
  Stream<PitchResult> get pitchStream => _controller.stream;

  @override
  Future<void> start() async {
    if (_isStarted) return;

    final microphonePermission = await Permission.microphone.request();
    if (!microphonePermission.isGranted) {
      throw Exception('Microphone permission not granted.');
    }

    if (!_supportsNativePitchPlugin) {
      await _startFallbackDetection();
      _isStarted = true;
      return;
    }

    await _detector.startDetection();

    await _detector.setParameters(
      sampleRate: _sampleRate,
      bufferSize: 8192,
      minPrecision: 0.75,
      toleranceCents: 8,
      a4Reference: 440.0,
    );

    _subscription = _detector.onPitchDetected.listen(
      (data) {
        final frequency = (data['frequency'] as num?)?.toDouble() ?? 0.0;
        final rawAccuracy = (data['accuracy'] as num?)?.toDouble() ?? 0.0;
        final volume = (data['volume'] as num?)?.toDouble() ?? 0.0;
        final noteOctave = (data['noteOctave'] as String?)?.trim();
        final pitchNote = NoteUtils.fromFrequency(frequency);
        final accuracy = rawAccuracy > 1 ? rawAccuracy / 100.0 : rawAccuracy;

        if (frequency < 27.5 || frequency > 4186.01) {
          return;
        }

        // Filter weak, invalid, or very noisy frames.
        if (accuracy < 0.60 || volume < 1.0) {
          return;
        }

        final result = PitchResult(
          note: noteOctave?.isNotEmpty == true ? noteOctave! : pitchNote.note,
          frequency: frequency,
          cents: pitchNote.cents,
          status: pitchNote.status,
          volume: volume,
          accuracy: rawAccuracy.round(),
        );

        _controller.add(result);
      },
      onError: (error, stackTrace) {
        _controller.addError(error, stackTrace);
      },
    );

    _isStarted = true;
  }

  @override
  Future<void> stop() async {
    await _subscription?.cancel();
    _subscription = null;
    await _recordingSubscription?.cancel();
    _recordingSubscription = null;
    await _amplitudeSubscription?.cancel();
    _amplitudeSubscription = null;

    if (_isStarted) {
      if (_supportsNativePitchPlugin) {
        await _detector.stopDetection();
      } else if (await _recorder.isRecording()) {
        await _recorder.stop();
      }
      _isStarted = false;
    }
  }

  @override
  Future<void> dispose() async {
    await stop();
    await _recorder.dispose();
    await _controller.close();
  }

  bool get _supportsNativePitchPlugin => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  Future<void> _startFallbackDetection() async {
    if (await _recorder.isRecording()) {
      return;
    }

    _pcmCalibrationFramesRemaining = _pcmCalibrationFrameTarget;
    _pcmNoiseFloor = 0;
    _amplitudeCalibrationSamplesRemaining = _amplitudeCalibrationSamplesTarget;
    _amplitudeNoiseFloor = 0;
    _lastResult = PitchResult.empty;

    final stream = await _recorder.startStream(
      const RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        numChannels: 1,
        sampleRate: _sampleRate,
      ),
    );

    _recordingSubscription = stream.listen(
      (bytes) {
        final result = _analyzePcmFrame(bytes);
        if (result != null) {
          _lastResult = result;
          _controller.add(result);
        }
      },
      onError: (Object error, StackTrace stackTrace) {
        _controller.addError(error, stackTrace);
      },
    );

    _amplitudeSubscription = _recorder
        .onAmplitudeChanged(const Duration(milliseconds: 250))
        .listen((amplitude) {
      final level = _normalizeDecibel(amplitude.current);
      if (_amplitudeCalibrationSamplesRemaining > 0) {
        final capturedSamples =
            _amplitudeCalibrationSamplesTarget - _amplitudeCalibrationSamplesRemaining;
        _amplitudeNoiseFloor =
            ((_amplitudeNoiseFloor * capturedSamples) + level) /
                (capturedSamples + 1);
        _amplitudeCalibrationSamplesRemaining--;

        _controller.add(
          PitchResult.empty.copyWith(
            status: 'Calibrating room noise... keep quiet',
            volume: level,
          ),
        );
        return;
      }

      final threshold = (_amplitudeNoiseFloor + 10).clamp(0.0, 100.0);
      final isSoundDetected = level >= threshold;

      if (!isSoundDetected && _lastResult.frequency > 0) {
        return;
      }

      final status = isSoundDetected
          ? 'Sound above noise floor, finding note'
          : 'Below noise threshold';

      _controller.add(
        PitchResult.empty.copyWith(
          status: status,
          volume: level,
        ),
      );
    });
  }

  PitchResult? _analyzePcmFrame(Uint8List bytes) {
    if (bytes.length < 4096) {
      return null;
    }

    final sampleCount = bytes.length ~/ 2;
    final samples = Float64List(sampleCount);
    double rms = 0;

    for (var i = 0; i < sampleCount; i++) {
      final low = bytes[i * 2];
      final high = bytes[i * 2 + 1];
      var value = (high << 8) | low;
      if (value >= 0x8000) {
        value -= 0x10000;
      }
      final normalized = value / 32768.0;
      samples[i] = normalized;
      rms += normalized * normalized;
    }

    rms = sqrt(rms / sampleCount);
    final volume = (rms * 100).clamp(0.0, 100.0).toDouble();

    if (_pcmCalibrationFramesRemaining > 0) {
      final capturedFrames = _pcmCalibrationFrameTarget - _pcmCalibrationFramesRemaining;
      _pcmNoiseFloor =
          ((_pcmNoiseFloor * capturedFrames) + volume) / (capturedFrames + 1);
      _pcmCalibrationFramesRemaining--;
      return null;
    }

    final threshold = max(1.5, (_pcmNoiseFloor * 1.35) + 1.0);
    if (volume < threshold) {
      return null;
    }

    final frequency = _detectFrequency(samples);
    if (frequency == null ||
        frequency < _minPianoFrequency ||
        frequency > _maxPianoFrequency) {
      return null;
    }

    final pitchNote = NoteUtils.fromFrequency(frequency);
    final accuracy = _estimateAccuracy(pitchNote.cents);

    return PitchResult(
      note: pitchNote.note,
      frequency: frequency,
      cents: pitchNote.cents,
      status: pitchNote.status,
      volume: volume,
      accuracy: accuracy,
    );
  }

  double? _detectFrequency(Float64List samples) {
    final minLag = (_sampleRate / _maxPianoFrequency).floor();
    final maxLag = min((_sampleRate / _minPianoFrequency).ceil(), samples.length ~/ 2);

    if (maxLag <= minLag) {
      return null;
    }

    double bestCorrelation = 0;
    var bestLag = -1;

    for (var lag = minLag; lag <= maxLag; lag++) {
      double correlation = 0;
      double energyA = 0;
      double energyB = 0;

      final limit = samples.length - lag;
      for (var i = 0; i < limit; i++) {
        final a = samples[i];
        final b = samples[i + lag];
        correlation += a * b;
        energyA += a * a;
        energyB += b * b;
      }

      if (energyA == 0 || energyB == 0) {
        continue;
      }

      final normalized = correlation / sqrt(energyA * energyB);
      if (normalized > bestCorrelation) {
        bestCorrelation = normalized;
        bestLag = lag;
      }
    }

    if (bestLag <= 0 || bestCorrelation < 0.65) {
      return null;
    }

    return _sampleRate / bestLag;
  }

  int _estimateAccuracy(int cents) {
    final centsDistance = cents.abs().clamp(0, 50);
    final stability = (1 - (centsDistance / 50)) * 100;
    return stability.round().clamp(0, 100).toInt();
  }

  double _normalizeDecibel(double decibels) {
    final normalized = ((decibels + 60) / 60) * 100;
    return normalized.clamp(0.0, 100.0).toDouble();
  }
}
