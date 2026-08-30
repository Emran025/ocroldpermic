import 'package:flutter_test/flutter_test.dart';
import 'package:old_permic_ocr_mobile/domain/entities/ocr_result.dart';
import 'package:old_permic_ocr_mobile/domain/entities/release_manifest.dart';
import 'package:old_permic_ocr_mobile/domain/repositories/ocr_ports.dart';
import 'package:old_permic_ocr_mobile/domain/usecases/run_ocr.dart';

const _hash =
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';

final _model = InstalledModel(
  manifest: const OcrPackageManifest(
    schemaVersion: 1,
    packageId: 'cyrillic-test',
    version: '1.2.0',
    modelVersion: '1.2.0',
    language: 'Historical Cyrillic',
    script: 'Cyrillic',
    alphabetVersion: '1.2',
    minimumRuntimeVersion: '1.0.0',
    createdAtUtc: '2026-08-30T00:00:00Z',
    modelFormat: ModelFormat.onnx,
    model: ReleaseArtifact(
        id: 'model', path: 'model.onnx', bytes: 1, sha256: _hash),
    alphabetArtifact: ReleaseArtifact(
        id: 'alphabet', path: 'alphabet.json', bytes: 1, sha256: _hash),
    alphabet: [GlyphClass(id: 0, codePoint: 0x0410, label: 'А')],
    input: InputSpec(width: 640, height: 640),
    output: OutputSpec(),
  ),
  installPath: '/models/cyrillic-test/1.2.0',
  installedAt: DateTime.utc(2026, 8, 30),
  source: 'test',
  isActive: true,
);

class _FakeInference implements OcrInference {
  @override
  Future<InferenceOutput> infer(String imagePath, InstalledModel model,
          OcrRunConfiguration configuration) async =>
      InferenceOutput(
        detections: const [
          GlyphDetection(
            glyph: GlyphClass(id: 0, codePoint: 0x0410, label: 'А'),
            confidence: .97,
            boundingBox: BoundingBox(left: 20, top: 10, right: 32, bottom: 30),
          ),
        ],
        elapsed: const Duration(milliseconds: 18),
        imageWidth: 100,
        imageHeight: 80,
      );
}

void main() {
  test('creates a traceable editable result from mocked local inference',
      () async {
    final result = await RunOcr(_FakeInference()).call(
      imagePath: '/inputs/page.jpg',
      model: _model,
      configuration: const OcrRunConfiguration(confidenceThreshold: .7),
    );

    expect(result.rawText, 'А');
    expect(result.model.manifest.packageId, 'cyrillic-test');
    expect(result.inferenceTime, const Duration(milliseconds: 18));
    expect(result.imageWidth, 100);
    expect(result.copyWith(editedText: 'Б').resolvedText, 'Б');
    expect(
        result
            .copyWith(editedText: result.rawText, clearEditedText: true)
            .hasCorrections,
        isFalse);
  });
}
