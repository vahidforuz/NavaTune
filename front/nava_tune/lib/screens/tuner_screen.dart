import 'dart:async';
import 'package:flutter/material.dart';
import '../models/pitch_result.dart';
import '../services/pitch_service.dart';

class TunerScreen extends StatefulWidget {
  const TunerScreen({super.key});

  @override
  State<TunerScreen> createState() => _TunerScreenState();
}

class _TunerScreenState extends State<TunerScreen> {
  PitchResult currentPitch = const PitchResult(
    note: 'A4',
    frequency: 440.0,
    cents: 0,
    status: 'In Tune',
  );

  final PitchService _pitchService = PitchService();
  StreamSubscription<PitchResult>? _subscription;

  void updatePitch(PitchResult result) {
    setState(() {
      currentPitch = result;
    });
  }

  @override
  void initState() {
    super.initState();

    _subscription = _pitchService.pitchStream.listen(updatePitch);
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _pitchService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tuner'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'AvaTune',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 30),
            Text(
              currentPitch.note,
              style: const TextStyle(fontSize: 72, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Text(
              '${currentPitch.frequency.toStringAsFixed(1)} Hz',
              style: const TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 8),
            Text(
              '${currentPitch.cents.toStringAsFixed(1)} cents',
              style: const TextStyle(fontSize: 20),
            ),
            const SizedBox(height: 8),
            Text(
              currentPitch.status,
              style: const TextStyle(fontSize: 22),
            ),
            const SizedBox(height: 30),
            Container(
              height: 12,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            const SizedBox(height: 30),
            Wrap(
              spacing: 12,
              children: [
                ElevatedButton(
                  onPressed: _pitchService.startDemo,
                  child: const Text('Start Demo'),
                ),
                ElevatedButton(
                  onPressed: _pitchService.stopDemo,
                  child: const Text('Stop Demo'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}