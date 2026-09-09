import 'dart:io';

import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../domain/entities/release_manifest.dart';
import '../domain/repositories/ocr_ports.dart';

/// Installs the OCR package shipped as a Flutter asset on first launch.
///
/// The asset is optional for development, but release builds are expected to
/// provide `assets/models/default.ocrpkg`. Once installed, inference remains
/// fully local and does not need a network connection or credentials.
class BundledModelInstaller {
  const BundledModelInstaller({this.assetKey = 'assets/models/default.ocrpkg'});

  final String assetKey;

  Future<InstalledModel?> installIfPresent(ModelRepository models) async {
    if (await models.active() != null) return null;

    ByteData bytes;
    try {
      bytes = await rootBundle.load(assetKey);
    } on FlutterError {
      return null;
    }

    final temporaryDirectory = await getTemporaryDirectory();
    final package = File(
        '${temporaryDirectory.path}/bundled-${DateTime.now().microsecondsSinceEpoch}.ocrpkg');
    try {
      await package.writeAsBytes(
          bytes.buffer.asUint8List(bytes.offsetInBytes, bytes.lengthInBytes),
          flush: true);
      return await models.importPackage(package.path);
    } finally {
      if (await package.exists()) await package.delete();
    }
  }
}
