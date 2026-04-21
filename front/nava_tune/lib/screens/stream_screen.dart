import 'dart:async';

import 'package:flutter/material.dart';
import '../services/microphone_service.dart';

class StreamScreen extends StatefulWidget {
  const StreamScreen({super.key});

  @override
  State<StreamScreen> createState() => _StreamScreenState();
}

class _StreamScreenState extends State<StreamScreen> {
  final MicrophoneService _microphoneService = MicrophoneService();

  String _statusText = 'Microphone not started';
  bool _isRecording = false;

  Future<void> _requestMicPermission() async {
    final granted = await _microphoneService.requestPermission();

    if (!mounted) return;

    setState(() {
      _statusText = granted
          ? 'Microphone permission granted'
          : 'Microphone permission denied';
    });
  }

  Future<void> _startRecording() async {
    try {
      await _microphoneService.startRecording();

      if (!mounted) return;

      setState(() {
        _isRecording = true;
        _statusText = 'Recording started';
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _statusText = 'Error: $e';
      });
    }
  }

  Future<void> _stopRecording() async {
    await _microphoneService.stopRecording();

    if (!mounted) return;

    setState(() {
      _isRecording = false;
      _statusText = 'Recording stopped';
    });
  }

  @override
  void dispose() {
    unawaited(_microphoneService.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Audio Stream'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              _statusText,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 20),
            ),
            const SizedBox(height: 30),
            ElevatedButton(
              onPressed: _requestMicPermission,
              child: const Text('Request Microphone Permission'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isRecording ? null : _startRecording,
              child: const Text('Start Recording'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isRecording ? _stopRecording : null,
              child: const Text('Stop Recording'),
            ),
          ],
        ),
      ),
    );
  }
}
