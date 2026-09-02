import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';

class AtomicModelStore implements ModelStore {
  AtomicModelStore(this.client);
  final Dio client;
  static const pointerName = 'active_model.json';

  Future<Directory> get _root async => getApplicationSupportDirectory();

  @override
  Future<ActiveModel?> active() async {
    final root = await _root;
    final pointer = File('${root.path}/$pointerName');
    if (!await pointer.exists()) return null;
    try {
      final json = jsonDecode(await pointer.readAsString()) as Map<String, dynamic>;
      final release = _manifest(json['release'] as Map<String, dynamic>);
      final path = json['local_path'] as String;
      if (!await File(path).exists()) return null;
      return ActiveModel(release: release, localPath: path);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<ActiveModel> stageAndActivate(ReleaseManifest release) async {
    final root = await _root;
    await root.create(recursive: true);
    final staged = File('${root.path}/.${release.releaseId}.part');
    final target = File('${root.path}/${release.releaseId}.onnx');
    await client.download(release.onnx.path, staged.path, deleteOnError: true);
    if (await staged.length() != release.onnx.bytes) throw const FormatException('حجم وزن ONNX غير مطابق.');
    final digest = sha256.convert(await staged.readAsBytes()).toString();
    if (digest != release.onnx.sha256) throw const FormatException('بصمة وزن ONNX غير مطابقة.');
    await staged.rename(target.path);
    final pointer = File('${root.path}/$pointerName');
    final tempPointer = File('${root.path}/.$pointerName.tmp');
    await tempPointer.writeAsString(jsonEncode({'release': _toJson(release), 'local_path': target.path}));
    await tempPointer.rename(pointer.path);
    return ActiveModel(release: release, localPath: target.path);
  }

  Map<String, dynamic> _toJson(ReleaseManifest release) => {'release_id': release.releaseId, 'created_at_utc': release.createdAtUtc, 'model_scope': release.modelScope, 'release_sha256': release.releaseSha256, 'onnx': {'path': release.onnx.path, 'bytes': release.onnx.bytes, 'sha256': release.onnx.sha256}, 'class_map': release.classMap.map((g) => {'id': g.id, 'code_point': g.codePoint}).toList()};
  ReleaseManifest _manifest(Map<String, dynamic> json) => ReleaseManifest(releaseId: json['release_id'] as String, createdAtUtc: json['created_at_utc'] as String, modelScope: json['model_scope'] as String, releaseSha256: json['release_sha256'] as String, onnx: ReleaseArtifact(path: (json['onnx'] as Map)['path'] as String, bytes: (json['onnx'] as Map)['bytes'] as int, sha256: (json['onnx'] as Map)['sha256'] as String), classMap: ((json['class_map'] as List)).map((g) => GlyphClass(id: g['id'] as int, codePoint: g['code_point'] as int, label: String.fromCharCode(g['code_point'] as int))).toList());
}
