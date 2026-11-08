import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/screens/change_password_screen.dart';
import 'package:meditour_app/presentation/screens/forgot_password_screen.dart';
import 'package:meditour_app/presentation/screens/login_screen.dart';
import 'package:meditour_app/presentation/screens/register_screen.dart';
import 'package:meditour_app/presentation/screens/reset_password_screen.dart';

Widget _app({required Widget home, double keyboardInset = 0}) {
  return MaterialApp(
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
        viewInsets: EdgeInsets.only(bottom: keyboardInset),
      ),
      child: child!,
    ),
    home: home,
  );
}

List<TextInputAction?> _actions(WidgetTester tester) {
  return tester
      .widgetList<TextField>(find.byType(TextField))
      .map((field) => field.textInputAction)
      .toList();
}

void main() {
  testWidgets('登录页：下一项跳转密码，完成键触发校验', (tester) async {
    await tester.pumpWidget(_app(home: const LoginScreen()));
    expect(_actions(tester), [TextInputAction.next, TextInputAction.done]);

    await tester.enterText(find.byType(TextField).first, 'bad-email');
    await tester.testTextInput.receiveAction(TextInputAction.next);
    await tester.pump();

    final editables =
        tester.widgetList<EditableText>(find.byType(EditableText));
    expect(editables.last.focusNode.hasFocus, isTrue);

    await tester.enterText(find.byType(TextField).last, '123');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(find.text('请输入有效的邮箱地址'), findsOneWidget);
    expect(find.text('密码至少 6 位'), findsOneWidget);
  });

  testWidgets('多字段表单的键盘动作按顺序连贯', (tester) async {
    await tester.pumpWidget(_app(home: const RegisterScreen()));
    expect(_actions(tester), [
      TextInputAction.next,
      TextInputAction.next,
      TextInputAction.next,
      TextInputAction.done,
    ]);

    await tester.pumpWidget(_app(home: const ResetPasswordScreen()));
    expect(_actions(tester), [
      TextInputAction.next,
      TextInputAction.next,
      TextInputAction.done,
    ]);

    await tester.pumpWidget(_app(home: const ChangePasswordScreen()));
    expect(_actions(tester), [
      TextInputAction.next,
      TextInputAction.next,
      TextInputAction.done,
    ]);

    await tester.pumpWidget(_app(home: const ForgotPasswordScreen()));
    expect(_actions(tester), [TextInputAction.done]);
  });

  testWidgets('键盘弹出时焦点字段自动滚动到可见区域', (tester) async {
    await tester.pumpWidget(
      _app(home: const ResetPasswordScreen(), keyboardInset: 300),
    );

    await tester.showKeyboard(find.byType(TextField).last);
    await tester.pumpAndSettle();

    final rect = tester.getRect(find.byType(TextField).last);
    expect(rect.bottom, lessThanOrEqualTo(600 - 300));
    expect(tester.takeException(), isNull);
  });
}
