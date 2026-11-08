import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/token_store.dart';

/// 登录返回的令牌对（refresh 一次一换）。
class AuthTokens {
  final String accessToken;
  final String refreshToken;

  const AuthTokens({required this.accessToken, required this.refreshToken});
}

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
    _dio.interceptors.add(_buildAuthInterceptor());
  }

  /// 免鉴权端点：登录、注册、刷新。
  ///
  /// `/auth/me` 等受保护接口必须携带 token，401 时也应清除失效凭据。
  static const Set<String> _publicAuthPaths = {
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
  };

  static bool _isPublicAuthPath(String path) {
    return _publicAuthPaths.contains(path.split('?').first);
  }

  /// 鉴权拦截器：请求注入 Bearer；401 时用 refresh token 续期并重放。
  ///
  /// 并发 401 共享同一个刷新 Future，保证一次只消耗一个 refresh token。
  InterceptorsWrapper _buildAuthInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = TokenStore.current;
        if (token != null && !_isPublicAuthPath(options.path)) {
          options.headers['Authorization'] = 'Bearer $token';
          options.extra['auth_token'] = token;
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final status = error.response?.statusCode;
        final requestOptions = error.requestOptions;
        if (status != 401 ||
            _isPublicAuthPath(requestOptions.path) ||
            requestOptions.path == '/auth/refresh') {
          handler.next(error);
          return;
        }
        // 重放过的请求再次 401：刷新令牌也无效，清会话。
        if (requestOptions.extra['auth_retried'] == true) {
          await TokenStore.clear();
          handler.next(error);
          return;
        }
        final current = TokenStore.current;
        if (current == null) {
          await TokenStore.clear();
          handler.next(error);
          return;
        }
        final usedToken = requestOptions.extra['auth_token'] as String?;
        // 其他并发请求已经刷新过，当前 token 更新，直接重放即可。
        final needsRefresh = usedToken == null || usedToken == current;
        if (needsRefresh && !await _refreshTokens()) {
          handler.next(error);
          return;
        }
        await _retry(requestOptions, handler);
      },
    );
  }

  Future<void> _retry(
    RequestOptions options,
    ErrorInterceptorHandler handler,
  ) async {
    options.extra['auth_retried'] = true;
    options.headers.remove('Authorization');
    try {
      final response = await _dio.fetch<dynamic>(options);
      handler.resolve(response);
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  Future<bool>? _refreshInFlight;

  /// 单飞刷新：并发 401 复用同一个 Future，刷新令牌只会被消费一次。
  Future<bool> _refreshTokens() {
    return _refreshInFlight ??= _performRefresh().whenComplete(() {
      _refreshInFlight = null;
    });
  }

  Future<bool> _performRefresh() async {
    final refreshToken = TokenStore.refreshToken;
    if (refreshToken == null || refreshToken.isEmpty) {
      // 没有刷新令牌可用，等同于续期失败：清会话。
      await TokenStore.clear();
      return false;
    }
    try {
      final data = await _request(
        () => _dio.post<dynamic>(
          '/auth/refresh',
          data: {'refresh_token': refreshToken},
        ),
      );
      final access = data['access_token'] as String?;
      final next = data['refresh_token'] as String?;
      if (access == null || access.isEmpty || next == null || next.isEmpty) {
        await TokenStore.clear();
        return false;
      }
      await TokenStore.save(access, refreshToken: next);
      return true;
    } catch (_) {
      // 刷新失败即登出：清干净会话，避免留下"看起来已登录"的状态。
      await TokenStore.clear();
      return false;
    }
  }

  /// 仅测试用：把与线上一致的鉴权拦截器装到自定义 Dio 上。
  @visibleForTesting
  InterceptorsWrapper get authInterceptorForTesting => _buildAuthInterceptor();

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
  Future<AuthTokens> login({
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
    return AuthTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String? ?? '',
    );
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
