import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Destination.getName', () {
    test('未指定语言时保持中文主名与英文名旧行为', () {
      final destination = _destination();

      expect(destination.getName('zh'), '北京');
      expect(destination.getName('zh-CN'), '北京');
      expect(destination.getName('en'), 'Beijing');
      // 旧缓存/样例没有 de/fr 译文，回退英文。
      expect(destination.getName('de'), 'Beijing');
      expect(destination.getName('fr'), 'Beijing');
    });

    test('de/fr 拉取后使用后端译文，其他语言回退英文', () {
      final german = _destination(contentLanguage: 'de', name: 'Peking');
      expect(german.getName('de'), 'Peking');
      expect(german.getName('zh'), 'Beijing');
      expect(german.getName('en'), 'Beijing');
      expect(german.getName('fr'), 'Beijing');

      final french = _destination(contentLanguage: 'fr', name: 'Pékin');
      expect(french.getName('fr'), 'Pékin');
      expect(french.getName('de'), 'Beijing');
    });

    test('缓存往返保留内容语言', () {
      final german = _destination(contentLanguage: 'de', name: 'Peking');
      final json = german.toJson();

      expect(json['content_language'], 'de');
      final restored = Destination.fromJson(Map<String, dynamic>.from(json));
      expect(restored.contentLanguage, 'de');
      expect(restored.getName('de'), 'Peking');
    });

    test('未指定语言的数据不写入 content_language', () {
      expect(_destination().toJson().containsKey('content_language'), isFalse);
    });
  });

  test('语言切换按新语言重新拉取，切回中文恢复，失败时回退英文', () async {
    SharedPreferences.setMockInitialValues({});
    DestinationRepository.resetForTesting();
    // 该用例走真实网络路径，恢复被 flutter_test 替换掉的 HttpClient。
    HttpOverrides.global = null;

    final requested = <String?>[];
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    server.listen((request) {
      final lang = request.uri.queryParameters['lang'];
      requested.add(lang);
      if (lang == 'it') {
        // 后端不支持的语言：422，前端应保留已有数据并回退英文。
        request.response
          ..statusCode = 422
          ..headers.contentType = ContentType.json
          ..write(jsonEncode({'detail': 'Unsupported lang'}))
          ..close();
        return;
      }
      final name = switch (lang) {
        'de' => 'Peking',
        'fr' => 'Pékin',
        _ => '北京',
      };
      request.response
        ..headers.contentType = ContentType.json
        ..write(jsonEncode([_payload(name)]))
        ..close();
    });
    ApiService.instance.dioForTesting.options.baseUrl =
        'http://127.0.0.1:${server.port}/api/v1';

    final provider = DestinationProvider();

    // 中文：沿用不传 lang 的旧路径。
    await provider.init(lang: 'zh');
    expect(requested, [null]);
    expect(provider.destinations.single.getName('zh'), '北京');
    expect(provider.destinations.single.getName('en'), 'Beijing');

    // 切到德语：带 lang=de 重新拉取，名称变成德语译文。
    await provider.syncLanguage('de');
    expect(requested.last, 'de');
    expect(provider.destinations.single.getName('de'), 'Peking');
    expect(provider.destinations.single.contentLanguage, 'de');
    // 当前数据里没有中文原文，中文/英文界面回退英文名。
    expect(provider.destinations.single.getName('zh'), 'Beijing');
    expect(provider.destinations.single.getName('en'), 'Beijing');

    // 同一语言不重复请求。
    final requestCount = requested.length;
    await provider.syncLanguage('de');
    expect(requested.length, requestCount);

    // 切回中文：再次不带 lang 拉取，主名恢复为中文。
    await provider.syncLanguage('zh');
    expect(requested.last, isNull);
    expect(provider.destinations.single.getName('zh'), '北京');
    expect(provider.destinations.single.getName('de'), 'Beijing');
    expect(provider.destinations.single.contentLanguage, isNull);

    // 后端不支持的语言：请求失败但不崩溃，保留中文数据。
    await provider.syncLanguage('it');
    expect(requested.last, 'it');
    expect(provider.hasError, isTrue);
    expect(provider.destinations.single.getName('zh'), '北京');
    expect(provider.destinations.single.getName('de'), 'Beijing');
  });
}

Destination _destination({String? contentLanguage, String name = '北京'}) {
  return Destination.fromJson(
    _payload(name),
    lang: contentLanguage,
  );
}

Map<String, Object> _payload(String name) {
  return {
    'id': 'beijing',
    'name': name,
    'name_en': 'Beijing',
    'tagline': 'tagline',
    'image_url': 'https://example.com/beijing.png',
    'search_terms': <Object>['beijing'],
    'best_season': 'Spring',
    'suggest_days': '3 days',
    'intro': 'intro',
    'experiences': <Object>[],
    'tips': <Object>[],
  };
}
