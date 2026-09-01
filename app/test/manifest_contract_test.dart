import 'package:flutter_test/flutter_test.dart';
import 'package:ocroldpermic/data/models/ocr_package_manifest_model.dart';
import 'package:ocroldpermic/domain/entities/release_manifest.dart';

void main() {
  const validManifest = {
    'schema_version': 1,
    'package_id': 'historic-greek',
    'version': '2.1.0',
    'model_version': '2.1.0-yolo',
    'language': 'Historical Greek',
    'script': 'Greek',
    'alphabet_version': '2026.08',
    'minimum_runtime_version': '1.0.0',
    'created_at': '2026-08-30T00:00:00Z',
    'model_format': 'onnx',
    'model': {
      'path': 'model/detector.onnx',
      'bytes': 2048,
      'sha256':
          'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    },
    'alphabet': {
      'artifact': {
        'path': 'alphabet/classes.json',
        'bytes': 128,
        'sha256':
            'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      },
      'classes': [
        {
          'id': 0,
          'unicode': 'U+0391',
          'character': 'Α',
          'name': 'GREEK CAPITAL LETTER ALPHA'
        },
        {'id': 1, 'unicode': 'U+0392', 'character': 'Β'},
      ],
    },
    'input': {'width': 640, 'height': 512, 'layout': 'nchw', 'channels': 3},
    'output': {
      'decoder': 'yolo_v8',
      'layout': 'channels_first',
      'box_format': 'xywh'
    },
    'reading_direction': 'ltr',
  };

  test('parses a self-describing non-Old-Permic package', () {
    final manifest = OcrPackageManifestModel.fromJson(validManifest);

    expect(manifest.displayName, 'Historical Greek · Greek');
    expect(manifest.glyphForClass(1)?.label, 'Β');
    expect(manifest.glyphForClass(1)?.unicode, 'U+0392');
    expect(manifest.input.height, 512);
    expect(manifest.readingDirection, ReadingDirection.leftToRight);
    expect(const ManifestValidator().validate(manifest).isValid, isTrue);
  });

  test('rejects duplicate alphabet class ids', () {
    final invalid = Map<String, dynamic>.from(validManifest);
    invalid['alphabet'] = {
      'artifact': {
        'path': 'alphabet/classes.json',
        'bytes': 128,
        'sha256':
            'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      },
      'classes': [
        {'id': 0, 'unicode': 'U+0391', 'character': 'Α'},
        {'id': 0, 'unicode': 'U+0392', 'character': 'Β'},
      ],
    };

    final validation = const ManifestValidator()
        .validate(OcrPackageManifestModel.fromJson(invalid));
    expect(validation.isValid, isFalse);
    expect(validation.problems.single, contains('unique'));
  });

  test('rejects packages that require a newer runtime', () {
    final invalid = Map<String, dynamic>.from(validManifest)
      ..['minimum_runtime_version'] = '2.0.0';

    final validation = const ManifestValidator(runtimeVersion: '1.0.0')
        .validate(OcrPackageManifestModel.fromJson(invalid));
    expect(validation.isValid, isFalse);
    expect(validation.problems.join(), contains('requires runtime'));
  });
}
