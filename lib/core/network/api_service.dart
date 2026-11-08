import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/token_store.dart';

/// 后端 API 封装（medical-tourism-platform，前缀 /api/v1）。
class ApiService {
  ApiService._() {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConstants.apiBaseUrl,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 12),
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = TokenStore.current;
          if (token != null && !_isPublicAuthPath(options.path)) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) {
          final status = error.response?.statusCode;
          if (status == 401 && !_isPublicAuthPath(error.requestOptions.path)) {
            TokenStore.clear();
          }
          handler.next(error);
        },
      ),
    );
  }

  /// 免鉴权端点：仅登录与注册。
  ///
  /// `/auth/me` 等受保护接口必须携带 token，401 时也应清除失效凭据。
  static const Set<String> _publicAuthPaths = {'/auth/login', '/auth/register'};

  static bool _isPublicAuthPath(String path) {
    return _publicAuthPaths.contains(path.split('?').first);
  }

  static final ApiService instance = ApiService._();

  late Dio _dio;

  /// 仅测试用：替换底层 Dio，以便模拟不同网络响应。
  @visibleForTesting
  Dio get dioForTesting => _dio;

  @visibleForTesting
  set dioForTesting(Dio dio) => _dio = dio;

  Future<Map<String, dynamic>> _request(
    Future<Response<dynamic>> Function() call,
  ) async {
    try {
      final response = await call();
      final data = response.data;
      if (data is Map<String, dynamic>) {
        return data;
      }
      if (data is Map) {
        return Map<String, dynamic>.from(data);
      }
      return const {};
    } on DioException catch (error) {
      throw ApiException.fromDio(error);
    }
  }

  Future<List<Map<String, dynamic>>> _requestList(
    Future<Response<dynamic>> Function() call,
  ) async {
    try {
      final response = await call();
      final data = response.data;
      if (data is List) {
        return data
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList();
      }
      return const [];
    } on DioException catch (error) {
      throw ApiException.fromDio(error);
    }
  }

  /// 登录（后端为 OAuth2PasswordRequestForm，需 form-urlencoded）。
  Future<String> login({
    required String email,
    required String password,
  }) async {
    final data = await _request(
      () => _dio.post<dynamic>(
        '/auth/login',
        data: {'username': email, 'password': password},
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      ),
    );
    return data['access_token'] as String;
  }

  /// 注册，返回新用户信息。
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? fullName,
    String preferredLanguage = 'en',
  }) {
    return _request(
      () => _dio.post<dynamic>('/auth/register', data: {
        'email': email,
        'password': password,
        if (fullName != null && fullName.isNotEmpty) 'full_name': fullName,
        'preferred_language': preferredLanguage,
      }),
    );
  }

  /// 当前登录用户。
  Future<Map<String, dynamic>> getMe() {
    return _request(() => _dio.get<dynamic>('/auth/me'));
  }

  /// 医疗套餐列表。
  Future<List<Map<String, dynamic>>> getPackages({int pageSize = 100}) async {
    final data = await _request(
      () => _dio.get<dynamic>(
        '/medical/packages',
        queryParameters: {'page': 1, 'page_size': pageSize},
      ),
    );
    final items = data['items'];
    if (items is List) {
      return items
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }
    return const [];
  }

  /// 医院列表。
  Future<List<Map<String, dynamic>>> getHospitals() {
    return _requestList(() => _dio.get<dynamic>('/medical/hospitals'));
  }

  /// 创建预约订单。
  Future<Map<String, dynamic>> createBooking(Map<String, dynamic> request) {
    return _request(() => _dio.post<dynamic>('/bookings/', data: request));
  }

  /// 我的预约订单（预留）。
  Future<List<Map<String, dynamic>>> getMyBookings() {
    return _requestList(() => _dio.get<dynamic>('/bookings/'));
  }

  /// 取消自己的待确认订单；后端仅允许 pending -> cancelled。
  Future<Map<String, dynamic>> cancelBooking(int id) {
    return _request(() => _dio.post<dynamic>('/bookings/$id/cancel'));
  }
}
