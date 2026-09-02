import 'package:dio/dio.dart';
import '../domain/repositories/ocr_ports.dart';
import '../infrastructure/network/github_release_repository.dart';
import '../infrastructure/storage/atomic_model_store.dart';
import 'model_update.dart';

class AppDependencies {
  AppDependencies._(this.updates, this.models);
  final ModelUpdateController updates;
  final ModelStore models;

  factory AppDependencies.create() {
    final dio = Dio(BaseOptions(connectTimeout: const Duration(seconds: 12), receiveTimeout: const Duration(seconds: 30)));
    final models = AtomicModelStore(dio);
    return AppDependencies._(ModelUpdateController(_NetworkStatus(), GithubReleaseRepository(dio), models), models);
  }
}

class _NetworkStatus implements NetworkRepository {
  @override
  Future<bool> isOnline() async {
    try {
      final response = await Dio().get<String>('https://raw.githubusercontent.com', options: Options(receiveTimeout: const Duration(seconds: 4)));
      return response.statusCode != null && response.statusCode! < 500;
    } catch (_) {
      return false;
    }
  }
}
