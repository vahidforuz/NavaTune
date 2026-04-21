import 'dart:async';
import '../models/pitch_result.dart';
import 'note_mapper.dart';

class PitchService {
  final StreamController<PitchResult> _controller =
  StreamController<PitchResult>.broadcast();

  Stream<PitchResult> get pitchStream => _controller.stream;

  Timer? _timer;
  int _index = 0;

  final List<double> _demoFrequencies = [
    437.8,
    440.0,
    442.3,
    329.6,
    261.6,
  ];

  void startDemo() {
    _timer?.cancel();

    _timer = Timer.periodic(const Duration(milliseconds: 1200), (_) {
      final frequency = _demoFrequencies[_index % _demoFrequencies.length];
      final mapped = NoteMapper.fromFrequency(frequency);

      _controller.add(
        PitchResult(
          note: mapped['note'],
          frequency: frequency,
          cents: mapped['cents'],
          status: mapped['status'],
        ),
      );

      _index++;
    });
  }

  void stopDemo() {
    _timer?.cancel();
  }

  void dispose() {
    _timer?.cancel();
    _controller.close();
  }
}