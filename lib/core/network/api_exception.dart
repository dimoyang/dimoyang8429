import 'package:dio/dio.dart';
import 'package:meditour_app/l10n/app_localizations.dart';

/// API 异常基类，UI 统一用 [toLocalizedMessage] 取本地化文案。
sealed class ApiException implements Exception {
  const ApiException();

  /// 把 DioException 映射为业务异常。
  static ApiException fromDio(DioException error) {
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.badCertificate) {
      return const NetworkException();
    }

    final statusCode = error.response?.statusCode;
    if (statusCode == null) {
      return const NetworkException();
    }
    if (statusCode == 401) {
      return const UnauthorizedException();
    }
    if (statusCode >= 500) {
      return const ServerException();
    }
    return ApiBusinessException(
      statusCode: statusCode,
      detail: _extractDetail(error.response?.data),
    );
  }

  static String? _extractDetail(dynamic data) {
    if (data is! Map) {
      return null;
    }
    final detail = data['detail'];
    if (detail is String) {
      return detail;
    }
    // FastAPI 422 校验错误：detail 为错误列表，取第一条消息。
    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is Map && first['msg'] is String) {
        return first['msg'] as String;
      }
    }
    return null;
  }

  String toLocalizedMessage(AppLocalizations l10n);
}

/// 网络不可达或超时。
class NetworkException extends ApiException {
  const NetworkException();

  @override
  String toLocalizedMessage(AppLocalizations l10n) => l10n.errorNetwork;
}

/// 401：未登录或 token 失效。
class UnauthorizedException extends ApiException {
  const UnauthorizedException();

  @override
  String toLocalizedMessage(AppLocalizations l10n) => l10n.errorUnauthorized;
}

/// 其余 4xx：优先展示后端返回的 detail。
class ApiBusinessException extends ApiException {
  final int statusCode;
  final String? detail;

  const ApiBusinessException({required this.statusCode, this.detail});

  @override
  String toLocalizedMessage(AppLocalizations l10n) {
    if (detail != null && detail!.isNotEmpty) {
      return detail!;
    }
    return l10n.errorUnknown;
  }
}

/// 5xx：服务端错误。
class ServerException extends ApiException {
  const ServerException();

  @override
  String toLocalizedMessage(AppLocalizations l10n) => l10n.errorServer;
}

/// 响应结构或字段类型无法解析。
class ResponseParseException extends ApiException {
  const ResponseParseException();

  @override
  String toLocalizedMessage(AppLocalizations l10n) => l10n.errorUnknown;
}

/// 本地参数错误（如服务 id 无法转换为后端 package_id）。
class InvalidArgumentException extends ApiException {
  const InvalidArgumentException();

  @override
  String toLocalizedMessage(AppLocalizations l10n) => l10n.errorUnknown;
}
