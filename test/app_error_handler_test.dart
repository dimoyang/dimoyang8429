import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/core/errors/app_error_handler.dart';
import 'package:meditour_app/l10n/app_localizations.dart';

final _details = FlutterErrorDetails(
  exception: StateError('internal-secret'),
  stack: StackTrace.empty,
  library: 'meditour test',
);

Widget _app(Locale locale) {
  final errorView = AppErrorHandler.buildErrorWidget(_details);
  return MaterialApp(
    locale: locale,
    supportedLocales: AppConstants.supportedLocales,
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: errorView,
  );
}

void main() {
  testWidgets('错误兜底界面按语言展示友好文案且不暴露技术细节', (tester) async {
    const expected = {
      'en': (
        "This page couldn't load",
        'Something went wrong. Please try again in a moment.',
      ),
      'zh': ('页面暂时无法显示', '出了点问题，请稍后重试。'),
      'de': (
        'Diese Seite konnte nicht geladen werden',
        'Etwas ist schiefgelaufen. Bitte versuchen Sie es gleich noch einmal.',
      ),
      'fr': (
        "Cette page n'a pas pu se charger",
        'Un problème est survenu. Veuillez réessayer dans un instant.',
      ),
    };

    for (final entry in expected.entries) {
      await tester.pumpWidget(_app(Locale(entry.key)));
      final (title, body) = entry.value;
      expect(find.text(title), findsOneWidget);
      expect(find.text(body), findsOneWidget);

      final texts = tester
          .widgetList<Text>(find.byType(Text))
          .map((text) => text.data ?? '')
          .join('\n');
      expect(texts, isNot(contains('StateError')));
      expect(texts, isNot(contains('internal-secret')));
      expect(texts, isNot(contains('Stack')));
    }
  });

  test('未捕获的异步异常会被记录而不是静默吞掉', () {
    final originalOnError = FlutterError.onError;
    final captured = <FlutterErrorDetails>[];
    FlutterError.onError = captured.add;
    addTearDown(() => FlutterError.onError = originalOnError);

    final error = StateError('async boom');
    expect(AppErrorHandler.reportAsyncError(error, StackTrace.current), isTrue);

    expect(captured, hasLength(1));
    expect(captured.single.exception, error);
    expect(captured.single.stack, isNotNull);
  });

  test('安装兜底后构建异常使用友好界面组件', () {
    final originalBuilder = ErrorWidget.builder;
    final originalOnError = FlutterError.onError;
    final originalAsync = PlatformDispatcher.instance.onError;
    addTearDown(() {
      ErrorWidget.builder = originalBuilder;
      FlutterError.onError = originalOnError;
      PlatformDispatcher.instance.onError = originalAsync;
    });

    AppErrorHandler.install();
    expect(AppErrorHandler.buildErrorWidget(_details), isA<AppErrorView>());
    expect(ErrorWidget.builder(_details), isA<AppErrorView>());
  });
}
