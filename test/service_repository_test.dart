import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';

void main() {
  final originalDio = ApiService.instance.dioForTesting;

  setUp(ServiceRepository.resetForTesting);

  tearDown(() {
    ApiService.instance.dioForTesting = originalDio;
  });

  test('网络不可达时回退到内置示例数据', () async {
    ApiService.instance.dioForTesting = Dio(
      BaseOptions(
        baseUrl: 'http://127.0.0.1:1/api/v1',
        connectTimeout: const Duration(milliseconds: 500),
        receiveTimeout: const Duration(milliseconds: 500),
      ),
    );

    final services = await ServiceRepository.getServices(forceRemote: true);

    expect(ServiceRepository.lastLoadWasSample, isTrue);
    expect(services.length, ServiceRepository.sampleServices.length);
    expect(services.first.id, ServiceRepository.sampleServices.first.id);
  });

  test('HTTP 5xx 不回退，抛出 ServerException', () async {
    final server = await _startServer();
    addTearDown(() => server.close(force: true));
    server.listen((request) async {
      request.response
        ..statusCode = HttpStatus.internalServerError
        ..headers.contentType = ContentType.json
        ..write('{"detail":"boom"}');
      await request.response.close();
    });
    ApiService.instance.dioForTesting = Dio(
      BaseOptions(baseUrl: 'http://127.0.0.1:${server.port}/api/v1'),
    );

    await expectLater(
      ServiceRepository.getServices(forceRemote: true),
      throwsA(isA<ServerException>()),
    );
    expect(ServiceRepository.lastLoadWasSample, isFalse);
    expect(ServiceRepository.findById('1'), isNull);
  });

  test('响应解析失败不回退，抛出 ResponseParseException', () async {
    final server = await _startServer();
    addTearDown(() => server.close(force: true));
    server.listen((request) async {
      request.response.headers.contentType = ContentType.json;
      if (request.uri.path.contains('/medical/packages')) {
        request.response.write(
          '{"items":[{"id":1,"price":"not-a-number"}]}',
        );
      } else {
        request.response.write('[]');
      }
      await request.response.close();
    });
    ApiService.instance.dioForTesting = Dio(
      BaseOptions(baseUrl: 'http://127.0.0.1:${server.port}/api/v1'),
    );

    await expectLater(
      ServiceRepository.getServices(forceRemote: true),
      throwsA(isA<ResponseParseException>()),
    );
    expect(ServiceRepository.lastLoadWasSample, isFalse);
    expect(ServiceRepository.findById('1'), isNull);
  });
}

Future<HttpServer> _startServer() {
  return HttpServer.bind(InternetAddress.loopbackIPv4, 0);
}
