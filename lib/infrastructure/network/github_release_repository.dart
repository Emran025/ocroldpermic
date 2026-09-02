import 'dart:convert';
import 'package:dio/dio.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';

class GithubReleaseRepository implements ReleaseRepository {
  GithubReleaseRepository(this.client, {this.latestUrl = 'https://raw.githubusercontent.com/Emran025/old-permic-ocr-lab/colab-results/artifacts/published/latest.json'});
  final Dio client;
  final String latestUrl;

  @override
  Future<ReleaseManifest> fetchLatest() async {
    final response = await client.get<String>(latestUrl, options: Options(responseType: ResponseType.plain));
    final pointer = jsonDecode(response.data ?? '{}') as Map<String, dynamic>;
    final path = pointer['release_path'] as String? ?? pointer['path'] as String?;
    if (path == null || path.contains('..') || !path.endsWith('/release.json')) throw const FormatException('مؤشر إصدار غير صالح.');
    final base = latestUrl.substring(0, latestUrl.indexOf('/artifacts/'));
    final releaseResponse = await client.get<String>('$base/$path', options: Options(responseType: ResponseType.plain));
    final json = jsonDecode(releaseResponse.data ?? '{}') as Map<String, dynamic>;
    final classMap = ((json['class_map'] ?? json['classMap']) as List<dynamic>).map((item) {
      final value = item as Map<String, dynamic>;
      final codePoint = value['code_point'] is int ? value['code_point'] as int : int.parse(value['code_point'].toString());
      return GlyphClass(id: value['id'] as int, codePoint: codePoint, label: String.fromCharCode(codePoint));
    }).toList(growable: false);
    final artifact = (json['onnx'] as Map<String, dynamic>);
    final release = ReleaseManifest(
      releaseId: json['release_id'] as String,
      createdAtUtc: json['created_at_utc'] as String,
      modelScope: json['model_scope'] as String,
      releaseSha256: json['release_sha256'] as String,
      onnx: ReleaseArtifact(path: artifact['path'] as String, bytes: artifact['bytes'] as int, sha256: artifact['sha256'] as String),
      classMap: classMap,
    );
    if (!release.isOldPermicContract) throw const FormatException('الإصدار لا يطابق عقد Old Permic ذي 38 محرفًا.');
    return release;
  }
}
