import 'dart:async';

import 'package:flutter/material.dart';

import '../models/detected_note.dart';
import '../services/flutter_pitch_detection_service.dart';
import '../services/note_recording_service.dart';

class StreamScreen extends StatefulWidget {
  const StreamScreen({super.key});

  @override
  State<StreamScreen> createState() => _StreamScreenState();
}

class _StreamScreenState extends State<StreamScreen> {
  final FlutterPitchDetectionService _pitchService =
      FlutterPitchDetectionService();

  final NoteRecordingService _noteRecordingService = NoteRecordingService();

  StreamSubscription? _pitchSubscription;

  String _statusText = 'Stream not started';
  bool _isRecording = false;
  List<DetectedNote> _recordedNotes = [];

  Future<void> _startRecording() async {
    try {
      await _pitchService.start();

      _noteRecordingService.clear();

      _pitchSubscription = _pitchService.pitchStream.listen((pitchResult) {
        _noteRecordingService.processPitch(pitchResult);

        if (!mounted) return;

        setState(() {
          _recordedNotes = _noteRecordingService.notes;
          _statusText =
              'Detecting: ${pitchResult.note} - ${pitchResult.frequency.toStringAsFixed(2)} Hz';
        });
      });

      if (!mounted) return;

      setState(() {
        _isRecording = true;
        _statusText = 'Recording notes...';
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _statusText = 'Error: $e';
      });
    }
  }

  Future<void> _stopRecording() async {
    await _pitchSubscription?.cancel();
    _pitchSubscription = null;

    _noteRecordingService.stopRecording();
    await _pitchService.stop();

    if (!mounted) return;

    setState(() {
      _isRecording = false;
      _recordedNotes = _noteRecordingService.notes;
      _statusText = 'Recording stopped';
    });
  }

  @override
  void dispose() {
    unawaited(_pitchSubscription?.cancel());
    unawaited(_pitchService.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Melody Recording'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Text(
              _statusText,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 20),
            ),

            const SizedBox(height: 30),

            ElevatedButton(
              onPressed: _isRecording ? null : _startRecording,
              child: const Text('Start Recording'),
            ),

            const SizedBox(height: 16),

            ElevatedButton(
              onPressed: _isRecording ? _stopRecording : null,
              child: const Text('Stop Recording'),
            ),

            const SizedBox(height: 30),

            const Text(
              'Recorded Notes',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 16),

            Expanded(
              child: _recordedNotes.isEmpty
                  ? const Center(
                      child: Text('No notes recorded yet'),
                    )
                  : ListView.builder(
                      itemCount: _recordedNotes.length,
                      itemBuilder: (context, index) {
                        final note = _recordedNotes[index];

                        return ListTile(
                          leading: Text('${index + 1}'),
                          title: Text(note.note),
                          subtitle: Text(
                            '${note.frequency.toStringAsFixed(2)} Hz — '
                            '${note.durationSeconds.toStringAsFixed(2)} s',
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}