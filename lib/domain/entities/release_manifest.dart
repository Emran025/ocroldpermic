class ReleaseArtifact {
  const ReleaseArtifact({required this.path, required this.bytes, required this.sha256});
  final String path;
  final int bytes;
  final String sha256;
}

class GlyphClass {
  const GlyphClass({required this.id, required this.codePoint, required this.label});
  final int id;
  final int codePoint;
  final String label;
}

class ReleaseManifest {
  const ReleaseManifest({
    required this.releaseId,
    required this.createdAtUtc,
    required this.modelScope,
    required this.releaseSha256,
    required this.onnx,
    required this.classMap,
  });

  final String releaseId;
  final String createdAtUtc;
  final String modelScope;
  final String releaseSha256;
  final ReleaseArtifact onnx;
  final List<GlyphClass> classMap;

  bool get isOldPermicContract =>
      modelScope.contains('old-permic') && classMap.length == 38 &&
      classMap.every((glyph) => glyph.codePoint >= 0x10350 && glyph.codePoint <= 0x10375);
}

class ActiveModel {
  const ActiveModel({required this.release, required this.localPath});
  final ReleaseManifest release;
  final String localPath;
}
