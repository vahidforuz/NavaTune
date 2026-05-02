import '../models/detected_note.dart';
import '../models/pitch_result.dart';

class NoteRecordingService {
  final List<DetectedNote> _notes = [];

  String? _currentNote;
  double _currentFrequency = 0;
  DateTime? _noteStartTime;
  DateTime? _lastPitchTime;

  static const int minNoteDurationMs = 250;
  static const int silenceTimeoutMs = 600;

  List<DetectedNote> get notes => List.unmodifiable(_notes);

  void processPitch(PitchResult pitch) {
    final now = DateTime.now();

    if (_currentNote == null) {
      _startNote(pitch, now);
      return;
    }

    if (pitch.note == _currentNote) {
      _currentFrequency = pitch.frequency;
      _lastPitchTime = now;
      return;
    }

    _endCurrentNote(now);
    _startNote(pitch, now);
  }

  void checkSilence() {
    if (_currentNote == null || _lastPitchTime == null) return;

    final now = DateTime.now();
    final silenceDuration =
        now.difference(_lastPitchTime!).inMilliseconds;

    if (silenceDuration >= silenceTimeoutMs) {
      _endCurrentNote(_lastPitchTime!);
    }
  }

  void stopRecording() {
    if (_currentNote != null) {
      _endCurrentNote(DateTime.now());
    }
  }

  void clear() {
    _notes.clear();
    _currentNote = null;
    _currentFrequency = 0;
    _noteStartTime = null;
    _lastPitchTime = null;
  }

  void _startNote(PitchResult pitch, DateTime now) {
    _currentNote = pitch.note;
    _currentFrequency = pitch.frequency;
    _noteStartTime = now;
    _lastPitchTime = now;
  }

  void _endCurrentNote(DateTime endTime) {
    if (_currentNote == null || _noteStartTime == null) return;

    final duration =
        endTime.difference(_noteStartTime!).inMilliseconds;

    if (duration >= minNoteDurationMs) {
      _notes.add(
        DetectedNote(
          note: _currentNote!,
          frequency: _currentFrequency,
          startTime: _noteStartTime!,
          endTime: endTime,
        ),
      );
    }

    _currentNote = null;
    _currentFrequency = 0;
    _noteStartTime = null;
    _lastPitchTime = null;
  }
}