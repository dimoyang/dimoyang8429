import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/respositories/booking_repository.dart';

void main() {
  final originalDio = ApiService.instance.dioForTesting;

  tearDown(() {
    ApiService.instance.dioForTesting = originalDio;
  });

  test('提交预约成功后映射后端返回', () async {
    final captured = <Map<String, dynamic>>[];
    final server = await _startServer((request) async {
      final body = await utf8.decoder.bind(request).join();
      captured.add(jsonDecode(body) as Map<String, dynamic>);
      await _json(request, {
        'id': 12,
        'order_no': 'MT-12',
        'total_price': 3200.5,
        'currency': 'EUR',
        'status': 'pending',
      });
    });
    addTearDown(() => server.close(force: true));
    ApiService.instance.dioForTesting = _dio(server.port);

    final result = await BookingRepository.create(
      serviceId: '3',
      date: DateTime(2026, 1, 2),
      contactName: 'Alice',
      contactPhone: '+8613800000000',
      contactEmail: 'alice@example.com',
      needPickup: true,
    );

    expect(result.id, 12);
    expect(result.orderNo, 'MT-12');
    expect(result.totalPrice, 3200.5);
    expect(result.currency, 'EUR');
    expect(result.status, 'pending');
    expect(captured.single['package_id'], 3);
    expect(
        captured.single['appointment_date'], contains('2026-01-02T09:00:00'));
    expect(captured.single['need_pickup'], isTrue);
  });

  test('serviceId 不是整数时抛 InvalidArgumentException', () async {
    await expectLater(
      BookingRepository.create(
        serviceId: 'abc',
        date: DateTime(2026, 1, 2),
        contactName: 'Alice',
        contactPhone: '+8613800000000',
        contactEmail: 'alice@example.com',
      ),
      throwsA(isA<InvalidArgumentException>()),
    );
  });

  test('服务端 5xx 抛 ServerException', () async {
    final server = await _startServer(
      (request) => _json(
        request,
        {'detail': 'boom'},
        status: HttpStatus.internalServerError,
      ),
    );
    addTearDown(() => server.close(force: true));
    ApiService.instance.dioForTesting = _dio(server.port);

    await expectLater(
      BookingRepository.create(
        serviceId: '3',
        date: DateTime(2026, 1, 2),
        contactName: 'Alice',
        contactPhone: '+8613800000000',
        contactEmail: 'alice@example.com',
      ),
      throwsA(isA<ServerException>()),
    );
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
