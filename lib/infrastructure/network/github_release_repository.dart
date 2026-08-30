import 'dart:convert';

import '../../core/api/api_consumer.dart';

import '../../data/models/ocr_package_manifest_model.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';

/// Generic HTTP manifest catalog. GitHub Releases can host these files, but the
/// domain layer remains independent of GitHub-specific APIs and URLs.
class RemoteModelCatalog implements ModelCatalog {
  RemoteModelCatalog(this.api, {this.validator = const ManifestValidator()});

  final ApiConsumer api;
  final ManifestValidator validator;

  @override
  Future<OcrPackageManifest> fetchManifest(Uri source) async {
    if (source.scheme != 'https' && source.scheme != 'http') {
      throw const FormatException(
          'Only HTTPS, HTTP, and local manifest sources are supported.');
    }
    final response = await api.get(source.toString());
    if (response == null) {
      throw const FormatException('The model manifest could not be retrieved.');
    }
    final raw = response is String ? response : jsonEncode(response);
    final manifest =
        OcrPackageManifestModel.fromJsonString(raw, sourceUri: source);
    final validation = validator.validate(manifest);
    if (!validation.isValid) {
      throw FormatException(validation.problems.join(' '));
    }
    return manifest;
  }

  @override
  Future<OcrPackageManifest?> checkForUpdate(InstalledModel installed) async {
    final source = installed.manifest.sourceUri;
    if (source == null ||
        (source.scheme != 'https' && source.scheme != 'http')) {
      return null;
    }
    final remote = await fetchManifest(source);
    if (remote.packageId != installed.manifest.packageId) {
      throw const FormatException(
          'The update source returned a different package identity.');
    }
    return _compareVersions(remote.version, installed.manifest.version) > 0
        ? remote
        : null;
  }

  static Uri resolveArtifact(Uri manifestUri, String artifactPath) {
    final artifactUri = Uri.tryParse(artifactPath);
    if (artifactUri != null && artifactUri.hasScheme) return artifactUri;
    return manifestUri.resolve(artifactPath);
  }

  int _compareVersions(String a, String b) {
    List<int> values(String version) => version
        .split(RegExp(r'[.+-]'))
        .map(
            (part) => int.tryParse(part.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0)
        .toList();
    final left = values(a);
    final right = values(b);
    final count = left.length > right.length ? left.length : right.length;
    for (var index = 0; index < count; index++) {
      final first = index < left.length ? left[index] : 0;
      final second = index < right.length ? right[index] : 0;
      if (first != second) return first.compareTo(second);
    }
    return 0;
  }
}
