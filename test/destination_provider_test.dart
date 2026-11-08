import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    DestinationRepository.resetForTesting();
    // 该用例要验证真实网络路径，恢复被 flutter_test 替换掉的 HttpClient。
    HttpOverrides.global = null;
  });

  test('首次加载为空后可重试，失败再成功后回到正常数据', () async {
    var mode = 'empty';
    final payload = [
      {
        'id': 'remote-city',
        'name': '远程城市',
        'name_en': 'Remote City',
        'tagline': 'tagline',
        'image_url': 'https://example.com/city.png',
        'search_terms': ['remote'],
        'best_season': 'Spring',
        'suggest_days': '3 days',
        'intro': 'intro',
        'experiences': <Object>[],
        'tips': <Object>[],
      },
    ];

    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    server.listen((request) {
      if (mode == 'empty') {
        request.response
          ..headers.contentType = ContentType.json
          ..write('[]')
          ..close();
        return;
      }
      if (mode == 'fail') {
        request.response
          ..statusCode = 500
          ..write('boom')
          ..close();
        return;
      }
      request.response
        ..headers.contentType = ContentType.json
        ..write(jsonEncode(payload))
        ..close();
    });
    ApiService.instance.dioForTesting.options.baseUrl =
        'http://127.0.0.1:${server.port}/api/v1';

    final provider = DestinationProvider();
    await provider.init();

    // 远端成功返回空列表：首页可展示空态，而不是一直骨架。
    expect(provider.destinations, isEmpty);
    expect(provider.hasError, isFalse);
    expect(provider.isInitialLoading, isFalse);

    // 服务端 500：保留空列表并进入错误态（首页据此显示重试按钮）。
    mode = 'fail';
    await provider.refresh();
    expect(provider.hasError, isTrue);
    expect(provider.destinations, isEmpty);
    expect(provider.isOfflineFallback, isTrue);

    // 用户点重试后成功：错误清除并载入远端数据。
    mode = 'ok';
    await provider.refresh();
    expect(provider.hasError, isFalse);
    expect(provider.destinations.single.id, 'remote-city');
    expect(provider.isOfflineFallback, isFalse);
  });
}
