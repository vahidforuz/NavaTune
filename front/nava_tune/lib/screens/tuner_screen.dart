import 'dart:async';

import 'package:flutter/material.dart';

import '../models/pitch_result.dart';
import '../services/flutter_pitch_detection_service.dart';
import '../services/pitch_service.dart';

class TunerScreen extends StatefulWidget {
  const TunerScreen({super.key});

  @override
  State<TunerScreen> createState() => _TunerScreenState();
}

class _TunerScreenState extends State<TunerScreen> {
  late final PitchService _pitchService;
  StreamSubscription<PitchResult>? _pitchSubscription;

  PitchResult currentPitch = PitchResult.empty;
  bool isListening = false;
  bool isBusy = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _pitchService = FlutterPitchDetectionService();
  }

  void updatePitch(PitchResult result) {
    setState(() {
      currentPitch = result;
    });
  }

  Future<void> startListening() async {
    if (isListening || isBusy) return;

    try {
      setState(() {
        isBusy = true;
        errorMessage = null;
      });

      _pitchSubscription ??= _pitchService.pitchStream.listen(
        (result) {
          updatePitch(result);
        },
        onError: (error) {
          setState(() {
            errorMessage = error.toString();
            isListening = false;
          });
        },
      );

      await _pitchService.start();

      setState(() {
        isListening = true;
        isBusy = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isListening = false;
        isBusy = false;
      });
    }
  }

  Future<void> stopListening() async {
    if (!isListening || isBusy) return;

    setState(() {
      isBusy = true;
    });

    await _pitchSubscription?.cancel();
    _pitchSubscription = null;

    await _pitchService.stop();

    setState(() {
      isListening = false;
      isBusy = false;
      currentPitch = PitchResult.empty;
      errorMessage = null;
    });
  }

  @override
  void dispose() {
    _pitchSubscription?.cancel();
    _pitchService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final noteColor = switch (currentPitch.status) {
      'In Tune' => const Color(0xFF2E7D32),
      'Sharp' => const Color(0xFFB26A00),
      'Flat' => const Color(0xFF1565C0),
      _ => const Color(0xFF24333E),
    };
    final hasDetectedNote = currentPitch.frequency > 0;
    final hasSound = currentPitch.volume > 5;
    final hearingLabel = !isListening
        ? 'Microphone stopped'
        : hasDetectedNote
            ? 'Note detected'
            : hasSound
                ? 'Sound detected'
                : 'No sound detected';
    final hearingColor = !isListening
        ? const Color(0xFF7A8585)
        : hasDetectedNote
            ? const Color(0xFF2E7D32)
            : hasSound
                ? const Color(0xFFB26A00)
                : const Color(0xFFC62828);

    return Scaffold(
      backgroundColor: const Color(0xFFF6F1E9),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF6F1E9),
        title: const Text('Tuner'),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: double.infinity,
                  constraints: const BoxConstraints(maxWidth: 520),
                  padding: const EdgeInsets.all(28),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(28),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x12000000),
                        blurRadius: 24,
                        offset: Offset(0, 12),
                      ),
                    ],
                  ),
                  child: Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: hearingColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          hearingLabel,
                          style: TextStyle(
                            fontSize: 15,
                            color: hearingColor,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        currentPitch.note,
                        style: TextStyle(
                          fontSize: 72,
                          fontWeight: FontWeight.w800,
                          color: noteColor,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        currentPitch.frequency > 0
                            ? '${currentPitch.frequency.toStringAsFixed(2)} Hz'
                            : 'Press Start, then play one piano note near the microphone',
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        currentPitch.status,
                        style: const TextStyle(
                          fontSize: 16,
                          color: Color(0xFF5B6666),
                          fontWeight: FontWeight.w500,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 18),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Microphone level',
                            style: TextStyle(
                              fontSize: 13,
                              color: Color(0xFF5B6666),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(999),
                            child: LinearProgressIndicator(
                              minHeight: 12,
                              value: (currentPitch.volume / 100).clamp(0.0, 1.0),
                              backgroundColor: const Color(0xFFE4E9E7),
                              valueColor: AlwaysStoppedAnimation<Color>(
                                hearingColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          _MetricChip(
                            label: 'Diagnosis',
                            value: currentPitch.status,
                          ),
                          _MetricChip(
                            label: 'Offset',
                            value: '${currentPitch.cents} cents',
                          ),
                          _MetricChip(
                            label: 'Accuracy',
                            value: '${currentPitch.accuracy}%',
                          ),
                          _MetricChip(
                            label: 'Volume',
                            value: currentPitch.volume.toStringAsFixed(1),
                          ),
                        ],
                      ),
                      const SizedBox(height: 28),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          FilledButton.icon(
                            onPressed: isListening ? null : startListening,
                            icon: const Icon(Icons.mic_rounded),
                            label: Text(isBusy && !isListening ? 'Starting...' : 'Start'),
                          ),
                          const SizedBox(width: 16),
                          OutlinedButton.icon(
                            onPressed: isListening ? stopListening : null,
                            icon: const Icon(Icons.stop_rounded),
                            label: Text(isBusy && isListening ? 'Stopping...' : 'Stop'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (errorMessage != null) ...[
                  const SizedBox(height: 18),
                  Text(
                    errorMessage!,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F4F3),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF6A7676),
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              fontSize: 16,
              color: Color(0xFF172121),
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
