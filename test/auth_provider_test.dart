import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart' show Locale;
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/core/network/token_store.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  final originalDio = ApiService.instance.dioForTesting;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TokenStore.resetForTesting();
  });

  tearDown(() {
    ApiService.instance.dioForTesting = originalDio;
  });

  test('登录成功后保存 token 并建立会话', () async {
    final server = await _startServer((request) async {
      if (request.uri.path.endsWith('/auth/login')) {
        await _json(request, {'access_token': 'token-123'});
      } else {
        await _json(request, {
          'id': 7,
          'email': 'user@example.com',
          'full_name': 'Alice',
          'preferred_language': 'zh',
        });
      }
    });
    addTearDown(() => server.close(force: true));
    ApiService.instance.dioForTesting = _dio(server.port);

    final auth = AuthProvider();
    await auth.init();
    await auth.login(email: 'user@example.com', password: 'secret123');

    expect(auth.isLoggedIn, isTrue);
    expect(auth.user!.email, 'user@example.com');
    expect(TokenStore.current, 'token-123');

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('auth_token'), 'token-123');
    expect(prefs.getString('cached_user'), contains('user@example.com'));
  });

  test('启动恢复遇到 401 时清除会话', () async {
    SharedPreferences.setMockInitialValues({'auth_token': 'expired-token'});
    TokenStore.resetForTesting();

    final server = await _startServer(
      (request) => _json(request, {'detail': 'expired'}, status: 401),
    );
    addTearDown(() => server.close(force: true));
    ApiService.instance.dioForTesting = _dio(server.port);

    final auth = AuthProvider();
    await auth.init();

    expect(auth.isInitialized, isTrue);
    expect(auth.isLoggedIn, isFalse);
    expect(TokenStore.current, isNull);

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('auth_token'), isNull);
    expect(prefs.getString('cached_user'), isNull);
  });

  test('启动恢复网络失败时不崩溃并回到未登录态', () async {
    SharedPreferences.setMockInitialValues({'auth_token': 'stale-token'});
    TokenStore.resetForTesting();
    ApiService.instance.dioForTesting = Dio(
      BaseOptions(
        baseUrl: 'http://127.0.0.1:1/api/v1',
        connectTimeout: const Duration(milliseconds: 500),
        receiveTimeout: const Duration(milliseconds: 500),
      ),
    );

    final auth = AuthProvider();
    await auth.init();

    expect(auth.isInitialized, isTrue);
    expect(auth.isLoggedIn, isFalse);
    expect(TokenStore.current, isNull);
  });

  test('登录 401 映射为凭据错误而不是会话过期', () async {
    final server = await _startServer(
      (request) => _json(
        request,
        {'detail': 'Incorrect username or password'},
        status: 401,
      ),
    );
    addTearDown(() => server.close(force: true));
    ApiService.instance.dioForTesting = _dio(server.port);

    final auth = AuthProvider();
    await auth.init();

    await expectLater(
      auth.login(email: 'user@example.com', password: 'wrong-pass'),
      throwsA(isA<InvalidCredentialsException>()),
    );

    final l10n = await AppLocalizations.delegate.load(const Locale('zh'));
    expect(
      const InvalidCredentialsException().toLocalizedMessage(l10n),
      '邮箱或密码错误。',
    );
    expect(auth.isLoggedIn, isFalse);
  });

  test('会话被清除后同步退出登录态', () async {
    final server = await _startServer((request) async {
      if (request.uri.path.endsWith('/auth/login')) {
        await _json(request, {'access_token': 'token-abc'});
      } else {
        await _json(request, {
          'id': 7,
          'email': 'user@example.com',
          'full_name': 'Alice',
          'preferred_language': 'zh',
        });
      }
    });
    addTearDown(() => server.close(force: true));
    ApiService.instance.dioForTesting = _dio(server.port);

    final auth = AuthProvider();
    await auth.init();
    await auth.login(email: 'user@example.com', password: 'secret123');
    expect(auth.isLoggedIn, isTrue);

    // 模拟拦截器在业务请求 401 后清除 token。
    await TokenStore.clear();

    expect(auth.isLoggedIn, isFalse);
    expect(auth.user, isNull);
    expect(TokenStore.current, isNull);
  });
}

Dio _dio(int port) {
  return Dio(BaseOptions(baseUrl: 'http://127.0.0.1:$port/api/v1'));
}

Future<HttpServer> _startServer(
  Future<void> Function(HttpRequest request) handler,
) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen(handler);
  return server;
}

Future<void> _json(
  HttpRequest request,
  Object body, {
  int status = 200,
}) async {
  request.response
    ..statusCode = status
    ..headers.contentType = ContentType.json
    ..write(jsonEncode(body));
  await request.response.close();
}
