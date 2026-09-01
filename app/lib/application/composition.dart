import 'package:dio/dio.dart';

import '../core/api/api_consumer.dart';
import '../core/api/dio_consumer.dart';
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
    final dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 45),
      sendTimeout: const Duration(seconds: 45),
      followRedirects: true,
      maxRedirects: 3,
      headers: const {'Accept': 'application/json'},
    ));
    final api = DioConsumer(dio: dio);
    final models = AtomicModelStore(dio);
    final catalog = RemoteModelCatalog(api);
    final updates = ModelUpdateController(_NetworkStatus(api), catalog, models);
    return AppDependencies._(OcrWorkspaceController(
      models: models,
      catalog: catalog,
      runOcr: RunOcr(OnnxYoloInferenceEngine()),
      remoteImages: RemoteImageLoader(dio),
      exporter: OcrResultExporter(),
      updates: updates,
    ));
  }
}

class _NetworkStatus implements NetworkRepository {
  const _NetworkStatus(this.api);
  final ApiConsumer api;

  @override
  Future<bool> isOnline() async {
    try {
      await api.get('https://www.cloudflare.com/cdn-cgi/trace');
      return true;
    } catch (_) {
      return false;
    }
  }
}
