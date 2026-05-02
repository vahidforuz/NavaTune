class DetectedNote {
  final String note;
  final double frequency;
  final DateTime startTime;
  final DateTime endTime;

  const DetectedNote({
    required this.note,
    required this.frequency,
    required this.startTime,
    required this.endTime,
  });

  double get durationSeconds {
    return endTime.difference(startTime).inMilliseconds / 1000.0;
  }

  Map<String, dynamic> toJson() {
    return {
      'note': note,
      'frequency': frequency,
      'startTime': startTime.toIso8601String(),
      'endTime': endTime.toIso8601String(),
      'durationSeconds': durationSeconds,
    };
  }
}