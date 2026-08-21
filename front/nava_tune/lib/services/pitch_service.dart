import '../models/pitch_result.dart';

abstract class PitchService {
  Stream<PitchResult> get pitchStream;

  Future<void> start();
  Future<void> stop();
  Future<void> dispose();
}