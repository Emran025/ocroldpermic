import 'dart:math' as math;

import 'release_manifest.dart';

class AlternativePrediction {
  const AlternativePrediction({required this.glyph, required this.confidence});

  final GlyphClass glyph;
  final double confidence;
}

class GlyphDetection {
  const GlyphDetection({
    required this.glyph,
    required this.confidence,
    required this.boundingBox,
    this.alternatives = const [],
  });

  final GlyphClass glyph;
  final double confidence;
  final BoundingBox boundingBox;
  final List<AlternativePrediction> alternatives;

  double get left => boundingBox.left;
  double get top => boundingBox.top;
  double get right => boundingBox.right;
  double get bottom => boundingBox.bottom;
  double get centerX => boundingBox.centerX;
  double get centerY => boundingBox.centerY;
}

class OcrTextLine {
  const OcrTextLine(
      {required this.detections, required this.text, required this.baseline});

  final List<GlyphDetection> detections;
  final String text;
  final double baseline;
}

class OrderedText {
  const OrderedText(
      {required this.detections,
      required this.lines,
      required this.text,
      required this.readingConfidence});

  final List<GlyphDetection> detections;
  final List<OcrTextLine> lines;
  final String text;
  final double readingConfidence;
}

class OcrRunConfiguration {
  const OcrRunConfiguration({
    this.confidenceThreshold = 0.50,
    this.iouThreshold = 0.45,
    this.maxDetections = 500,
  })  : assert(confidenceThreshold >= 0 && confidenceThreshold <= 1),
        assert(iouThreshold >= 0 && iouThreshold <= 1),
        assert(maxDetections > 0);

  final double confidenceThreshold;
  final double iouThreshold;
  final int maxDetections;
}

class OcrResult {
  const OcrResult({
    required this.orderedText,
    required this.model,
    required this.inputPath,
    required this.createdAt,
    required this.inferenceTime,
    required this.configuration,
    required this.imageWidth,
    required this.imageHeight,
    this.editedText,
  });

  final OrderedText orderedText;
  final InstalledModel model;
  final String inputPath;
  final DateTime createdAt;
  final Duration inferenceTime;
  final OcrRunConfiguration configuration;
  final int imageWidth;
  final int imageHeight;
  final String? editedText;

  String get rawText => orderedText.text;
  String get resolvedText => editedText ?? rawText;
  bool get hasCorrections => editedText != null && editedText != rawText;

  OcrResult copyWith({String? editedText, bool clearEditedText = false}) =>
      OcrResult(
        orderedText: orderedText,
        model: model,
        inputPath: inputPath,
        createdAt: createdAt,
        inferenceTime: inferenceTime,
        configuration: configuration,
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        editedText: clearEditedText ? null : (editedText ?? this.editedText),
      );
}

/// Reconstructs multi-line text independently of detector output order.
class ReadingOrder {
  const ReadingOrder();

  OrderedText order(List<GlyphDetection> input,
      {ReadingDirection direction = ReadingDirection.leftToRight}) {
    if (input.isEmpty) {
      return const OrderedText(
          detections: [], lines: [], text: '', readingConfidence: 0);
    }
    final sortedByVerticalPosition = [...input]
      ..sort((a, b) => a.centerY.compareTo(b.centerY));
    final typicalHeight = _median(sortedByVerticalPosition
        .map((item) => item.boundingBox.height)
        .where((value) => value > 0)
        .toList());
    final tolerance = math.max(4.0, typicalHeight * 0.72);
    final lines = <_LineCluster>[];

    for (final detection in sortedByVerticalPosition) {
      _LineCluster? closest;
      var closestDistance = double.infinity;
      for (final line in lines) {
        final distance = (detection.centerY - line.baseline).abs();
        if (distance <= tolerance && distance < closestDistance) {
          closest = line;
          closestDistance = distance;
        }
      }
      if (closest == null) {
        lines.add(_LineCluster(detection));
      } else {
        closest.add(detection);
      }
    }

    lines.sort((a, b) => a.baseline.compareTo(b.baseline));
    final orderedLines = lines.map((line) {
      line.items.sort((a, b) {
        final x = a.centerX.compareTo(b.centerX);
        return direction == ReadingDirection.leftToRight ? x : -x;
      });
      return OcrTextLine(
        detections: List.unmodifiable(line.items),
        text: line.items.map((item) => item.glyph.label).join(),
        baseline: line.baseline,
      );
    }).toList(growable: false);
    final ordered =
        orderedLines.expand((line) => line.detections).toList(growable: false);
    final confidence =
        ordered.fold<double>(0, (sum, item) => sum + item.confidence) /
            ordered.length;
    return OrderedText(
      detections: ordered,
      lines: orderedLines,
      text: orderedLines.map((line) => line.text).join('\n'),
      readingConfidence: confidence,
    );
  }

  double _median(List<double> values) {
    if (values.isEmpty) return 16;
    values.sort();
    final middle = values.length ~/ 2;
    return values.length.isOdd
        ? values[middle]
        : (values[middle - 1] + values[middle]) / 2;
  }
}

class _LineCluster {
  _LineCluster(GlyphDetection item)
      : items = [item],
        baseline = item.centerY;

  final List<GlyphDetection> items;
  double baseline;

  void add(GlyphDetection item) {
    baseline = ((baseline * items.length) + item.centerY) / (items.length + 1);
    items.add(item);
  }
}

/// Backwards-compatible function entry point for simple callers and tests.
OrderedText orderDetections(List<GlyphDetection> input,
        {ReadingDirection direction = ReadingDirection.leftToRight}) =>
    const ReadingOrder().order(input, direction: direction);
