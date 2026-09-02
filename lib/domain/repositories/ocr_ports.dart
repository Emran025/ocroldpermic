import '../entities/ocr_result.dart';
import '../entities/release_manifest.dart';

abstract interface class ReleaseRepository {
  Future<ReleaseManifest> fetchLatest();
}

abstract interface class ModelStore {
  Future<ActiveModel?> active();
  Future<ActiveModel> stageAndActivate(ReleaseManifest release);
}

abstract interface class NetworkRepository {
  Future<bool> isOnline();
}

abstract interface class OcrInference {
  Future<List<GlyphDetection>> infer(String imagePath, ActiveModel model);
}
