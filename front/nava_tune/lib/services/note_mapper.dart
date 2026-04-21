class NoteMapper {
  static const List<String> _notes = [
    'C', 'C#', 'D', 'D#', 'E', 'F',
    'F#', 'G', 'G#', 'A', 'A#', 'B'
  ];

  static Map<String, dynamic> fromFrequency(double frequency) {
    if (frequency <= 0) {
      return {
        'note': '--',
        'cents': 0.0,
        'status': 'No signal',
      };
    }

    final midi = 69 + 12 * (logBase2(frequency / 440.0));
    final nearestMidi = midi.round();
    final cents = (midi - nearestMidi) * 100;

    final noteIndex = nearestMidi % 12;
    final octave = (nearestMidi ~/ 12) - 1;
    final noteName = '${_notes[noteIndex]}$octave';

    String status;
    if (cents < -5) {
      status = 'Flat';
    } else if (cents > 5) {
      status = 'Sharp';
    } else {
      status = 'In Tune';
    }

    return {
      'note': noteName,
      'cents': cents,
      'status': status,
    };
  }

  static double logBase2(double x) {
    return MathHelper.log(x) / MathHelper.log(2);
  }
}

class MathHelper {
  static double log(double x) {
    return x > 0 ? _ln(x) : 0;
  }

  static double _ln(double x) {
    return x == 1 ? 0 : (x - 1) / (x + 1) * 2;
  }
}