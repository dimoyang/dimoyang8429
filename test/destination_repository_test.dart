import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    DestinationRepository.resetForTesting();
    // flutter_test 默认把 HttpClient 换成始终返回 400 的假实现；这两个用例
    // 要验证真实网络路径（连接失败回退 / 本地服务拉取），需恢复真实 HttpClient。
    HttpOverrides.global = null;
  });

  test('refresh falls back to sample data when network fails', () async {
    ApiService.instance.dioForTesting.options.baseUrl =
        'http://127.0.0.1:1/api/v1';

    final list = await DestinationRepository.refresh();

    expect(list, isNotEmpty);
    expect(list.first.id, 'beijing');
    expect(DestinationRepository.lastLoadWasSample, isTrue);
  });

  test('refresh loads remote data and persists cache', () async {
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
        'experiences': [
          {'icon': '🏯', 'title': 'Palace', 'description': 'desc'},
        ],
        'tips': ['tip'],
      },
    ];

    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    server.listen((request) {
      request.response
        ..headers.contentType = ContentType.json
        ..write(jsonEncode(payload))
        ..close();
    });
    ApiService.instance.dioForTesting.options.baseUrl =
        'http://127.0.0.1:${server.port}/api/v1';

    final list = await DestinationRepository.refresh();

    expect(list, hasLength(1));
    expect(list.single.id, 'remote-city');
    expect(list.single.nameEn, 'Remote City');
    expect(list.single.experiences.single.title, 'Palace');
    expect(DestinationRepository.lastLoadWasSample, isFalse);

    // 持久缓存恢复：重置内存缓存后仍能从 SharedPreferences 还原。
    DestinationRepository.resetForTesting();
    expect(DestinationRepository.destinations.first.id, 'beijing');
    await DestinationRepository.restoreCache();
    expect(DestinationRepository.destinations.single.id, 'remote-city');
  });
}
