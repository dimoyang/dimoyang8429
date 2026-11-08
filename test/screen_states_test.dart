import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/core/network/token_store.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/screens/bookings_screen.dart';
import 'package:meditour_app/presentation/screens/medical_list_screen.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _packageJson = {
  'id': 1,
  'name': '膝关节置换手术',
  'name_en': 'Knee Replacement Surgery',
  'price': 15000,
  'currency': 'EUR',
  'duration_days': 21,
  'category': 'orthopedics',
  'description': '由三甲医院骨科专家团队主刀。',
  'image_url': 'https://example.com/knee.png',
};

const _packageJson2 = {
  'id': 2,
  'name': '微创种植牙',
  'name_en': 'Dental Implants',
  'price': 2500,
  'currency': 'EUR',
  'duration_days': 7,
  'category': 'dentistry',
  'description': '数字化导板种植技术。',
  'image_url': 'https://example.com/dental.png',
};

const _bookingJson = {
  'id': 7,
  'order_no': 'MT202601010000AB',
  'package_id': 1,
  'appointment_date': '2026-02-01T09:00:00',
  'total_price': 15000,
  'currency': 'EUR',
  'status': 'pending',
  'created_at': '2026-01-01T10:00:00',
};

void main() {
  final originalDio = ApiService.instance.dioForTesting;

  setUpAll(() async {
    await initializeDateFormatting();
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TokenStore.resetForTesting();
    ServiceRepository.resetForTesting();
  });

  tearDown(() {
    ApiService.instance.dioForTesting = originalDio;
  });

  testWidgets('医疗列表错误态显示并可重试', (tester) async {
    var failing = true;
    _installFakeApi((options) {
      if (failing) {
        return _jsonBody({'detail': 'boom'}, status: 500);
      }
      if (options.path.contains('/medical/packages')) {
        return _jsonBody({
          'items': [_packageJson],
        });
      }
      return _jsonBody(<Object>[]);
    });

    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await _pumpFrames(tester);

    expect(find.text('加载失败'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '重试'), findsOneWidget);

    failing = false;
    await tester.tap(find.widgetWithText(FilledButton, '重试'));
    await _pumpFrames(tester);

    expect(find.text('膝关节置换手术'), findsOneWidget);
  });

  testWidgets('医疗列表空态显示', (tester) async {
    _installFakeApi((options) {
      if (options.path.contains('/medical/packages')) {
        return _jsonBody({'items': <Object>[]});
      }
      return _jsonBody(<Object>[]);
    });

    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await _pumpFrames(tester);

    expect(find.text('暂无可预约服务'), findsOneWidget);
  });

  testWidgets('医疗列表在 320dp 与 1.3 倍字号下不溢出', (tester) async {
    _installFakeApi((options) {
      if (options.path.contains('/medical/packages')) {
        return _jsonBody({
          'items': [_packageJson],
        });
      }
      return _jsonBody(<Object>[]);
    });
    _useNarrowScreen(tester);

    await tester.pumpWidget(
      _app(home: const MedicalListScreen(), textScale: 1.3),
    );
    await _pumpFrames(tester);

    expect(tester.takeException(), isNull);
    expect(find.text('膝关节置换手术'), findsOneWidget);
  });

  testWidgets('订单页未登录时显示登录引导', (tester) async {
    _installFakeApi((options) => _jsonBody(<Object>[]));
    final auth = AuthProvider();
    await tester.runAsync(auth.init);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);

    expect(find.text('需要登录'), findsOneWidget);
    expect(find.text('登录后可查看您的预约记录与就诊信息。'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '去登录'), findsOneWidget);
  });

  testWidgets('订单页空态显示', (tester) async {
    _installFakeApi(_bookingRoutes(bookings: <Object>[]));
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);

    expect(find.text('还没有预约'), findsOneWidget);
    expect(find.text('您提交的医疗服务预约会显示在这里。'), findsOneWidget);
  });

  testWidgets('订单页错误态显示并可重试', (tester) async {
    var failing = true;
    _installFakeApi((options) {
      final routes = _bookingRoutes(bookings: [_bookingJson]);
      if (options.path.contains('/bookings') && failing) {
        return _jsonBody({'detail': 'boom'}, status: 500);
      }
      return routes(options);
    });
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);

    expect(find.text('预约加载失败'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '重试'), findsOneWidget);

    failing = false;
    await tester.tap(find.widgetWithText(FilledButton, '重试'));
    await _pumpFrames(tester);

    expect(find.text('MT202601010000AB'), findsOneWidget);
    expect(find.text('待确认'), findsOneWidget);
  });

  testWidgets('医疗列表在少量条目时仍可下拉刷新', (tester) async {
    var packageCalls = 0;
    _installFakeApi((options) {
      if (options.path.contains('/medical/packages')) {
        packageCalls++;
        return _jsonBody({
          'items': [_packageJson, _packageJson2],
        });
      }
      return _jsonBody(<Object>[]);
    });

    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await _pumpFrames(tester);
    expect(packageCalls, 1);

    // 两条样例数据不足一屏，依赖 AlwaysScrollableScrollPhysics 才能下拉刷新。
    await tester.drag(find.byType(ListView), const Offset(0, 260));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await _pumpFrames(tester);

    expect(packageCalls, greaterThan(1));
  });

  testWidgets('订单页在 320dp 与 1.3 倍字号下不溢出', (tester) async {
    _installFakeApi(_bookingRoutes(bookings: [_bookingJson]));
    final auth = await _loggedInAuth(tester);
    _useNarrowScreen(tester);

    await tester.pumpWidget(
      _app(home: const BookingsScreen(), auth: auth, textScale: 1.3),
    );
    await _pumpFrames(tester);

    expect(tester.takeException(), isNull);
    expect(find.text('MT202601010000AB'), findsOneWidget);
    expect(find.text('待确认'), findsOneWidget);
  });
}

/// 订单页依赖的登录、当前用户与订单列表三个端点。
ResponseBody Function(RequestOptions) _bookingRoutes({
  required List<Object> bookings,
}) {
  return (options) {
    if (options.path.contains('/auth/login')) {
      return _jsonBody({'access_token': 'token-123'});
    }
    if (options.path.contains('/auth/me')) {
      return _jsonBody({
        'id': 1,
        'email': 'alice@example.com',
        'full_name': 'Alice',
      });
    }
    if (options.path.contains('/bookings')) {
      return _jsonBody(bookings);
    }
    return _jsonBody(<Object>[]);
  };
}

/// 在真实异步区完成登录准备，避免在 fake-async 中等待网络/存储链导致挂起。
Future<AuthProvider> _loggedInAuth(WidgetTester tester) async {
  final auth = AuthProvider();
  await tester.runAsync(() async {
    await auth.init();
    await auth.login(email: 'alice@example.com', password: 'secret12');
  });
  return auth;
}

void _installFakeApi(ResponseBody Function(RequestOptions) handler) {
  final dio = Dio(BaseOptions(baseUrl: 'http://fake.local/api/v1'))
    ..httpClientAdapter = _FakeAdapter(handler);
  ApiService.instance.dioForTesting = dio;
}

ResponseBody _jsonBody(Object data, {int status = 200}) {
  return ResponseBody.fromString(
    jsonEncode(data),
    status,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

Widget _app({
  required Widget home,
  AuthProvider? auth,
  double textScale = 1.0,
}) {
  final app = MaterialApp(
    locale: const Locale('zh'),
    supportedLocales: AppConstants.supportedLocales,
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(context).copyWith(
        textScaler: TextScaler.linear(textScale),
      ),
      child: child!,
    ),
    home: home,
  );
  if (auth == null) {
    return app;
  }
  return ChangeNotifierProvider<AuthProvider>.value(value: auth, child: app);
}

void _useNarrowScreen(WidgetTester tester) {
  tester.view.devicePixelRatio = 3.0;
  tester.view.physicalSize = const Size(320 * 3, 700 * 3);
  addTearDown(tester.view.reset);
}

/// 手动推帧，避免等待图片占位动画导致 pumpAndSettle 超时。
Future<void> _pumpFrames(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  await tester.pump(const Duration(milliseconds: 300));
}

class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this._handler);

  final ResponseBody Function(RequestOptions options) _handler;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return _handler(options);
  }

  @override
  void close({bool force = false}) {}
}
