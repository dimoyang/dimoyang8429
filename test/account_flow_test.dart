import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/core/network/token_store.dart';
import 'package:meditour_app/core/utils/route_location.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/screens/change_password_screen.dart';
import 'package:meditour_app/presentation/screens/delete_account_screen.dart';
import 'package:meditour_app/presentation/screens/forgot_password_screen.dart';
import 'package:meditour_app/presentation/screens/profile_screen.dart';
import 'package:meditour_app/presentation/screens/reset_password_screen.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    TokenStore.resetForTesting();
  });

  testWidgets('忘记密码：成功提示不暴露邮箱是否存在', (tester) async {
    var requests = 0;
    _installFakeApi((options) {
      if (options.path.contains('/auth/password-reset/request')) {
        requests++;
      }
      return _jsonBody({'detail': 'ok'});
    });

    await tester.pumpWidget(
      _app(home: const ForgotPasswordScreen(), auth: AuthProvider()),
    );
    await tester.enterText(find.byType(TextFormField), 'alice@example.com');
    await tester.tap(find.widgetWithText(FilledButton, '发送重置邮件'));
    await _pumpFrames(tester);

    expect(requests, 1);
    expect(
      find.text('如果该邮箱已注册，我们已发送密码重置邮件，请稍候几分钟查看。'),
      findsOneWidget,
    );
    // 不能出现"邮箱不存在/未注册"之类的账号枚举提示。
    expect(find.textContaining('不存在'), findsNothing);
    expect(find.textContaining('未注册'), findsNothing);
  });

  testWidgets('重置密码：无效令牌 400 显示专用提示', (tester) async {
    _installFakeApi(
      (options) => _jsonBody({'detail': 'invalid token'}, status: 400),
    );

    await tester.pumpWidget(
      _app(
        home: const ResetPasswordScreen(token: 'bad-token'),
        auth: AuthProvider(),
      ),
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'newpass1');
    await tester.enterText(find.byType(TextFormField).at(2), 'newpass1');
    await tester.tap(find.widgetWithText(FilledButton, '设置新密码'));
    await _pumpFrames(tester);

    expect(find.text('重置令牌无效或已过期，请重新申请。'), findsOneWidget);
  });

  testWidgets('修改密码：当前密码错误 400 与网络失败区分提示', (tester) async {
    _installFakeApi(
      (options) => _jsonBody({'detail': 'wrong password'}, status: 400),
    );

    await tester.pumpWidget(
      _app(home: const ChangePasswordScreen(), auth: AuthProvider()),
    );
    await tester.enterText(find.byType(TextFormField).at(0), 'old-pass');
    await tester.enterText(find.byType(TextFormField).at(1), 'new-pass1');
    await tester.enterText(find.byType(TextFormField).at(2), 'new-pass1');
    await tester.tap(find.widgetWithText(FilledButton, '更新密码'));
    await _pumpFrames(tester);

    expect(find.text('当前密码不正确。'), findsOneWidget);
  });

  testWidgets('修改密码成功显示重新登录引导', (tester) async {
    _installFakeApi((options) {
      if (options.path.contains('/auth/login')) {
        return _jsonBody({
          'access_token': 'token-123',
          'refresh_token': 'refresh-123',
        });
      }
      if (options.path.contains('/auth/change-password')) {
        return _jsonBody({'detail': 'ok'});
      }
      return _jsonBody({'id': 1, 'email': 'alice@example.com'});
    });
    final auth = await _loggedInAuth(tester);

    await tester.pumpWidget(
      _app(home: const ChangePasswordScreen(), auth: auth),
    );
    await tester.enterText(find.byType(TextFormField).at(0), 'old-pass');
    await tester.enterText(find.byType(TextFormField).at(1), 'new-pass1');
    await tester.enterText(find.byType(TextFormField).at(2), 'new-pass1');
    await tester.tap(find.widgetWithText(FilledButton, '更新密码'));
    await _pumpFrames(tester);

    expect(find.text('密码已修改，请重新登录。'), findsOneWidget);
  });

  testWidgets('注销账号：密码错误 400 显示密码错误', (tester) async {
    _installFakeApi(
      (options) => _jsonBody({'detail': 'wrong password'}, status: 400),
    );

    await tester.pumpWidget(
      _app(home: const DeleteAccountScreen(), auth: AuthProvider()),
    );
    await tester.enterText(find.byType(TextFormField), 'old-pass');
    await tester.tap(find.widgetWithText(FilledButton, '确认注销账号'));
    await _pumpFrames(tester);
    // 二次确认：对话框里的确认按钮。
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.widgetWithText(FilledButton, '确认注销账号'),
      ),
    );
    await _pumpFrames(tester);

    expect(find.text('密码不正确。'), findsOneWidget);
  });

  test('修改密码成功会清会话，不能停留在已登录状态', () async {
    _installFakeApi((options) {
      if (options.path.contains('/auth/change-password')) {
        return _jsonBody({'detail': 'ok'});
      }
      return _jsonBody({'id': 1, 'email': 'alice@example.com'});
    });
    await TokenStore.save('access-old', refreshToken: 'refresh-old');
    final auth = AuthProvider();
    await auth.init();
    expect(auth.isLoggedIn, isTrue);

    await auth.changePassword(
        currentPassword: 'old-pass', newPassword: 'new-pass1');

    expect(auth.isLoggedIn, isFalse);
    expect(TokenStore.current, isNull);
    expect(TokenStore.refreshToken, isNull);
  });

  test('注销账号成功会清会话', () async {
    _installFakeApi((options) {
      if (options.path.contains('/auth/account')) {
        return _jsonBody({'detail': 'deleted'});
      }
      return _jsonBody({'id': 1, 'email': 'alice@example.com'});
    });
    await TokenStore.save('access-old', refreshToken: 'refresh-old');
    final auth = AuthProvider();
    await auth.init();
    expect(auth.isLoggedIn, isTrue);

    await auth.deleteAccount('old-pass');

    expect(auth.isLoggedIn, isFalse);
    expect(TokenStore.current, isNull);
  });

  test('重置密码成功会作废旧会话', () async {
    _installFakeApi((options) {
      if (options.path.contains('/auth/password-reset/confirm')) {
        return _jsonBody({'detail': 'ok'});
      }
      return _jsonBody({'id': 1, 'email': 'alice@example.com'});
    });
    await TokenStore.save('access-old', refreshToken: 'refresh-old');
    final auth = AuthProvider();
    await auth.init();
    expect(auth.isLoggedIn, isTrue);

    await auth.confirmPasswordReset(
        token: 'reset-token', newPassword: 'new-pass1');

    expect(auth.isLoggedIn, isFalse);
    expect(TokenStore.current, isNull);
    expect(TokenStore.refreshToken, isNull);
  });

  testWidgets('导出数据在非 Web 平台降级为预览并提示复制', (tester) async {
    _installFakeApi((options) {
      if (options.path.contains('/auth/login')) {
        return _jsonBody({
          'access_token': 'token-123',
          'refresh_token': 'refresh-123',
        });
      }
      if (options.path.contains('/auth/export')) {
        return _jsonBody({
          'email': 'alice@example.com',
          'bookings': <Object>[],
        });
      }
      return _jsonBody({'id': 1, 'email': 'alice@example.com'});
    });
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(800, 1400);
    addTearDown(tester.view.reset);

    final auth = await _loggedInAuth(tester);
    await tester.pumpWidget(
      _app(
        home: const ProfileScreen(),
        auth: auth,
        language: LanguageProvider(initialCode: 'zh'),
      ),
    );
    await _pumpFrames(tester);

    await tester.tap(find.text('导出我的数据'));
    await _pumpFrames(tester);

    expect(find.text('我的数据'), findsOneWidget);
    expect(
      find.text('当前平台不支持直接保存文件，可复制下方的 JSON 后自行保存。'),
      findsOneWidget,
    );
    expect(find.byType(SelectableText), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '复制 JSON'), findsOneWidget);
  });

  testWidgets('修改密码入口带 redirect=/profile，登录后回原页面', (tester) async {
    // 入口参数由 ProfileScreen 传给路由；这里验证登录页地址拼接规则。
    expect(loginLocation(redirect: '/profile'), '/login?redirect=%2Fprofile');
    expect(loginLocation(redirect: 'https://evil.example.com'), '/login');
    expect(loginLocation(redirect: null), '/login');
  });
}

Widget _app({
  required Widget home,
  AuthProvider? auth,
  LanguageProvider? language,
}) {
  Widget child = MaterialApp(
    locale: const Locale('zh'),
    supportedLocales: AppConstants.supportedLocales,
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: home,
  );
  if (language != null) {
    child = ChangeNotifierProvider<LanguageProvider>.value(
      value: language,
      child: child,
    );
  }
  if (auth != null) {
    child =
        ChangeNotifierProvider<AuthProvider>.value(value: auth, child: child);
  }
  return child;
}

Future<void> _pumpFrames(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  await tester.pump(const Duration(milliseconds: 300));
  await tester.pump(const Duration(milliseconds: 300));
}

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
