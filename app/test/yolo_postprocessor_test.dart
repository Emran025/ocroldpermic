import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:ocroldpermic/domain/entities/ocr_result.dart';
import 'package:ocroldpermic/domain/entities/release_manifest.dart';
import 'package:ocroldpermic/infrastructure/inference/image_preprocessor.dart';
import 'package:ocroldpermic/infrastructure/inference/yolo_postprocessor.dart';

const _hash =
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';

OcrPackageManifest manifest() => const OcrPackageManifest(
      schemaVersion: 1,
      packageId: 'example-greek',
      version: '1.0.0',
      modelVersion: '1.0.0',
      language: 'Greek',
      script: 'Greek',
      alphabetVersion: '1',
      minimumRuntimeVersion: '1.0.0',
      createdAtUtc: '2026-08-30T00:00:00Z',
      modelFormat: ModelFormat.onnx,
      model: ReleaseArtifact(
          id: 'model', path: 'model.onnx', bytes: 1, sha256: _hash),
      alphabetArtifact: ReleaseArtifact(
          id: 'alphabet', path: 'alphabet.json', bytes: 1, sha256: _hash),
      alphabet: [
        GlyphClass(id: 0, codePoint: 0x0391, label: 'Α'),
        GlyphClass(id: 1, codePoint: 0x0392, label: 'Β'),
      ],
      input: InputSpec(width: 640, height: 640),
      output: OutputSpec(),
    );

final image = PreprocessedImage(
  tensor: Float32List(0),
  shape: [1, 3, 640, 640],
  originalWidth: 640,
  originalHeight: 640,
  scale: 1,
  padX: 0,
  padY: 0,
);

void main() {
  test('maps highest scoring dynamic class to its alphabet glyph', () {
    final detections = const YoloPostProcessor().decode(
      values: const [100, 300, 100, 300, 40, 40, 50, 50, .9, .1, .2, .8],
      manifest: manifest(),
      image: image,
      configuration: const OcrRunConfiguration(confidenceThreshold: .5),
    );

    expect(detections, hasLength(2));
    expect(detections.first.glyph.label, 'Α');
    expect(detections.last.glyph.label, 'Β');
    expect(detections.first.boundingBox.left, 80);
    expect(detections.first.alternatives.first.glyph.unicode, 'U+0391');
  });

  test('suppresses overlapping duplicates of the same class', () {
    final detections = const YoloPostProcessor().decode(
      values: const [100, 102, 100, 102, 40, 40, 50, 50, .9, .8, .1, .1],
      manifest: manifest(),
      image: image,
      configuration:
          const OcrRunConfiguration(confidenceThreshold: .5, iouThreshold: .4),
    );

    expect(detections, hasLength(1));
  });
}
