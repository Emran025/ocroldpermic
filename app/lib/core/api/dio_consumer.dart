import 'package:dio/dio.dart';

import '../error/app_exceptions.dart';
import 'api_consumer.dart';

final class DioConsumer implements ApiConsumer {
  DioConsumer({required Dio dio}) : _dio = dio;
  final Dio _dio;

  @override
  Future<dynamic> get(String path,
          {Object? data, Map<String, dynamic>? queryParameters}) =>
      _request(
          () => _dio.get(path, data: data, queryParameters: queryParameters));

  @override
  Future<dynamic> post(String path,
          {Object? data, Map<String, dynamic>? queryParameters}) =>
      _request(
          () => _dio.post(path, data: data, queryParameters: queryParameters));

  @override
  Future<dynamic> put(String path,
          {Object? data, Map<String, dynamic>? queryParameters}) =>
      _request(
          () => _dio.put(path, data: data, queryParameters: queryParameters));

  @override
  Future<dynamic> delete(String path,
          {Object? data, Map<String, dynamic>? queryParameters}) =>
      _request(() =>
          _dio.delete(path, data: data, queryParameters: queryParameters));

  Future<dynamic> _request(Future<Response<dynamic>> Function() request) async {
    try {
      final response = await request();
      if (response.statusCode == null || response.statusCode! >= 400) {
        throw ServerException('Remote request failed.',
            statusCode: response.statusCode);
      }
      return response.data;
    } on DioException catch (error) {
      throw mapDioException(error);
    }
  }
}
