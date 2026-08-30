import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../application/model_update.dart';
import '../../domain/entities/ocr_result.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';
import '../../domain/usecases/run_ocr.dart';
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
  String? _message;
  String? get message => _message;
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
      _fail('Installed OCR packages could not be loaded.');
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
      _fail('Enter a valid image URL.');
      return;
    }
    _status = OcrWorkspaceStatus.downloading;
    _message = 'Downloading image…';
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
      _fail('The image URL could not be downloaded or decoded.');
    }
    notifyListeners();
  }

  Future<void> installRemoteManifest(String source) async {
    final uri = Uri.tryParse(source.trim());
    if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
      _fail('Enter a valid HTTP(S) package manifest URL.');
      return;
    }
    _status = OcrWorkspaceStatus.checking;
    _message = 'Checking OCR package…';
    notifyListeners();
    try {
      final manifest = await catalog.fetchManifest(uri);
      _status = OcrWorkspaceStatus.downloading;
      _message = 'Downloading ${manifest.displayName}…';
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
      _message = '${manifest.displayName} is ready for offline OCR.';
    } catch (_) {
      _fail(
          'The OCR package is invalid, incompatible, or could not be installed.');
    }
    notifyListeners();
  }

  Future<void> installRemotePackage(String source) async {
    final uri = Uri.tryParse(source.trim());
    if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
      _fail('Enter a valid HTTP(S) OCR package URL.');
      return;
    }
    _status = OcrWorkspaceStatus.downloading;
    _message = 'Downloading OCR package…';
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
      _message = '${installed.manifest.displayName} is ready for offline OCR.';
    } catch (_) {
      _fail(
          'The remote OCR package is invalid, unsafe, or could not be installed.');
    }
    notifyListeners();
  }

  Future<void> importPackage(String path) async {
    if (!await File(path).exists()) {
      _fail('The selected OCR package is no longer available.');
      return;
    }
    _status = OcrWorkspaceStatus.downloading;
    _message = 'Validating local OCR package…';
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
      _message = '${installed.manifest.displayName} is ready for offline OCR.';
    } catch (_) {
      _fail('The local OCR package is invalid, unsafe, or incompatible.');
    }
    notifyListeners();
  }

  Future<void> selectModel(InstalledModel model) async {
    _status = OcrWorkspaceStatus.loadingModels;
    _message = 'Activating ${model.manifest.displayName}…';
    notifyListeners();
    try {
      await models.activate(model.manifest.packageId, model.manifest.version);
      await _reloadModels();
      _status = OcrWorkspaceStatus.ready;
      _message = null;
    } catch (_) {
      _fail('This OCR package could not be activated.');
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
      _fail(
          'The active OCR package cannot be removed. Activate a replacement first.');
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
      _fail('Install or select an OCR package before running OCR.');
      return;
    }
    if (image == null) {
      _fail('Select, capture, or download an image before running OCR.');
      return;
    }
    _status = OcrWorkspaceStatus.running;
    _message = 'Running on-device OCR…';
    _result = null;
    notifyListeners();
    try {
      _result = await runOcr(
          imagePath: image, model: model, configuration: _configuration);
      _status = OcrWorkspaceStatus.completed;
      _message = _result!.orderedText.detections.isEmpty
          ? 'No glyphs met the current confidence threshold.'
          : null;
    } catch (_) {
      _fail(
          'OCR could not be completed. Check the image and selected model package.');
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
      _message = 'Export created: ${file.path}';
      notifyListeners();
      return file;
    } catch (_) {
      _fail('The OCR result could not be exported.');
      notifyListeners();
      return null;
    }
  }

  Future<void> checkForUpdate() async {
    _status = OcrWorkspaceStatus.checking;
    _message = 'Checking for package updates…';
    notifyListeners();
    final update = await updates.check(manual: true);
    _status = _activeModel == null
        ? OcrWorkspaceStatus.idle
        : OcrWorkspaceStatus.ready;
    _message = switch (update) {
      UpdateOffline() => 'Offline. Installed OCR packages remain available.',
      UpdateUpToDate() => 'The active OCR package is up to date.',
      UpdateAvailable(:final manifest) =>
        'Update available: ${manifest.version}. Open the package manager to install it.',
      UpdateActivated(:final model) =>
        '${model.manifest.displayName} updated successfully.',
      UpdateInstalling() => 'Installing package update…',
      UpdateChecking() => 'Checking for package updates…',
      UpdateFailed(:final message) => message,
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
    _message = progress.message ?? _message;
    notifyListeners();
  }

  void _fail(String message) {
    _status = OcrWorkspaceStatus.failed;
    _message = message;
  }
}
