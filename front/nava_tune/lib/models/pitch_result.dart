class PitchResult {
  final String note;
  final double frequency;
  final double cents;
  final String status;

  const PitchResult({
    required this.note,
    required this.frequency,
    required this.cents,
    required this.status,
  });
}