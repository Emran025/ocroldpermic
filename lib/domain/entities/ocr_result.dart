import 'release_manifest.dart';

class GlyphDetection {
  const GlyphDetection({required this.glyph, required this.confidence, required this.left, required this.top, required this.right, required this.bottom});
  final GlyphClass glyph;
  final double confidence;
  final double left;
  final double top;
  final double right;
  final double bottom;
  double get centerY => (top + bottom) / 2;
}

class OrderedText {
  const OrderedText({required this.detections, required this.text, required this.readingConfidence});
  final List<GlyphDetection> detections;
  final String text;
  final double readingConfidence;
}

OrderedText orderDetections(List<GlyphDetection> input) {
  final detections = [...input]..sort((a, b) {
    final lineDelta = a.centerY.compareTo(b.centerY);
    if (lineDelta != 0 && (a.centerY - b.centerY).abs() > ((a.bottom - a.top) + (b.bottom - b.top)) / 2) return lineDelta;
    final xDelta = a.left.compareTo(b.left);
    return xDelta != 0 ? xDelta : a.glyph.id.compareTo(b.glyph.id);
  });
  final confidence = detections.isEmpty ? 0.0 : (detections.map((item) => item.confidence).reduce((a, b) => a + b) / detections.length).toDouble();
  return OrderedText(detections: detections, text: detections.map((item) => item.glyph.label).join(), readingConfidence: confidence);
}
