import 'dart:convert';
import 'dart:io';

import 'package:archive/archive_io.dart';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../../data/models/ocr_package_manifest_model.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';
import '../network/github_release_repository.dart';

/// File-backed package repository with candidate installation and an atomic
/// active pointer. Corrupt downloads cannot replace an existing active model.
class AtomicModelStore implements ModelRepository {
  AtomicModelStore(this.client, {this.validator = const ManifestValidator()});

  static const _activePointer = 'active_package.json';
  static const _recordName = 'installation.json';
  static const _maximumArchiveBytes = 1024 * 1024 * 1024;
  static const _maximumExtractedBytes = 1024 * 1024 * 1024;
  static const _zeroHash =
      '0000000000000000000000000000000000000000000000000000000000000000';

  final Dio client;
  final ManifestValidator validator;

  Future<Directory> get _root async {
    final directory = await getApplicationSupportDirectory();
    return Directory('${directory.path}/ocr_packages');
  }

  @override
  Future<List<InstalledModel>> listInstalled() async {
    final root = await _root;
    if (!await root.exists()) return const [];
    final activeIdentity = await _readActiveIdentity(root);
    final installed = <InstalledModel>[];
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File || !entity.path.endsWith('/$_recordName')) continue;
      try {
        final record =
            jsonDecode(await entity.readAsString()) as Map<String, dynamic>;
        final manifest = OcrPackageManifestModel.fromJson(
          Map<String, dynamic>.from(record['manifest'] as Map),
          sourceUri: _parseUri(record['source_uri']),
        );
        final installPath = entity.parent.path;
        if (!await File('$installPath/${_storedArtifactPath(manifest.model)}')
            .exists()) {
          continue;
        }
        installed.add(InstalledModel(
          manifest: manifest,
          installPath: installPath,
          installedAt:
              DateTime.tryParse(record['installed_at']?.toString() ?? '')
                      ?.toUtc() ??
                  DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
          source: record['source']?.toString() ?? 'unknown',
          isActive: activeIdentity == manifest.identity,
          lastUsedAt:
              DateTime.tryParse(record['last_used_at']?.toString() ?? '')
                  ?.toUtc(),
        ));
      } catch (_) {
        // Ignore incomplete and unreadable records; they never become active.
      }
    }
    installed.sort((a, b) => b.installedAt.compareTo(a.installedAt));
    return installed;
  }

  @override
  Future<InstalledModel?> active() async {
    final root = await _root;
    final identity = await _readActiveIdentity(root);
    if (identity == null) return null;
    final installed = await listInstalled();
    for (final item in installed) {
      if (item.manifest.identity == identity) return item;
    }
    return null;
  }

  @override
  Future<InstalledModel> installFromManifest(
    OcrPackageManifest manifest, {
    required ModelSource source,
    void Function(ModelTransferProgress progress)? onProgress,
  }) async {
    final validation = validator.validate(manifest);
    if (!validation.isValid) {
      throw FormatException(validation.problems.join(' '));
    }
    if (source.kind != ModelSourceKind.remoteManifest &&
        source.kind != ModelSourceKind.bundled) {
      throw const FormatException(
          'This source cannot install a manifest directly.');
    }

    final root = await _root;
    await root.create(recursive: true);
    final candidate = await _newCandidate(root, manifest);
    try {
      onProgress?.call(const ModelTransferProgress(
          phase: 'downloading_model', message: 'Downloading model artifact'));
      final manifestUri = manifest.sourceUri ?? source.location;
      await _downloadArtifact(
          manifest.model, manifestUri, candidate, onProgress);
      if (manifest.alphabetArtifact.bytes > 0 &&
          manifest.alphabetArtifact.sha256 != _zeroHash) {
        onProgress?.call(const ModelTransferProgress(
            phase: 'downloading_alphabet',
            message: 'Downloading alphabet artifact'));
        await _downloadArtifact(
            manifest.alphabetArtifact, manifestUri, candidate, onProgress);
      }
      await File('${candidate.path}/manifest.json')
          .writeAsString(jsonEncode(_manifestJson(manifest)));
      return await _commitCandidate(candidate, manifest,
          source: source.label ?? source.location.toString(),
          sourceUri: manifestUri);
    } catch (_) {
      await _deleteQuietly(candidate);
      rethrow;
    }
  }

  @override
  Future<InstalledModel> importPackage(
    String archivePath, {
    void Function(ModelTransferProgress progress)? onProgress,
  }) async {
    final archiveFile = File(archivePath);
    return _importArchiveFile(archiveFile,
        sourceUri: archiveFile.uri, onProgress: onProgress);
  }

  @override
  Future<InstalledModel> installFromPackageUrl(
    Uri packageUrl, {
    void Function(ModelTransferProgress progress)? onProgress,
  }) async {
    if (packageUrl.scheme != 'https' && packageUrl.scheme != 'http') {
      throw const FormatException('Remote packages must use HTTP(S).');
    }
    final root = await _root;
    final downloads = Directory('${root.path}/.downloads');
    await downloads.create(recursive: true);
    final staged = File(
        '${downloads.path}/package-${DateTime.now().microsecondsSinceEpoch}.ocrpkg.part');
    final cancel = CancelToken();
    try {
      await client.download(
        packageUrl.toString(),
        staged.path,
        deleteOnError: true,
        cancelToken: cancel,
        onReceiveProgress: (received, total) {
          if (received > _maximumArchiveBytes) {
            cancel.cancel('Package exceeds safety limit.');
          }
          onProgress?.call(ModelTransferProgress(
            phase: 'downloading_package',
            receivedBytes: received,
            totalBytes: total > 0 ? total : null,
            message: 'Downloading OCR package',
          ));
        },
      );
      return await _importArchiveFile(staged,
          sourceUri: packageUrl, onProgress: onProgress);
    } finally {
      if (await staged.exists()) await staged.delete();
    }
  }

  Future<InstalledModel> _importArchiveFile(
    File archiveFile, {
    required Uri sourceUri,
    void Function(ModelTransferProgress progress)? onProgress,
  }) async {
    if (!await archiveFile.exists()) {
      throw const FormatException(
          'The selected package file no longer exists.');
    }
    if (await archiveFile.length() > _maximumArchiveBytes) {
      throw const FormatException('The package exceeds the 1 GB safety limit.');
    }

    final root = await _root;
    await root.create(recursive: true);
    final provisional = await _newCandidate(root, null);
    try {
      onProgress?.call(const ModelTransferProgress(
          phase: 'validating_package', message: 'Validating package archive'));
      final archive = ZipDecoder()
          .decodeBytes(await archiveFile.readAsBytes(), verify: true);
      var total = 0;
      for (final entry in archive.files) {
        if (!_isSafeRelativePath(entry.name)) {
          throw const FormatException(
              'The package contains an unsafe file path.');
        }
        if (!entry.isFile) continue;
        total += entry.size;
        if (total > _maximumExtractedBytes) {
          throw const FormatException(
              'The extracted package exceeds the 1 GB safety limit.');
        }
        final output = File('${provisional.path}/${entry.name}');
        await output.parent.create(recursive: true);
        await output.writeAsBytes(entry.content as List<int>, flush: true);
      }
      final manifestFile = File('${provisional.path}/manifest.json');
      if (!await manifestFile.exists()) {
        throw const FormatException(
            'An OCR package must include manifest.json at its root.');
      }
      final manifest = OcrPackageManifestModel.fromJsonString(
          await manifestFile.readAsString());
      final validation = validator.validate(manifest);
      if (!validation.isValid) {
        throw FormatException(validation.problems.join(' '));
      }
      await _verifyCandidateArtifacts(provisional, manifest);
      return await _commitCandidate(
        provisional,
        manifest,
        source: sourceUri.toString(),
        sourceUri: sourceUri,
      );
    } catch (_) {
      await _deleteQuietly(provisional);
      rethrow;
    }
  }

  @override
  Future<InstalledModel> activate(String packageId, String version) async {
    final installed = await listInstalled();
    final selected = installed
        .where((item) =>
            item.manifest.packageId == packageId &&
            item.manifest.version == version)
        .toList();
    if (selected.isEmpty) {
      throw const FormatException(
          'The requested OCR package is not installed.');
    }
    final candidate = selected.first;
    await _verifyCandidateArtifacts(
        Directory(candidate.installPath), candidate.manifest);
    final root = await _root;
    await _writeActiveIdentity(root, candidate.manifest.identity);
    return candidate.copyWith(isActive: true);
  }

  @override
  Future<void> remove(String packageId, String version) async {
    final activeModel = await active();
    if (activeModel?.manifest.packageId == packageId &&
        activeModel?.manifest.version == version) {
      throw const FormatException(
          'Install and activate a replacement before removing the active OCR package.');
    }
    final root = await _root;
    final directory = Directory(
        '${root.path}/${_safeSegment(packageId)}/${_safeSegment(version)}');
    if (await directory.exists()) await directory.delete(recursive: true);
  }

  Future<Directory> _newCandidate(
      Directory root, OcrPackageManifest? manifest) async {
    final stamp = DateTime.now().microsecondsSinceEpoch;
    final name = manifest == null
        ? 'import-$stamp'
        : '${_safeSegment(manifest.packageId)}-${_safeSegment(manifest.version)}-$stamp';
    final candidate = Directory('${root.path}/.candidates/$name');
    await candidate.create(recursive: true);
    return candidate;
  }

  Future<void> _downloadArtifact(
    ReleaseArtifact artifact,
    Uri manifestUri,
    Directory candidate,
    void Function(ModelTransferProgress progress)? progress,
  ) async {
    if (!_isSafeRelativePath(artifact.path) &&
        Uri.tryParse(artifact.path)?.hasScheme != true) {
      throw const FormatException('The artifact path is unsafe.');
    }
    final uri = RemoteModelCatalog.resolveArtifact(manifestUri, artifact.path);
    if (uri.scheme != 'https' && uri.scheme != 'http') {
      throw const FormatException('Remote artifacts must use HTTP(S).');
    }
    final relativePath = Uri.tryParse(artifact.path)?.hasScheme == true
        ? '${artifact.id}.bin'
        : artifact.path;
    final target = File('${candidate.path}/$relativePath');
    await target.parent.create(recursive: true);
    final staged = File('${target.path}.part');
    await client.download(
      uri.toString(),
      staged.path,
      deleteOnError: true,
      onReceiveProgress: (received, total) =>
          progress?.call(ModelTransferProgress(
        phase: 'downloading_${artifact.id}',
        receivedBytes: received,
        totalBytes: total > 0 ? total : null,
        message: 'Downloading ${artifact.id}',
      )),
    );
    await _verifyArtifact(staged, artifact, requireSize: true);
    await staged.rename(target.path);
  }

  Future<void> _verifyCandidateArtifacts(
      Directory directory, OcrPackageManifest manifest) async {
    final model =
        File('${directory.path}/${_storedArtifactPath(manifest.model)}');
    await _verifyArtifact(model, manifest.model, requireSize: true);
    final alphabet = File(
        '${directory.path}/${_storedArtifactPath(manifest.alphabetArtifact)}');
    if (manifest.alphabetArtifact.bytes > 0 ||
        manifest.alphabetArtifact.sha256 != _zeroHash) {
      await _verifyArtifact(alphabet, manifest.alphabetArtifact,
          requireSize: manifest.alphabetArtifact.bytes > 0);
    }
  }

  Future<void> _verifyArtifact(File file, ReleaseArtifact artifact,
      {required bool requireSize}) async {
    if (!await file.exists()) {
      throw FormatException('Required artifact ${artifact.id} is missing.');
    }
    final actualBytes = await file.length();
    if (requireSize && actualBytes != artifact.bytes) {
      throw FormatException(
          'Artifact ${artifact.id} has an unexpected file size.');
    }
    if (artifact.sha256 != _zeroHash) {
      final actualHash = sha256.convert(await file.readAsBytes()).toString();
      if (actualHash.toLowerCase() != artifact.sha256.toLowerCase()) {
        throw FormatException(
            'Artifact ${artifact.id} failed its SHA-256 integrity check.');
      }
    }
  }

  Future<InstalledModel> _commitCandidate(
    Directory candidate,
    OcrPackageManifest manifest, {
    required String source,
    required Uri sourceUri,
  }) async {
    final root = await _root;
    final target = Directory(
        '${root.path}/${_safeSegment(manifest.packageId)}/${_safeSegment(manifest.version)}');
    if (await target.exists()) {
      await _deleteQuietly(candidate);
    } else {
      await target.parent.create(recursive: true);
      await candidate.rename(target.path);
    }
    final record = File('${target.path}/$_recordName');
    final now = DateTime.now().toUtc();
    await record.writeAsString(
        jsonEncode({
          'installed_at': now.toIso8601String(),
          'source': source,
          'source_uri': sourceUri.toString(),
          'manifest': _manifestJson(manifest),
        }),
        flush: true);
    await _writeActiveIdentity(root, manifest.identity);
    return InstalledModel(
      manifest: manifest,
      installPath: target.path,
      installedAt: now,
      source: source,
      isActive: true,
    );
  }

  Future<String?> _readActiveIdentity(Directory root) async {
    final pointer = File('${root.path}/$_activePointer');
    if (!await pointer.exists()) return null;
    try {
      final json =
          jsonDecode(await pointer.readAsString()) as Map<String, dynamic>;
      return json['identity']?.toString();
    } catch (_) {
      return null;
    }
  }

  Future<void> _writeActiveIdentity(Directory root, String identity) async {
    await root.create(recursive: true);
    final pointer = File('${root.path}/$_activePointer');
    final staged = File('${root.path}/.$_activePointer.tmp');
    await staged.writeAsString(
        jsonEncode({
          'identity': identity,
          'activated_at': DateTime.now().toUtc().toIso8601String()
        }),
        flush: true);
    if (await pointer.exists()) await pointer.delete();
    await staged.rename(pointer.path);
  }

  Map<String, dynamic> _manifestJson(OcrPackageManifest manifest) => {
        'schema_version': manifest.schemaVersion,
        'package_id': manifest.packageId,
        'version': manifest.version,
        'model_version': manifest.modelVersion,
        'language': manifest.language,
        'script': manifest.script,
        'alphabet_version': manifest.alphabetVersion,
        'minimum_runtime_version': manifest.minimumRuntimeVersion,
        'created_at': manifest.createdAtUtc,
        'model_format': manifest.modelFormat.name,
        'reading_direction':
            manifest.readingDirection == ReadingDirection.rightToLeft
                ? 'rtl'
                : 'ltr',
        'model': _artifactJson(manifest.model),
        'alphabet': {
          'version': manifest.alphabetVersion,
          'artifact': _artifactJson(manifest.alphabetArtifact),
          'classes': manifest.alphabet
              .map((entry) => {
                    'id': entry.id,
                    'unicode': entry.unicode,
                    'character': entry.label,
                    if (entry.name != null) 'name': entry.name,
                    if (entry.display != null) 'display': entry.display,
                  })
              .toList(),
        },
        'input': {
          'width': manifest.input.width,
          'height': manifest.input.height,
          'layout': manifest.input.layout.name,
          'channels': manifest.input.channels,
          'normalization': manifest.input.normalization,
          'letterbox': manifest.input.letterbox,
          'pad_color': manifest.input.padColor,
        },
        'output': {
          'decoder': manifest.output.decoder,
          'layout': manifest.output.layout == YoloLayout.predictionsFirst
              ? 'predictions_first'
              : 'channels_first',
          'box_format': manifest.output.boxFormat,
          'coordinates': manifest.output.coordinates,
          'has_objectness': manifest.output.hasObjectness,
        },
        if (manifest.releaseSha256 != null)
          'release_sha256': manifest.releaseSha256,
      };

  Map<String, dynamic> _artifactJson(ReleaseArtifact artifact) => {
        'id': artifact.id,
        'path': artifact.path,
        'bytes': artifact.bytes,
        'sha256': artifact.sha256,
        if (artifact.mediaType != null) 'media_type': artifact.mediaType,
      };

  bool _isSafeRelativePath(String path) {
    if (path.isEmpty ||
        path.startsWith('/') ||
        path.startsWith('\\') ||
        path.contains('\\')) {
      return false;
    }
    return path.split('/').every(
        (segment) => segment.isNotEmpty && segment != '.' && segment != '..');
  }

  String _storedArtifactPath(ReleaseArtifact artifact) {
    final uri = Uri.tryParse(artifact.path);
    return uri != null && uri.hasScheme
        ? 'artifacts/${artifact.id}.bin'
        : artifact.path;
  }

  String _safeSegment(String value) =>
      value.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');

  Uri? _parseUri(dynamic value) =>
      value == null ? null : Uri.tryParse(value.toString());

  Future<void> _deleteQuietly(Directory directory) async {
    try {
      if (await directory.exists()) await directory.delete(recursive: true);
    } catch (_) {
      // Best-effort cleanup only; the pointer remains untouched.
    }
  }
}
