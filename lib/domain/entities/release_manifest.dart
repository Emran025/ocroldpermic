import 'dart:ui';

enum ModelFormat { onnx, tflite }

enum TensorLayout { nchw, nhwc }

enum YoloLayout { channelsFirst, predictionsFirst }

enum ReadingDirection { leftToRight, rightToLeft }

class ReleaseArtifact {
  const ReleaseArtifact({
    required this.id,
    required this.path,
    required this.bytes,
    required this.sha256,
    this.mediaType,
  });

  final String id;
  final String path;
  final int bytes;
  final String sha256;
  final String? mediaType;

  bool get hasValidHash => RegExp(r'^[a-fA-F0-9]{64}$').hasMatch(sha256);
}

/// Alphabet entries belong to the package, never to application source code.
class GlyphClass {
  const GlyphClass({
    required this.id,
    required this.codePoint,
    required this.label,
    this.name,
    this.display,
  });

  final int id;
  final int codePoint;
  final String label;
  final String? name;
  final String? display;

  String get unicode =>
      'U+${codePoint.toRadixString(16).toUpperCase().padLeft(4, '0')}';
}

class InputSpec {
  const InputSpec({
    required this.width,
    required this.height,
    this.layout = TensorLayout.nchw,
    this.channels = 3,
    this.normalization = 'zero_to_one',
    this.letterbox = true,
    this.padColor = 114,
  });

  final int width;
  final int height;
  final TensorLayout layout;
  final int channels;
  final String normalization;
  final bool letterbox;
  final int padColor;

  bool get isSane =>
      width > 0 &&
      width <= 4096 &&
      height > 0 &&
      height <= 4096 &&
      (channels == 1 || channels == 3 || channels == 4);
}

class OutputSpec {
  const OutputSpec({
    this.decoder = 'yolo_v8',
    this.layout = YoloLayout.channelsFirst,
    this.boxFormat = 'xywh',
    this.coordinates = 'pixels',
    this.hasObjectness = false,
  });

  final String decoder;
  final YoloLayout layout;
  final String boxFormat;
  final String coordinates;
  final bool hasObjectness;
}

/// The versioned, self-describing contract between model publishing and the app.
class OcrPackageManifest {
  const OcrPackageManifest({
    required this.schemaVersion,
    required this.packageId,
    required this.version,
    required this.modelVersion,
    required this.language,
    required this.script,
    required this.alphabetVersion,
    required this.minimumRuntimeVersion,
    required this.createdAtUtc,
    required this.modelFormat,
    required this.model,
    required this.alphabetArtifact,
    required this.alphabet,
    required this.input,
    required this.output,
    this.readingDirection = ReadingDirection.leftToRight,
    this.releaseSha256,
    this.sourceUri,
  });

  final int schemaVersion;
  final String packageId;
  final String version;
  final String modelVersion;
  final String language;
  final String script;
  final String alphabetVersion;
  final String minimumRuntimeVersion;
  final String createdAtUtc;
  final ModelFormat modelFormat;
  final ReleaseArtifact model;
  final ReleaseArtifact alphabetArtifact;
  final List<GlyphClass> alphabet;
  final InputSpec input;
  final OutputSpec output;
  final ReadingDirection readingDirection;
  final String? releaseSha256;
  final Uri? sourceUri;

  String get displayName =>
      language.trim().isEmpty ? script : '$language · $script';
  String get identity => '$packageId@$version';
  bool get isCompatibleSchema => schemaVersion == 1;
  GlyphClass? glyphForClass(int id) {
    for (final glyph in alphabet) {
      if (glyph.id == id) return glyph;
    }
    return null;
  }
}

class InstalledModel {
  const InstalledModel({
    required this.manifest,
    required this.installPath,
    required this.installedAt,
    required this.source,
    required this.isActive,
    this.lastUsedAt,
  });

  final OcrPackageManifest manifest;
  final String installPath;
  final DateTime installedAt;
  final String source;
  final bool isActive;
  final DateTime? lastUsedAt;

  String get modelPath => '$installPath/${_localArtifactPath(manifest.model)}';
  String get alphabetPath =>
      '$installPath/${_localArtifactPath(manifest.alphabetArtifact)}';

  String _localArtifactPath(ReleaseArtifact artifact) {
    final uri = Uri.tryParse(artifact.path);
    return uri != null && uri.hasScheme
        ? 'artifacts/${artifact.id}.bin'
        : artifact.path;
  }

  InstalledModel copyWith({bool? isActive, DateTime? lastUsedAt}) =>
      InstalledModel(
        manifest: manifest,
        installPath: installPath,
        installedAt: installedAt,
        source: source,
        isActive: isActive ?? this.isActive,
        lastUsedAt: lastUsedAt ?? this.lastUsedAt,
      );
}

class PackageValidation {
  const PackageValidation.valid() : problems = const [];
  const PackageValidation.invalid(this.problems);

  final List<String> problems;
  bool get isValid => problems.isEmpty;
}

class BoundingBox {
  const BoundingBox(
      {required this.left,
      required this.top,
      required this.right,
      required this.bottom});

  final double left;
  final double top;
  final double right;
  final double bottom;

  double get width => right - left;
  double get height => bottom - top;
  double get centerX => (left + right) / 2;
  double get centerY => (top + bottom) / 2;
  Rect get rect => Rect.fromLTRB(left, top, right, bottom);
}
