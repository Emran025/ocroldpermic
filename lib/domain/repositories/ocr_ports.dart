import '../entities/ocr_result.dart';
import '../entities/release_manifest.dart';

enum ModelSourceKind { remoteManifest, remotePackage, localPackage, bundled }

class ModelSource {
  const ModelSource({required this.kind, required this.location, this.label});

  final ModelSourceKind kind;
  final Uri location;
  final String? label;
}

class ModelTransferProgress {
  const ModelTransferProgress({
    required this.phase,
    this.receivedBytes = 0,
    this.totalBytes,
    this.message,
  });

  final String phase;
  final int receivedBytes;
  final int? totalBytes;
  final String? message;

  double? get fraction => totalBytes == null || totalBytes == 0
      ? null
      : receivedBytes / totalBytes!;
}

abstract interface class ModelCatalog {
  Future<OcrPackageManifest> fetchManifest(Uri source);
  Future<OcrPackageManifest?> checkForUpdate(InstalledModel installed);
}

abstract interface class ModelRepository {
  Future<List<InstalledModel>> listInstalled();
  Future<InstalledModel?> active();
  Future<InstalledModel> installFromManifest(
    OcrPackageManifest manifest, {
    required ModelSource source,
    void Function(ModelTransferProgress progress)? onProgress,
  });
  Future<InstalledModel> importPackage(
    String archivePath, {
    void Function(ModelTransferProgress progress)? onProgress,
  });
  Future<InstalledModel> installFromPackageUrl(
    Uri packageUrl, {
    void Function(ModelTransferProgress progress)? onProgress,
  });
  Future<InstalledModel> activate(String packageId, String version);
  Future<void> remove(String packageId, String version);
}

abstract interface class NetworkRepository {
  Future<bool> isOnline();
}

class InferenceOutput {
  const InferenceOutput({
    required this.detections,
    required this.elapsed,
    required this.imageWidth,
    required this.imageHeight,
  });

  final List<GlyphDetection> detections;
  final Duration elapsed;
  final int imageWidth;
  final int imageHeight;
}

abstract interface class OcrInference {
  Future<InferenceOutput> infer(
    String imagePath,
    InstalledModel model,
    OcrRunConfiguration configuration,
  );
}
