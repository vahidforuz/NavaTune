class PitchResult {
  final String note;
  final double frequency;
  final int cents;
  final String status;
  final double volume;
  final int accuracy;

  const PitchResult({
    required this.note,
    required this.frequency,
    required this.cents,
    required this.status,
    required this.volume,
    required this.accuracy,
  });

  PitchResult copyWith({
    String? note,
    double? frequency,
    int? cents,
    String? status,
    double? volume,
    int? accuracy,
  }) {
    return PitchResult(
      note: note ?? this.note,
      frequency: frequency ?? this.frequency,
      cents: cents ?? this.cents,
      status: status ?? this.status,
      volume: volume ?? this.volume,
      accuracy: accuracy ?? this.accuracy,
    );
  }

  static const empty = PitchResult(
    note: '--',
    frequency: 0.0,
    cents: 0,
    status: 'Waiting for a note',
    volume: 0.0,
    accuracy: 0,
  );
}
