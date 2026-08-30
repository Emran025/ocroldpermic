import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';

class RemoteImageLoader {
  RemoteImageLoader(this.client);

  static const maximumBytes = 25 * 1024 * 1024;
  final Dio client;

  Future<String> download(Uri uri,
      {void Function(int received, int total)? onProgress}) async {
    if (uri.scheme != 'https' && uri.scheme != 'http') {
      throw const FormatException('Enter an HTTP(S) image URL.');
    }
    final response = await client.get<List<int>>(
      uri.toString(),
      options: Options(
          responseType: ResponseType.bytes,
          receiveTimeout: const Duration(seconds: 45)),
    );
    final data = response.data;
    if (data == null || data.isEmpty) {
      throw const FormatException('The remote URL returned an empty image.');
    }
    if (data.length > maximumBytes) {
      throw const FormatException(
          'The remote image exceeds the 25 MB safety limit.');
    }
    final contentType =
        response.headers.value(Headers.contentTypeHeader)?.toLowerCase();
    if (contentType != null && !contentType.startsWith('image/')) {
      throw const FormatException('The remote URL did not return an image.');
    }
    final typedData = Uint8List.fromList(data);
    if (img.decodeImage(typedData) == null) {
      throw const FormatException('The remote image could not be decoded.');
    }
    final cache = await getTemporaryDirectory();
    final path =
        '${cache.path}/ocr-input-${DateTime.now().microsecondsSinceEpoch}.img';
    await File(path).writeAsBytes(typedData, flush: true);
    onProgress?.call(data.length, data.length);
    return path;
  }
}
