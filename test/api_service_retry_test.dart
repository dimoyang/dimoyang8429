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
  final originalRetries = ApiService.maxGetRetries;
  final originalDelay = ApiService.retryBaseDelay;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TokenStore.resetForTesting();
    ApiService.maxGetRetries = 2;
    // 测试里不真实等待，退避逻辑本身由次数断言覆盖。
    ApiService.retryBaseDelay = Duration.zero;
  });

  tearDown(() {
    dio.options.baseUrl = originalBaseUrl;
    ApiService.maxGetRetries = originalRetries;
    ApiService.retryBaseDelay = originalDelay;
  });

  Future<void> startServer(
    Future<void> Function(HttpRequest request) handler,
  ) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen(handler);
    addTearDown(() => server.close(force: true));
    dio.options.baseUrl = 'http://127.0.0.1:${server.port}';
  }

  test('GET 遇到 5xx 时有限重试，恢复后成功', () async {
    var calls = 0;
    await startServer((request) async {
      calls++;
      if (calls < 3) {
        await _json(request, {'detail': 'busy'}, status: 503);
        return;
      }
      await _json(request, {'id': 7, 'email': 'user@example.com'});
    });

    final me = await ApiService.instance.getMe();

    expect(me['email'], 'user@example.com');
    expect(calls, 3);
  });

  test('GET 持续 5xx 时重试次数有上限并最终抛出', () async {
    var calls = 0;
    await startServer((request) async {
      calls++;
      await _json(request, {'detail': 'busy'}, status: 500);
    });

    await expectLater(
      ApiService.instance.getHospitals(),
      throwsA(isA<ApiException>()),
    );
    // 首次请求 + 2 次重试，绝不无限重试。
    expect(calls, 3);
  });

  test('GET 4xx 不重试', () async {
    var calls = 0;
    await startServer((request) async {
      calls++;
      await _json(request, {'detail': 'gone'}, status: 404);
    });

    await expectLater(
      ApiService.instance.getHospitals(),
      throwsA(isA<ApiException>()),
    );
    expect(calls, 1);
  });

  test('POST 5xx 不自动重试，避免重复写入', () async {
    var calls = 0;
    await startServer((request) async {
      calls++;
      await _json(request, {'detail': 'busy'}, status: 503);
    });

    await expectLater(
      ApiService.instance.createBooking({'service_id': 1}),
      throwsA(isA<ApiException>()),
    );
    expect(calls, 1);
  });

  test('取消订单 POST 失败不重试', () async {
    var calls = 0;
    await startServer((request) async {
      calls++;
      await _json(request, {'detail': 'busy'}, status: 503);
    });

    await expectLater(
      ApiService.instance.cancelBooking(7),
      throwsA(isA<ApiException>()),
    );
    expect(calls, 1);
  });
}

Future<void> _json(HttpRequest request, Object data, {int status = 200}) async {
  request.response
    ..statusCode = status
    ..headers.contentType = ContentType.json
    ..write(jsonEncode(data));
  await request.response.close();
}
