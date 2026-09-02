import 'package:flutter_test/flutter_test.dart';
import 'package:old_permic_ocr_mobile/domain/entities/ocr_result.dart';
import 'package:old_permic_ocr_mobile/domain/entities/release_manifest.dart';

void main() {
  test('orders Old Permic detections by line then left-to-right', () {
    const first = GlyphClass(id: 0, codePoint: 0x10350, label: '\u{10350}');
    const second = GlyphClass(id: 1, codePoint: 0x10351, label: '\u{10351}');
    final result = orderDetections([
      const GlyphDetection(glyph: second, confidence: .8, left: .7, top: .1, right: .8, bottom: .2),
      const GlyphDetection(glyph: first, confidence: .9, left: .1, top: .1, right: .2, bottom: .2),
    ]);
    expect(result.text, '\u{10350}\u{10351}');
    expect(result.readingConfidence, closeTo(.85, .0001));
  });
}
