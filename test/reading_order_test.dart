import 'package:flutter_test/flutter_test.dart';
import 'package:old_permic_ocr_mobile/domain/entities/ocr_result.dart';
import 'package:old_permic_ocr_mobile/domain/entities/release_manifest.dart';

GlyphDetection detection(GlyphClass glyph, double left, double top,
        {double confidence = .9}) =>
    GlyphDetection(
      glyph: glyph,
      confidence: confidence,
      boundingBox:
          BoundingBox(left: left, top: top, right: left + 12, bottom: top + 18),
    );

void main() {
  const alpha = GlyphClass(id: 0, codePoint: 0x0391, label: 'Α');
  const beta = GlyphClass(id: 1, codePoint: 0x0392, label: 'Β');
  const gamma = GlyphClass(id: 2, codePoint: 0x0393, label: 'Γ');
  const delta = GlyphClass(id: 3, codePoint: 0x0394, label: 'Δ');

  test('orders detector output into left-to-right multi-line text', () {
    final result = orderDetections([
      detection(delta, 80, 70, confidence: .6),
      detection(beta, 60, 10, confidence: .8),
      detection(gamma, 10, 70, confidence: .7),
      detection(alpha, 10, 10),
    ]);

    expect(result.text, 'ΑΒ\nΓΔ');
    expect(result.lines, hasLength(2));
    expect(result.readingConfidence, closeTo(.75, .0001));
  });

  test('uses package-defined right-to-left order within each line', () {
    final result = orderDetections([
      detection(alpha, 10, 10),
      detection(beta, 60, 10),
    ], direction: ReadingDirection.rightToLeft);

    expect(result.text, 'ΒΑ');
  });

  test('tolerates a modest slant while grouping one line', () {
    final result = orderDetections([
      detection(beta, 58, 18),
      detection(alpha, 10, 10),
    ]);

    expect(result.lines, hasLength(1));
    expect(result.text, 'ΑΒ');
  });
}
