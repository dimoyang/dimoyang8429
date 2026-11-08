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
import 'package:meditour_app/presentation/screens/booking_screen.dart';
import 'package:meditour_app/presentation/screens/medical_list_screen.dart';
import 'package:meditour_app/presentation/screens/service_detail_screen.dart';
import 'package:meditour_app/presentation/widgets/service_card.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';
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

/// 指定状态的最小订单数据，用于状态映射与取消流程测试。
Map<String, Object> _orderJson({required int id, required String status}) {
  return {
    'id': id,
    'order_no': 'MT2026010100$id',
    'package_id': 1,
    'appointment_date': '2026-02-01T09:00:00',
    'total_price': 15000,
    'currency': 'EUR',
    'status': status,
    'created_at': '2026-01-01T10:00:00',
  };
}

void main() {
  final originalDio = ApiService.instance.dioForTesting;
  final originalRetryDelay = ApiService.retryBaseDelay;

  setUpAll(() async {
    await initializeDateFormatting();
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TokenStore.resetForTesting();
    ServiceRepository.resetForTesting();
    // 测试里不真实等待退避；重试次数语义由 api_service_retry_test 覆盖。
    ApiService.retryBaseDelay = Duration.zero;
  });

  tearDown(() {
    ApiService.instance.dioForTesting = originalDio;
    ApiService.retryBaseDelay = originalRetryDelay;
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

  testWidgets('订单状态按语言映射并对未知状态兜底', (tester) async {
    _installFakeApi(_bookingRoutes(bookings: [
      _orderJson(id: 1, status: 'pending'),
      _orderJson(id: 2, status: 'confirmed'),
      _orderJson(id: 3, status: 'completed'),
      _orderJson(id: 4, status: 'cancelled'),
      _orderJson(id: 5, status: 'archived'),
    ]));
    final auth = await _loggedInAuth(tester);
    _useTallScreen(tester);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);

    expect(find.text('待确认'), findsOneWidget);
    expect(find.text('已确认'), findsOneWidget);
    expect(find.text('已完成'), findsOneWidget);
    expect(find.text('已取消'), findsOneWidget);
    // 未知状态不能裸露后端英文变量。
    expect(find.text('archived'), findsNothing);
    expect(find.text('未知状态'), findsOneWidget);
    // 时间按当前语言格式化，不直接展示 ISO 字符串。
    expect(find.textContaining('下单时间'), findsNWidgets(5));
    expect(find.textContaining('T10:00:00'), findsNothing);
    expect(find.textContaining('2026-01-01'), findsNothing);
    // 仅待确认订单提供取消入口。
    expect(find.widgetWithText(TextButton, '取消预约'), findsOneWidget);
  });

  testWidgets('取消待确认订单成功后刷新为已取消', (tester) async {
    var cancelled = false;
    var listCalls = 0;
    _installFakeApi((options) {
      if (options.method == 'POST' && options.path.contains('/cancel')) {
        cancelled = true;
        return _jsonBody(_orderJson(id: 7, status: 'cancelled'));
      }
      if (options.path.contains('/bookings')) {
        listCalls++;
        return _jsonBody([
          _orderJson(id: 7, status: cancelled ? 'cancelled' : 'pending'),
        ]);
      }
      return _bookingRoutes(bookings: <Object>[])(options);
    });
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);
    expect(find.text('待确认'), findsOneWidget);
    expect(listCalls, 1);

    await tester.tap(find.widgetWithText(TextButton, '取消预约'));
    await _pumpFrames(tester);
    expect(find.text('确认取消'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, '确认取消'));
    await _pumpFrames(tester);

    expect(find.text('预约已取消'), findsOneWidget);
    expect(find.text('已取消'), findsOneWidget);
    expect(find.text('待确认'), findsNothing);
    expect(listCalls, 2);
  });

  testWidgets('取消订单 409 提示当前状态不可取消', (tester) async {
    var listCalls = 0;
    _installFakeApi((options) {
      if (options.method == 'POST' && options.path.contains('/cancel')) {
        return _jsonBody(
          {'detail': 'Only pending bookings can be cancelled'},
          status: 409,
        );
      }
      if (options.path.contains('/bookings')) {
        listCalls++;
        return _jsonBody([_orderJson(id: 7, status: 'pending')]);
      }
      return _bookingRoutes(bookings: <Object>[])(options);
    });
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);
    await tester.tap(find.widgetWithText(TextButton, '取消预约'));
    await _pumpFrames(tester);
    await tester.tap(find.widgetWithText(FilledButton, '确认取消'));
    await _pumpFrames(tester);

    expect(find.text('该预约当前状态不可取消'), findsOneWidget);
    expect(find.text('预约不存在或无权操作'), findsNothing);
    // 状态冲突时刷新列表以同步最新状态。
    expect(listCalls, 2);
  });

  testWidgets('取消订单 404 提示不存在或无权操作', (tester) async {
    var listCalls = 0;
    _installFakeApi((options) {
      if (options.method == 'POST' && options.path.contains('/cancel')) {
        return _jsonBody({'detail': 'Booking not found'}, status: 404);
      }
      if (options.path.contains('/bookings')) {
        listCalls++;
        return _jsonBody([_orderJson(id: 7, status: 'pending')]);
      }
      return _bookingRoutes(bookings: <Object>[])(options);
    });
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await _pumpFrames(tester);
    await tester.tap(find.widgetWithText(TextButton, '取消预约'));
    await _pumpFrames(tester);
    await tester.tap(find.widgetWithText(FilledButton, '确认取消'));
    await _pumpFrames(tester);

    expect(find.text('预约不存在或无权操作'), findsOneWidget);
    expect(find.text('该预约当前状态不可取消'), findsNothing);
    expect(listCalls, 2);
  });

  testWidgets('医疗列表加载中显示静态骨架并保持可稳定等待', (tester) async {
    final semantics = tester.ensureSemantics();
    _installHangingApi();

    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await tester.pump();

    expect(find.byType(SkeletonBox), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    // 读屏只播报一次"加载中"，不会逐个念占位块。
    expect(find.bySemanticsLabel('加载中…'), findsOneWidget);

    // 静态占位没有循环动画，pumpAndSettle 必须能正常结束。
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    semantics.dispose();
  });

  testWidgets('订单列表加载中显示静态骨架并保持可稳定等待', (tester) async {
    _installFakeApi(_bookingRoutes(bookings: <Object>[]));
    final auth = await _loggedInAuth(tester);
    _installHangingApi();

    await tester.pumpWidget(_app(home: const BookingsScreen(), auth: auth));
    await tester.pump();

    expect(find.byType(SkeletonBox), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);

    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('医疗列表按分类筛选且刷新后不重置', (tester) async {
    _installFakeApi(_medicalRoutes());
    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await _pumpFrames(tester);
    expect(find.byType(ServiceCard), findsNWidgets(2));

    await tester.tap(find.widgetWithText(ChoiceChip, '牙科'));
    await tester.pump();

    expect(find.byType(ServiceCard), findsOneWidget);
    expect(find.text('微创种植牙'), findsOneWidget);
    expect(find.text('膝关节置换手术'), findsNothing);

    // 下拉刷新只更新数据，不应把用户选择的分类重置。
    await tester.drag(find.byType(ListView), const Offset(0, 260));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await _pumpFrames(tester);

    expect(find.byType(ServiceCard), findsOneWidget);
    expect(find.text('微创种植牙'), findsOneWidget);
  });

  testWidgets('医疗列表筛空时显示筛选空态并可清除', (tester) async {
    _installFakeApi(_medicalRoutes());
    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await _pumpFrames(tester);

    await tester.tap(find.widgetWithText(ChoiceChip, '骨科'));
    await tester.pump();
    await tester.tap(find.widgetWithText(ChoiceChip, '5,000 以下'));
    await tester.pump();

    // 与「后端本来就没有数据」的空态文案区分。
    expect(find.text('没有符合筛选的服务'), findsOneWidget);
    expect(find.text('暂无可预约服务'), findsNothing);

    await tester.tap(find.text('清除筛选').last);
    await tester.pump();

    expect(find.text('没有符合筛选的服务'), findsNothing);
    expect(find.byType(ServiceCard), findsNWidgets(2));
  });

  testWidgets('医疗列表按价格排序', (tester) async {
    _installFakeApi(_medicalRoutes());
    _useTallScreen(tester);
    await tester.pumpWidget(_app(home: const MedicalListScreen()));
    await _pumpFrames(tester);

    await tester.tap(find.widgetWithText(ChoiceChip, '价格从低到高'));
    await tester.pump();
    expect(_visibleServiceNames(tester), ['微创种植牙', '膝关节置换手术']);

    await tester.tap(find.widgetWithText(ChoiceChip, '价格从高到低'));
    await tester.pump();
    expect(_visibleServiceNames(tester), ['膝关节置换手术', '微创种植牙']);
  });

  testWidgets('预约表单的键盘动作按顺序连贯', (tester) async {
    _installFakeApi(_medicalRoutes());
    _useTallScreen(tester);
    await tester.pumpWidget(_app(home: const BookingScreen(serviceId: '1')));
    await _pumpFrames(tester);

    final actions = tester
        .widgetList<TextField>(find.byType(TextField))
        .map((field) => field.textInputAction)
        .toList();
    expect(actions, [
      TextInputAction.next,
      TextInputAction.next,
      TextInputAction.next,
      TextInputAction.done,
    ]);
  });

  testWidgets('服务详情横屏：主内容可见且底部操作条避开手势区', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(800, 400);
    addTearDown(tester.view.reset);
    _installFakeApi(_medicalRoutes());

    await tester.pumpWidget(
      _app(
        home: const ServiceDetailScreen(serviceId: '1'),
        padding: const EdgeInsets.only(bottom: 24),
      ),
    );
    await _pumpFrames(tester);

    // 底部条高度 = 14 + 52 + 14 + 24 安全区；横屏 400 高时从 296 开始。
    final button = tester.getRect(find.byType(FilledButton).last);
    expect(button.bottom, lessThanOrEqualTo(400 - 24));

    // hero 高度被限制为屏高的 55%（220），标题仍在首屏且不被操作条覆盖。
    final title = tester.getRect(find.text('膝关节置换手术'));
    expect(title.top, lessThan(296));
    expect(tester.takeException(), isNull);
  });
}

/// 健康之旅列表的两条样例数据。
ResponseBody Function(RequestOptions) _medicalRoutes() {
  return (options) {
    if (options.path.contains('/medical/packages')) {
      return _jsonBody({
        'items': [_packageJson, _packageJson2],
      });
    }
    return _jsonBody(<Object>[]);
  };
}

/// 当前列表顺序下的服务名称，用于验证排序结果。
List<String> _visibleServiceNames(WidgetTester tester) {
  return tester
      .widgetList<ServiceCard>(find.byType(ServiceCard))
      .map((card) => card.service.nameZh)
      .toList();
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

/// 模拟请求一直挂起，用于验证加载骨架的稳定性。
void _installHangingApi() {
  final dio = Dio(BaseOptions(baseUrl: 'http://fake.local/api/v1'))
    ..httpClientAdapter = _HangingAdapter();
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
  EdgeInsets padding = EdgeInsets.zero,
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
        padding: padding,
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

/// 加高视口，确保多张订单卡片都被 ListView 构建出来。
void _useTallScreen(WidgetTester tester) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(800, 1400);
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

class _HangingAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    return Completer<ResponseBody>().future;
  }

  @override
  void close({bool force = false}) {}
}
