import 'dart:math' as math;

import '../../domain/entities/ocr_result.dart';
import '../../domain/entities/release_manifest.dart';
import 'image_preprocessor.dart';

/// Converts YOLO tensor output into domain detections without leaking tensor
/// shapes or class indexes into presentation code.
class YoloPostProcessor {
  const YoloPostProcessor();

  List<GlyphDetection> decode({
    required List<num> values,
    required OcrPackageManifest manifest,
    required PreprocessedImage image,
    required OcrRunConfiguration configuration,
  }) {
    final classes = manifest.alphabet.length;
    final featureCount = 4 + classes + (manifest.output.hasObjectness ? 1 : 0);
    if (featureCount <= 4 ||
        values.length < featureCount ||
        values.length % featureCount != 0) {
      throw const FormatException(
          'The model output does not match the package alphabet contract.');
    }
    final count = values.length ~/ featureCount;
    final candidates = <GlyphDetection>[];
    for (var prediction = 0; prediction < count; prediction++) {
      num read(int feature) =>
          manifest.output.layout == YoloLayout.channelsFirst
              ? values[(feature * count) + prediction]
              : values[(prediction * featureCount) + feature];
      final objectness =
          manifest.output.hasObjectness ? read(4).toDouble() : 1.0;
      final classOffset = 4 + (manifest.output.hasObjectness ? 1 : 0);
      var classId = 0;
      var score = -double.infinity;
      final scoredClasses = <_ScoredClass>[];
      for (var index = 0; index < classes; index++) {
        final confidence = read(classOffset + index).toDouble() * objectness;
        scoredClasses.add(_ScoredClass(index, confidence));
        if (confidence > score) {
          score = confidence;
          classId = index;
        }
      }
      if (score < configuration.confidenceThreshold) continue;
      final glyph = manifest.glyphForClass(classId);
      if (glyph == null) continue;
      final box = _toOriginalBox(read(0).toDouble(), read(1).toDouble(),
          read(2).toDouble(), read(3).toDouble(), manifest, image);
      if (box.width <= 0 || box.height <= 0) continue;
      scoredClasses.sort((a, b) => b.confidence.compareTo(a.confidence));
      final alternatives = scoredClasses
          .take(3)
          .map((candidate) => manifest.glyphForClass(candidate.classId) == null
              ? null
              : AlternativePrediction(
                  glyph: manifest.glyphForClass(candidate.classId)!,
                  confidence: candidate.confidence))
          .whereType<AlternativePrediction>()
          .toList(growable: false);
      candidates.add(GlyphDetection(
          glyph: glyph,
          confidence: score,
          boundingBox: box,
          alternatives: alternatives));
    }
    return _nms(
        candidates, configuration.iouThreshold, configuration.maxDetections);
  }

  BoundingBox _toOriginalBox(
    double one,
    double two,
    double three,
    double four,
    OcrPackageManifest manifest,
    PreprocessedImage image,
  ) {
    final xMultiplier = manifest.output.coordinates == 'normalized'
        ? manifest.input.width.toDouble()
        : 1.0;
    final yMultiplier = manifest.output.coordinates == 'normalized'
        ? manifest.input.height.toDouble()
        : 1.0;
    final x1 = manifest.output.boxFormat == 'xyxy'
        ? one * xMultiplier
        : (one - (three / 2)) * xMultiplier;
    final y1 = manifest.output.boxFormat == 'xyxy'
        ? two * yMultiplier
        : (two - (four / 2)) * yMultiplier;
    final x2 = manifest.output.boxFormat == 'xyxy'
        ? three * xMultiplier
        : (one + (three / 2)) * xMultiplier;
    final y2 = manifest.output.boxFormat == 'xyxy'
        ? four * yMultiplier
        : (two + (four / 2)) * yMultiplier;
    double originalX(double value) => ((value - image.padX) / image.scale)
        .clamp(0, image.originalWidth.toDouble());
    double originalY(double value) => ((value - image.padY) / image.scale)
        .clamp(0, image.originalHeight.toDouble());
    return BoundingBox(
        left: originalX(x1),
        top: originalY(y1),
        right: originalX(x2),
        bottom: originalY(y2));
  }

  List<GlyphDetection> _nms(
      List<GlyphDetection> input, double threshold, int maximum) {
    final candidates = [...input]
      ..sort((a, b) => b.confidence.compareTo(a.confidence));
    final kept = <GlyphDetection>[];
    for (final candidate in candidates) {
      if (kept.length == maximum) break;
      if (kept.any((existing) =>
          existing.glyph.id == candidate.glyph.id &&
          _iou(existing.boundingBox, candidate.boundingBox) > threshold)) {
        continue;
      }
      kept.add(candidate);
    }
    return kept;
  }

  double _iou(BoundingBox a, BoundingBox b) {
    final left = math.max(a.left, b.left);
    final top = math.max(a.top, b.top);
    final right = math.min(a.right, b.right);
    final bottom = math.min(a.bottom, b.bottom);
    final intersection = math.max(0, right - left) * math.max(0, bottom - top);
    final union = (a.width * a.height) + (b.width * b.height) - intersection;
    return union <= 0 ? 0 : intersection / union;
  }
}

class _ScoredClass {
  const _ScoredClass(this.classId, this.confidence);
  final int classId;
  final double confidence;
}
