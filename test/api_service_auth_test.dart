import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/core/network/token_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  final dio = ApiService.instance.dioForTesting;
  final originalBaseUrl = dio.options.baseUrl;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TokenStore.resetForTesting();
  });

  tearDown(() {
    dio.options.baseUrl = originalBaseUrl;
  });

  test('/auth/me 请求携带 Bearer token', () async {
    final headers = <String, String?>{};
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      headers['authorization'] =
          request.headers.value(HttpHeaders.authorizationHeader);
      await _json(request, {'id': 7, 'email': 'user@example.com'});
    });
    addTearDown(() => server.close(force: true));
    dio.options.baseUrl = 'http://127.0.0.1:${server.port}';

    await TokenStore.save('token-123');
    final me = await ApiService.instance.getMe();

    expect(headers['authorization'], 'Bearer token-123');
    expect(me['email'], 'user@example.com');
  });

  test('/auth/me 返回 401 时清除本地 token', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      await _json(request, {'detail': 'expired'}, status: 401);
    });
    addTearDown(() => server.close(force: true));
    dio.options.baseUrl = 'http://127.0.0.1:${server.port}';

    await TokenStore.save('token-123');

    await expectLater(
      ApiService.instance.getMe(),
      throwsA(isA<ApiException>()),
    );
    expect(TokenStore.current, isNull);
  });

  test('401 后用 refresh token 续期并重放请求', () async {
    var refreshCalls = 0;
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      if (request.uri.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        await _json(request, {
          'access_token': 'access-new',
          'refresh_token': 'refresh-new',
        });
        return;
      }
      final auth = request.headers.value(HttpHeaders.authorizationHeader);
      if (auth == 'Bearer token-old') {
        await _json(request, {'detail': 'expired'}, status: 401);
      } else {
        await _json(request, {'id': 7, 'email': 'user@example.com'});
      }
    });
    addTearDown(() => server.close(force: true));
    dio.options.baseUrl = 'http://127.0.0.1:${server.port}';

    await TokenStore.save('token-old', refreshToken: 'refresh-old');
    final me = await ApiService.instance.getMe();

    expect(me['email'], 'user@example.com');
    expect(refreshCalls, 1);
    expect(TokenStore.current, 'access-new');
    expect(TokenStore.refreshToken, 'refresh-new');
  });

  test('并发 401 只消耗一次 refresh token', () async {
    var refreshCalls = 0;
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      if (request.uri.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        // 模拟真实网络往返，制造并发窗口。
        await Future<void>.delayed(const Duration(milliseconds: 40));
        await _json(request, {
          'access_token': 'access-new',
          'refresh_token': 'refresh-new',
        });
        return;
      }
      final auth = request.headers.value(HttpHeaders.authorizationHeader);
      if (auth == 'Bearer token-old') {
        await _json(request, {'detail': 'expired'}, status: 401);
      } else {
        await _json(request, {'id': 7, 'email': 'user@example.com'});
      }
    });
    addTearDown(() => server.close(force: true));
    dio.options.baseUrl = 'http://127.0.0.1:${server.port}';

    await TokenStore.save('token-old', refreshToken: 'refresh-old');
    final results = await Future.wait([
      ApiService.instance.getMe(),
      ApiService.instance.getMe(),
    ]);

    expect(results, hasLength(2));
    expect(refreshCalls, 1);
    expect(TokenStore.current, 'access-new');
  });

  test('refresh 失败时清空会话并抛出未授权错误', () async {
    var refreshCalls = 0;
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      if (request.uri.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        await _json(request, {'detail': 'invalid refresh'}, status: 401);
        return;
      }
      await _json(request, {'detail': 'expired'}, status: 401);
    });
    addTearDown(() => server.close(force: true));
    dio.options.baseUrl = 'http://127.0.0.1:${server.port}';

    await TokenStore.save('token-old', refreshToken: 'refresh-old');

    await expectLater(
      ApiService.instance.getMe(),
      throwsA(isA<UnauthorizedException>()),
    );
    expect(refreshCalls, 1);
    expect(TokenStore.current, isNull);
    expect(TokenStore.refreshToken, isNull);
  });
}

Future<void> _json(HttpRequest request, Object data, {int status = 200}) async {
  request.response
    ..statusCode = status
    ..headers.contentType = ContentType.json
    ..write(jsonEncode(data));
  await request.response.close();
}
