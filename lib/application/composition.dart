import 'package:dio/dio.dart';

import '../domain/repositories/ocr_ports.dart';
import '../domain/usecases/run_ocr.dart';
import '../infrastructure/inference/onnx_yolo_inference.dart';
import '../infrastructure/network/github_release_repository.dart';
import '../infrastructure/network/remote_image_loader.dart';
import '../infrastructure/storage/atomic_model_store.dart';
import '../infrastructure/storage/ocr_result_exporter.dart';
import '../presentation/state/ocr_workspace_controller.dart';
import 'model_update.dart';

class AppDependencies {
  AppDependencies._(this.workspace);

  final OcrWorkspaceController workspace;

  factory AppDependencies.create() {
    final client = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 45),
      followRedirects: true,
      maxRedirects: 3,
    ));
    final models = AtomicModelStore(client);
    final catalog = RemoteModelCatalog(client);
    final updates =
        ModelUpdateController(_NetworkStatus(client), catalog, models);
    return AppDependencies._(OcrWorkspaceController(
      models: models,
      catalog: catalog,
      runOcr: RunOcr(OnnxYoloInferenceEngine()),
      remoteImages: RemoteImageLoader(client),
      exporter: OcrResultExporter(),
      updates: updates,
    ));
  }
}

class _NetworkStatus implements NetworkRepository {
  const _NetworkStatus(this.client);

  final Dio client;

  @override
  Future<bool> isOnline() async {
    try {
      final response =
          await client.head<void>('https://www.cloudflare.com/cdn-cgi/trace');
      return response.statusCode != null && response.statusCode! < 500;
    } catch (_) {
      return false;
    }
  }
}
