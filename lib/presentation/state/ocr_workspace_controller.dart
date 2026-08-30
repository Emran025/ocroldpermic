import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../application/model_update.dart';
import '../../domain/entities/ocr_result.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';
import '../../domain/usecases/run_ocr.dart';
import '../../config/localization/workspace_messages.dart';
import '../../infrastructure/network/remote_image_loader.dart';
import '../../infrastructure/storage/ocr_result_exporter.dart';

enum OcrWorkspaceStatus {
  idle,
  loadingModels,
  checking,
  downloading,
  ready,
  running,
  completed,
  failed
}

class OcrWorkspaceController extends ChangeNotifier {
  OcrWorkspaceController({
    required this.models,
    required this.catalog,
    required this.runOcr,
    required this.remoteImages,
    required this.exporter,
    required this.updates,
  });

  final ModelRepository models;
  final ModelCatalog catalog;
  final RunOcr runOcr;
  final RemoteImageLoader remoteImages;
  final OcrResultExporter exporter;
  final ModelUpdateController updates;

  OcrWorkspaceStatus _status = OcrWorkspaceStatus.idle;
  OcrWorkspaceStatus get status => _status;
  WorkspaceMessage? _message;
  WorkspaceMessage? get message => _message;
  List<InstalledModel> _installedModels = const [];
  List<InstalledModel> get installedModels =>
      List.unmodifiable(_installedModels);
  InstalledModel? _activeModel;
  InstalledModel? get activeModel => _activeModel;
  String? _imagePath;
  String? get imagePath => _imagePath;
  OcrResult? _result;
  OcrResult? get result => _result;
  OcrRunConfiguration _configuration = const OcrRunConfiguration();
  OcrRunConfiguration get configuration => _configuration;
  double? _transferProgress;
  double? get transferProgress => _transferProgress;

  Future<void> initialize() async {
    _status = OcrWorkspaceStatus.loadingModels;
    _message = null;
    notifyListeners();
    try {
      await _reloadModels();
      _status = _activeModel == null
          ? OcrWorkspaceStatus.idle
          : OcrWorkspaceStatus.ready;
    } catch (_) {
      _fail(WorkspaceMessages.packagesLoad);
    }
    notifyListeners();
  }

  void setImage(String path) {
    _imagePath = path;
    _result = null;
    _message = null;
    if (_activeModel != null) _status = OcrWorkspaceStatus.ready;
    notifyListeners();
  }

  Future<void> fetchRemoteImage(String url) async {
    final uri = Uri.tryParse(url.trim());
    if (uri == null) {
      _fail(WorkspaceMessages.invalidImageUrl);
      return;
    }
    _status = OcrWorkspaceStatus.downloading;
    _message = WorkspaceMessages.downloadingImage;
    _transferProgress = null;
    notifyListeners();
    try {
      _imagePath =
          await remoteImages.download(uri, onProgress: (received, total) {
        _transferProgress = total <= 0 ? null : received / total;
        notifyListeners();
      });
      _result = null;
      _status = _activeModel == null
          ? OcrWorkspaceStatus.idle
          : OcrWorkspaceStatus.ready;
      _message = null;
    } catch (_) {
      _fail(WorkspaceMessages.imageDownloadFailed);
    }
    notifyListeners();
  }

  Future<void> installRemoteManifest(String source) async {
    final uri = Uri.tryParse(source.trim());
    if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
      _fail(WorkspaceMessages.invalidManifestUrl);
      return;
    }
    _status = OcrWorkspaceStatus.checking;
    _message = WorkspaceMessages.checkingPackage;
    notifyListeners();
    try {
      final manifest = await catalog.fetchManifest(uri);
      _status = OcrWorkspaceStatus.downloading;
      _message = WorkspaceMessages.downloadingPackage;
      _transferProgress = null;
      notifyListeners();
      await models.installFromManifest(
        manifest,
        source:
            ModelSource(kind: ModelSourceKind.remoteManifest, location: uri),
        onProgress: _onTransfer,
      );
      await _reloadModels();
      _status = OcrWorkspaceStatus.ready;
      _message = WorkspaceMessages.ready(manifest.displayName);
    } catch (_) {
      _fail(WorkspaceMessages.invalidRemotePackage);
    }
    notifyListeners();
  }

  Future<void> installRemotePackage(String source) async {
    final uri = Uri.tryParse(source.trim());
    if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
      _fail(WorkspaceMessages.invalidManifestUrl);
      return;
    }
    _status = OcrWorkspaceStatus.downloading;
    _message = WorkspaceMessages.downloadingPackage;
    _transferProgress = null;
    notifyListeners();
    try {
      final installed =
          await models.installFromPackageUrl(uri, onProgress: _onTransfer);
      await _reloadModels();
      _activeModel = _installedModels
          .where(
              (model) => model.manifest.identity == installed.manifest.identity)
          .firstOrNull;
      _status = OcrWorkspaceStatus.ready;
      _message = WorkspaceMessages.ready(installed.manifest.displayName);
    } catch (_) {
      _fail(WorkspaceMessages.invalidRemotePackage);
    }
    notifyListeners();
  }

  Future<void> importPackage(String path) async {
    if (!await File(path).exists()) {
      _fail(WorkspaceMessages.missingPackage);
      return;
    }
    _status = OcrWorkspaceStatus.downloading;
    _message = WorkspaceMessages.validatingPackage;
    _transferProgress = null;
    notifyListeners();
    try {
      final installed =
          await models.importPackage(path, onProgress: _onTransfer);
      await _reloadModels();
      _activeModel = _installedModels
          .where(
              (model) => model.manifest.identity == installed.manifest.identity)
          .firstOrNull;
      _status = OcrWorkspaceStatus.ready;
      _message = WorkspaceMessages.ready(installed.manifest.displayName);
    } catch (_) {
      _fail(WorkspaceMessages.invalidLocalPackage);
    }
    notifyListeners();
  }

  Future<void> selectModel(InstalledModel model) async {
    _status = OcrWorkspaceStatus.loadingModels;
    _message = WorkspaceMessages.activating(model.manifest.displayName);
    notifyListeners();
    try {
      await models.activate(model.manifest.packageId, model.manifest.version);
      await _reloadModels();
      _status = OcrWorkspaceStatus.ready;
      _message = null;
    } catch (_) {
      _fail(WorkspaceMessages.activationFailed);
    }
    notifyListeners();
  }

  Future<void> removeModel(InstalledModel model) async {
    try {
      await models.remove(model.manifest.packageId, model.manifest.version);
      await _reloadModels();
      _status = _activeModel == null
          ? OcrWorkspaceStatus.idle
          : OcrWorkspaceStatus.ready;
    } catch (_) {
      _fail(WorkspaceMessages.removeActiveFailed);
    }
    notifyListeners();
  }

  void updateConfiguration(
      {double? confidenceThreshold, double? iouThreshold, int? maxDetections}) {
    _configuration = OcrRunConfiguration(
      confidenceThreshold:
          confidenceThreshold ?? _configuration.confidenceThreshold,
      iouThreshold: iouThreshold ?? _configuration.iouThreshold,
      maxDetections: maxDetections ?? _configuration.maxDetections,
    );
    notifyListeners();
  }

  Future<void> run() async {
    final model = _activeModel;
    final image = _imagePath;
    if (model == null) {
      _fail(WorkspaceMessages.selectPackageFirst);
      return;
    }
    if (image == null) {
      _fail(WorkspaceMessages.selectImageFirst);
      return;
    }
    _status = OcrWorkspaceStatus.running;
    _message = WorkspaceMessages.ocrRunning;
    _result = null;
    notifyListeners();
    try {
      _result = await runOcr(
          imagePath: image, model: model, configuration: _configuration);
      _status = OcrWorkspaceStatus.completed;
      _message = _result!.orderedText.detections.isEmpty
          ? WorkspaceMessages.noGlyphs
          : null;
    } catch (_) {
      _fail(WorkspaceMessages.ocrFailed);
    }
    notifyListeners();
  }

  void editText(String value) {
    final current = _result;
    if (current == null) return;
    _result = current.copyWith(
        editedText: value, clearEditedText: value == current.rawText);
    notifyListeners();
  }

  Future<File?> export(OcrExportFormat format) async {
    final current = _result;
    if (current == null) return null;
    try {
      final file = await exporter.export(current, format);
      _message = WorkspaceMessages.exportCreated(file.path);
      notifyListeners();
      return file;
    } catch (_) {
      _fail(WorkspaceMessages.exportFailed);
      notifyListeners();
      return null;
    }
  }

  Future<void> checkForUpdate() async {
    _status = OcrWorkspaceStatus.checking;
    _message = WorkspaceMessages.checkingUpdates;
    notifyListeners();
    final update = await updates.check(manual: true);
    _status = _activeModel == null
        ? OcrWorkspaceStatus.idle
        : OcrWorkspaceStatus.ready;
    _message = switch (update) {
      UpdateOffline() => WorkspaceMessages.offline,
      UpdateUpToDate() => WorkspaceMessages.upToDate,
      UpdateAvailable(:final manifest) =>
        WorkspaceMessages.updateAvailable(manifest.version),
      UpdateActivated(:final model) =>
        WorkspaceMessages.updated(model.manifest.displayName),
      UpdateInstalling() => WorkspaceMessages.installingUpdate,
      UpdateChecking() => WorkspaceMessages.checkingUpdates,
      UpdateFailed(:final message) => WorkspaceMessages.raw(message),
    };
    notifyListeners();
  }

  Future<void> _reloadModels() async {
    _installedModels = await models.listInstalled();
    _activeModel =
        _installedModels.where((model) => model.isActive).firstOrNull;
  }

  void _onTransfer(ModelTransferProgress progress) {
    _transferProgress = progress.fraction;
    notifyListeners();
  }

  void _fail(WorkspaceMessage message) {
    _status = OcrWorkspaceStatus.failed;
    _message = message;
  }
}
