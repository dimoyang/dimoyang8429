import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/screens/home_screen.dart';
import 'package:meditour_app/presentation/widgets/offline_data_hint.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _OfflineFallbackDestinationProvider extends DestinationProvider {
  @override
  bool get isOfflineFallback => true;

  @override
  bool get isInitialLoading => false;
}

void main() {
  testWidgets('首页在离线兜底时展示内联提示而不是骨架', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await _pumpHome(tester, _OfflineFallbackDestinationProvider());
    await _scrollToDestinations(tester);

    expect(find.byType(OfflineDataHint), findsOneWidget);
    expect(
      find.text('暂时无法连接服务器，当前显示的是示例数据。'),
      findsOneWidget,
    );
    expect(find.text('热门目的地'), findsOneWidget);
  });

  testWidgets('首页正常加载时不展示离线提示', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await _pumpHome(tester, DestinationProvider());
    await _scrollToDestinations(tester);

    expect(find.byType(OfflineDataHint), findsNothing);
  });
}

Future<void> _scrollToDestinations(WidgetTester tester) async {
  await tester.scrollUntilVisible(
    find.text('热门目的地'),
    300,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pump();
}

Future<void> _pumpHome(
  WidgetTester tester,
  DestinationProvider destinationProvider,
) async {
  await tester.pumpWidget(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<DestinationProvider>.value(
          value: destinationProvider,
        ),
        ChangeNotifierProvider(
          create: (_) => LanguageProvider(initialCode: 'zh'),
        ),
        ChangeNotifierProvider(create: (_) => FavoritesProvider()),
      ],
      child: MaterialApp(
        locale: const Locale('zh'),
        supportedLocales: AppConstants.supportedLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: const HomeScreen(),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 100));
}
