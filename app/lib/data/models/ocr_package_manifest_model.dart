import 'dart:convert';

import '../../domain/entities/release_manifest.dart';

class OcrPackageManifestModel {
  const OcrPackageManifestModel._();

  static OcrPackageManifest fromJsonString(String source, {Uri? sourceUri}) {
    final decoded = jsonDecode(source);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('The model manifest must be a JSON object.');
    }
    return fromJson(decoded, sourceUri: sourceUri);
  }

  /// Accepts schema v1 and the repository's previous release.json shape so an
  /// existing published model can migrate without application-specific logic.
  static OcrPackageManifest fromJson(Map<String, dynamic> json,
      {Uri? sourceUri}) {
    final modelNode = _map(json['model']) ?? _map(json['onnx']);
    if (modelNode == null) {
      throw const FormatException('The manifest has no model artifact.');
    }

    final alphabetNode = _map(json['alphabet']);
    final rawClasses = alphabetNode?['classes'] ??
        json['classes'] ??
        json['class_map'] ??
        const [];
    if (rawClasses is! List) {
      throw const FormatException('The alphabet classes must be a list.');
    }

    final alphabet = rawClasses
        .map((entry) => _glyph(_map(entry) ?? const {}))
        .toList(growable: false);
    final packageNode = _map(json['package']);
    final inputNode = _map(json['input']) ?? const {};
    final outputNode = _map(json['output']) ?? const {};
    final alphabetArtifactNode =
        _map(json['alphabet_artifact']) ?? _map(alphabetNode?['artifact']);

    return OcrPackageManifest(
      schemaVersion:
          _integer(json['schema_version'] ?? json['schemaVersion'] ?? 1),
      packageId: _string(
          json['package_id'] ?? packageNode?['id'] ?? json['release_id']),
      version: _string(
          json['version'] ?? packageNode?['version'] ?? json['release_id']),
      modelVersion: _string(json['model_version'] ??
          modelNode['version'] ??
          json['version'] ??
          json['release_id']),
      language: _string(
          json['language'] ?? packageNode?['language'] ?? json['model_scope']),
      script: _string(
          json['script'] ?? packageNode?['script'] ?? json['model_scope']),
      alphabetVersion: _string(json['alphabet_version'] ??
          alphabetNode?['version'] ??
          json['version'] ??
          json['release_id']),
      minimumRuntimeVersion:
          _string(json['minimum_runtime_version'] ?? '1.0.0'),
      createdAtUtc: _string(json['created_at'] ??
          json['created_at_utc'] ??
          DateTime.now().toUtc().toIso8601String()),
      modelFormat: _modelFormat(json['model_format'] ??
          modelNode['format'] ??
          (json.containsKey('onnx') ? 'onnx' : null)),
      model: _artifact('model', modelNode),
      alphabetArtifact: _artifact(
        'alphabet',
        alphabetArtifactNode ??
            <String, dynamic>{
              'path': alphabetNode?['path'] ?? 'alphabet/classes.json',
              'bytes': alphabetNode?['bytes'] ?? 0,
              'sha256': alphabetNode?['sha256'] ?? _emptyHash,
            },
      ),
      alphabet: alphabet,
      input: InputSpec(
        width: _integer(inputNode['width'] ??
            inputNode['size'] ??
            json['input_size'] ??
            640),
        height: _integer(inputNode['height'] ??
            inputNode['size'] ??
            json['input_size'] ??
            640),
        layout: _tensorLayout(inputNode['layout']),
        channels: _integer(inputNode['channels'] ?? 3),
        normalization: _string(inputNode['normalization'] ?? 'zero_to_one'),
        letterbox: inputNode['letterbox'] is bool
            ? inputNode['letterbox'] as bool
            : true,
        padColor: _integer(inputNode['pad_color'] ?? 114),
      ),
      output: OutputSpec(
        decoder: _string(outputNode['decoder'] ?? 'yolo_v8'),
        layout: _yoloLayout(outputNode['layout']),
        boxFormat: _string(outputNode['box_format'] ?? 'xywh'),
        coordinates: _string(outputNode['coordinates'] ?? 'pixels'),
        hasObjectness: outputNode['has_objectness'] is bool
            ? outputNode['has_objectness'] as bool
            : false,
      ),
      readingDirection:
          json['reading_direction']?.toString().toLowerCase() == 'rtl'
              ? ReadingDirection.rightToLeft
              : ReadingDirection.leftToRight,
      releaseSha256:
          _nullableString(json['release_sha256'] ?? json['checksum']),
      sourceUri: sourceUri,
    );
  }

  static const _emptyHash =
      '0000000000000000000000000000000000000000000000000000000000000000';

  static ReleaseArtifact _artifact(String id, Map<String, dynamic> source) =>
      ReleaseArtifact(
        id: _string(source['id'] ?? id),
        path: _string(source['url'] ?? source['path']),
        bytes: _integer(source['bytes'] ?? source['size_bytes'] ?? 0),
        sha256: _string(source['sha256'] ?? source['checksum'] ?? _emptyHash)
            .toLowerCase(),
        mediaType: _nullableString(source['media_type']),
      );

  static GlyphClass _glyph(Map<String, dynamic> source) {
    final codePoint = _codePoint(source['code_point'] ??
        source['codePoint'] ??
        source['unicode'] ??
        source['character']);
    return GlyphClass(
      id: _integer(source['id'] ?? source['class_id']),
      codePoint: codePoint,
      label: _string(source['character'] ??
          source['label'] ??
          String.fromCharCode(codePoint)),
      name: _nullableString(source['name']),
      display: _nullableString(source['display']),
    );
  }

  static int _codePoint(dynamic value) {
    if (value is int) return value;
    final string = _string(value);
    if (string.startsWith('U+')) {
      return int.parse(string.substring(2), radix: 16);
    }
    if (string.runes.length == 1) return string.runes.single;
    return int.parse(string);
  }

  static String _string(dynamic value) {
    final result = value?.toString().trim() ?? '';
    if (result.isEmpty) {
      throw const FormatException('A required manifest value is missing.');
    }
    return result;
  }

  static String? _nullableString(dynamic value) {
    final result = value?.toString().trim();
    return result == null || result.isEmpty ? null : result;
  }

  static int _integer(dynamic value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static Map<String, dynamic>? _map(dynamic value) =>
      value is Map<String, dynamic>
          ? value
          : value is Map
              ? Map<String, dynamic>.from(value)
              : null;

  static ModelFormat _modelFormat(dynamic value) =>
      switch (value?.toString().toLowerCase()) {
        'onnx' => ModelFormat.onnx,
        'tflite' => ModelFormat.tflite,
        _ => throw FormatException('Unsupported model format: $value'),
      };

  static TensorLayout _tensorLayout(dynamic value) =>
      value?.toString().toLowerCase() == 'nhwc'
          ? TensorLayout.nhwc
          : TensorLayout.nchw;

  static YoloLayout _yoloLayout(dynamic value) =>
      value?.toString().toLowerCase() == 'predictions_first'
          ? YoloLayout.predictionsFirst
          : YoloLayout.channelsFirst;
}

class ManifestValidator {
  const ManifestValidator({this.runtimeVersion = '1.0.0'});

  final String runtimeVersion;

  PackageValidation validate(OcrPackageManifest manifest) {
    final issues = <String>[];
    if (!manifest.isCompatibleSchema) {
      issues.add('Package schema v${manifest.schemaVersion} is not supported.');
    }
    if (manifest.packageId.isEmpty || manifest.version.isEmpty) {
      issues.add('The package identity is incomplete.');
    }
    if (!manifest.input.isSane) {
      issues.add('The model input dimensions are unsafe or unsupported.');
    }
    if (manifest.model.path.isEmpty ||
        manifest.model.bytes <= 0 ||
        !manifest.model.hasValidHash) {
      issues.add(
          'The model artifact requires a path, byte size, and SHA-256 checksum.');
    }
    if (manifest.alphabet.isEmpty) {
      issues.add('The package contains no alphabet mapping.');
    }
    if (manifest.alphabetArtifact.path.isEmpty) {
      issues.add('The alphabet artifact path is missing.');
    }
    final ids = manifest.alphabet.map((entry) => entry.id).toList();
    if (ids.toSet().length != ids.length) {
      issues.add('Alphabet class IDs must be unique.');
    }
    if (manifest.alphabet.any((entry) =>
        entry.id < 0 || entry.codePoint < 0 || entry.codePoint > 0x10FFFF)) {
      issues.add(
          'Alphabet mappings contain an invalid class ID or Unicode code point.');
    }
    if (manifest.alphabet.any((entry) => entry.label.runes.length != 1)) {
      issues.add(
          'Each alphabet entry must represent exactly one Unicode character.');
    }
    if (_isNewer(manifest.minimumRuntimeVersion, runtimeVersion)) {
      issues.add(
          'Package requires runtime ${manifest.minimumRuntimeVersion}; this runtime is $runtimeVersion.');
    }
    if (manifest.output.decoder != 'yolo_v8') {
      issues.add('Unsupported output decoder: ${manifest.output.decoder}.');
    }
    return issues.isEmpty
        ? const PackageValidation.valid()
        : PackageValidation.invalid(issues);
  }

  bool _isNewer(String required, String available) {
    List<int> parts(String value) => value
        .split('.')
        .map(
            (part) => int.tryParse(part.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0)
        .toList();
    final needed = parts(required);
    final current = parts(available);
    for (var index = 0; index < 3; index++) {
      final a = index < needed.length ? needed[index] : 0;
      final b = index < current.length ? current[index] : 0;
      if (a != b) return a > b;
    }
    return false;
  }
}
