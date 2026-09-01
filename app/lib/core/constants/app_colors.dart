import 'package:flutter/material.dart';

/// Visual tokens for the archival OCR lab. Keep product colors here; widgets
/// should consume [ColorScheme] instead of hard-coding palette values.
abstract final class AppColors {
  static const ink = Color(0xFF1E201E);
  static const graphite = Color(0xFF3C3D37);
  static const olive = Color(0xFF697565);
  static const paper = Color(0xFFFFFEF0);
  static const readingPaper = Color(0xFFFBF9F2);
  static const readingInk = Color(0xFF333333);
  static const error = Color(0xFFB3261E);
  static const success = Color(0xFF2E7D32);
}
