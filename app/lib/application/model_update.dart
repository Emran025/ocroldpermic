import '../domain/entities/release_manifest.dart';
import '../domain/repositories/ocr_ports.dart';

sealed class UpdateState {
  const UpdateState();
}

class UpdateOffline extends UpdateState {
  const UpdateOffline();
}

class UpdateChecking extends UpdateState {
  const UpdateChecking();
}

class UpdateUpToDate extends UpdateState {
  const UpdateUpToDate(this.model);
  final InstalledModel model;
}

class UpdateAvailable extends UpdateState {
  const UpdateAvailable(this.manifest);
  final OcrPackageManifest manifest;
}

class UpdateInstalling extends UpdateState {
  const UpdateInstalling(this.progress);
  final ModelTransferProgress progress;
}

class UpdateActivated extends UpdateState {
  const UpdateActivated(this.model);
  final InstalledModel model;
}

class UpdateFailed extends UpdateState {
  const UpdateFailed(this.message);
  final String message;
}

/// Keeps update discovery separate from installation. A failed candidate never
/// replaces the model currently pointed to by the local repository.
class ModelUpdateController {
  ModelUpdateController(this.network, this.catalog, this.models,
      {DateTime Function()? clock})
      : _clock = clock ?? DateTime.now;

  static const interval = Duration(minutes: 10);
  final NetworkRepository network;
  final ModelCatalog catalog;
  final ModelRepository models;
  final DateTime Function() _clock;
  DateTime? _lastAutomaticCheck;
  Future<UpdateState>? _inFlight;
  OcrPackageManifest? _pending;

  Future<UpdateState> check({bool manual = false}) {
    if (_inFlight != null) return _inFlight!;
    final now = _clock();
    if (!manual &&
        _lastAutomaticCheck != null &&
        now.difference(_lastAutomaticCheck!) < interval) {
      return Future.value(const UpdateFailed(
          'Automatic check is deferred until the next check window.'));
    }
    _lastAutomaticCheck = now;
    final operation = _check();
    _inFlight = operation;
    operation.whenComplete(() => _inFlight = null);
    return operation;
  }

  Future<UpdateState> _check() async {
    if (!await network.isOnline()) return const UpdateOffline();
    try {
      final current = await models.active();
      if (current == null) {
        return const UpdateFailed('No active OCR package is installed.');
      }
      final available = await catalog.checkForUpdate(current);
      if (available == null ||
          available.identity == current.manifest.identity) {
        return UpdateUpToDate(current);
      }
      _pending = available;
      return UpdateAvailable(available);
    } catch (_) {
      return const UpdateFailed('Could not check for package updates.');
    }
  }

  Future<UpdateState> installPending(
      {void Function(ModelTransferProgress progress)? onProgress}) async {
    final manifest = _pending;
    if (manifest == null || manifest.sourceUri == null) {
      return const UpdateFailed(
          'There is no verified update ready to install.');
    }
    try {
      final model = await models.installFromManifest(
        manifest,
        source: ModelSource(
            kind: ModelSourceKind.remoteManifest,
            location: manifest.sourceUri!),
        onProgress: onProgress,
      );
      _pending = null;
      return UpdateActivated(model);
    } catch (_) {
      return const UpdateFailed(
          'The update could not be installed. The current model remains active.');
    }
  }
}
