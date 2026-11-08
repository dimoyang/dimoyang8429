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
import 'package:meditour_app/presentation/screens/booking_screen.dart';
import 'package:meditour_app/presentation/screens/service_detail_screen.dart';
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

const _bookingResultJson = {
  'id': 7,
  'order_no': 'MT202601010000AB',
  'total_price': 15000,
  'currency': 'EUR',
  'status': 'pending',
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

  testWidgets('服务详情错误态显示并可重试', (tester) async {
    var failing = true;
    _installFakeApi((options) {
      if (failing) {
        return _jsonBody({'detail': 'boom'}, status: 500);
      }
      return _serviceRoutes(options);
    });

    await tester
        .pumpWidget(_app(home: const ServiceDetailScreen(serviceId: '1')));
    await _pumpFrames(tester);

    // AppBar 与错误体各出现一次「加载失败」。
    expect(find.text('加载失败'), findsNWidgets(2));
    expect(find.widgetWithText(FilledButton, '重试'), findsOneWidget);

    failing = false;
    await tester.tap(find.widgetWithText(FilledButton, '重试'));
    await _pumpFrames(tester);

    // 首屏只有大图，向上滚动后标题进入视口。
    await tester.drag(find.byType(ListView), const Offset(0, -400));
    await _pumpFrames(tester);

    expect(find.text('加载失败'), findsNothing);
    expect(find.text('膝关节置换手术'), findsOneWidget);
  });

  testWidgets('服务详情在 320dp 与 1.3 倍字号下不溢出', (tester) async {
    _installFakeApi(_serviceRoutes);
    _useNarrowScreen(tester);

    await tester.pumpWidget(
      _app(home: const ServiceDetailScreen(serviceId: '1'), textScale: 1.3),
    );
    await _pumpFrames(tester);

    expect(tester.takeException(), isNull);
    expect(find.text('膝关节置换手术'), findsOneWidget);
    expect(find.text('预约咨询'), findsOneWidget);
  });

  testWidgets('预约页未选日期时在表单内联提示', (tester) async {
    _installFakeApi(_bookingRoutes);
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(
      _app(home: const BookingScreen(serviceId: '1'), auth: auth),
    );
    await _pumpFrames(tester);

    await _fillContactFields(tester);
    await _scrollTo(tester, find.widgetWithText(FilledButton, '提交预约'));
    await tester.tap(find.widgetWithText(FilledButton, '提交预约'));
    await _pumpFrames(tester);

    expect(find.text('请选择期望到诊日期'), findsOneWidget);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('预约成功页在 320dp 与 1.3 倍字号下可滚动不溢出', (tester) async {
    _installFakeApi(_bookingRoutes);
    final auth = await _loggedInAuth(tester);
    _useNarrowScreen(tester);

    await tester.pumpWidget(
      _app(
        home: const BookingScreen(serviceId: '1'),
        auth: auth,
        textScale: 1.3,
      ),
    );
    await _pumpFrames(tester);

    await _fillContactFields(tester);
    final dateField = find.ancestor(
      of: find.text('请选择日期'),
      matching: find.byType(InkWell),
    );
    await _scrollTo(tester, dateField);
    // 直接触发日期字段的点击回调：窄屏大字号下日期字段的命中点会随滚动位置变化，
    // 本用例关注的是成功页布局，无需复现真实手势。
    tester.widget<InkWell>(dateField).onTap!();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('确定'));
    await _pumpFrames(tester);

    await _scrollTo(tester, find.widgetWithText(FilledButton, '提交预约'));
    await tester.tap(find.widgetWithText(FilledButton, '提交预约'));
    await _pumpFrames(tester);

    expect(tester.takeException(), isNull);
    expect(find.text('预约提交成功'), findsOneWidget);
    expect(find.byType(SingleChildScrollView), findsWidgets);
  });
}

/// 服务详情依赖的套餐与医院两个端点。
ResponseBody _serviceRoutes(RequestOptions options) {
  if (options.path.contains('/medical/packages')) {
    return _jsonBody({
      'items': [_packageJson],
    });
  }
  return _jsonBody(<Object>[]);
}

/// 预约页涉及的服务、登录与创建订单端点。
ResponseBody _bookingRoutes(RequestOptions options) {
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
  if (options.method == 'POST' && options.path.contains('/bookings')) {
    return _jsonBody(_bookingResultJson, status: 201);
  }
  return _serviceRoutes(options);
}

Future<void> _fillContactFields(WidgetTester tester) async {
  final fields = find.byType(TextFormField);
  expect(fields, findsAtLeastNWidgets(3));
  await tester.enterText(fields.at(0), 'Alice');
  await tester.enterText(fields.at(1), '13800138000');
  await tester.enterText(fields.at(2), 'alice@example.com');
}

/// 表单是懒加载 ListView，先把目标控件滚入视口再操作。
Future<void> _scrollTo(WidgetTester tester, Finder target) async {
  await tester.dragUntilVisible(
    target,
    find.byType(ListView),
    const Offset(0, -150),
  );
  // 大字号窄屏下目标可能只是部分露出，补一次 ensureVisible 再点击。
  await tester.ensureVisible(target);
  await tester.pump();
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
