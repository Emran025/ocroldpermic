import 'package:dio/dio.dart';

sealed class AppException implements Exception {
  const AppException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

final class NetworkException extends AppException {
  const NetworkException(super.message);
}

final class ServerException extends AppException {
  const ServerException(super.message, {super.statusCode});
}

final class ParsingException extends AppException {
  const ParsingException(super.message);
}

AppException mapDioException(DioException error) {
  final status = error.response?.statusCode;
  if (error.type == DioExceptionType.connectionError ||
      error.type == DioExceptionType.connectionTimeout ||
      error.type == DioExceptionType.receiveTimeout ||
      error.type == DioExceptionType.sendTimeout) {
    return const NetworkException('Network connection failed.');
  }
  final payload = error.response?.data;
  final message = payload is Map ? payload['message']?.toString() : null;
  return ServerException(message ?? 'Remote request failed.',
      statusCode: status);
}
