import 'dart:math';

class NoteUtils {
  static const List<String> _notes = [
    'C', 'C#', 'D', 'D#', 'E', 'F',
    'F#', 'G', 'G#', 'A', 'A#', 'B',
  ];

  static PitchNote fromFrequency(
      double frequency, {
        double a4 = 440.0,
        int inTuneTolerance = 5,
      }) {
    if (frequency <= 0) {
      return const PitchNote(
        note: '--',
        cents: 0,
        status: 'No pitch',
      );
    }

    final midi = 69 + 12 * (log2(frequency / a4));
    final nearestMidi = midi.round();

    final noteIndex = nearestMidi % 12;
    final octave = (nearestMidi ~/ 12) - 1;
    final noteName = '${_notes[noteIndex]}$octave';

    final nearestFreq = a4 * pow(2, (nearestMidi - 69) / 12);
    final cents = (1200 * log2(frequency / nearestFreq)).round();

    String status;
    if (cents.abs() <= inTuneTolerance) {
      status = 'In Tune';
    } else if (cents < 0) {
      status = 'Flat';
    } else {
      status = 'Sharp';
    }

    return PitchNote(
      note: noteName,
      cents: cents,
      status: status,
    );
  }

  static double log2(double x) => log(x) / ln2;
}

class PitchNote {
  final String note;
  final int cents;
  final String status;

  const PitchNote({
    required this.note,
    required this.cents,
    required this.status,
  });
}