import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/screens/destination_search_screen.dart';
import 'package:meditour_app/presentation/widgets/destination_card.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _recentKey = 'recent_destination_searches';

void main() {
  testWidgets('最近搜索可点击应用、单条删除与清空', (tester) async {
    SharedPreferences.setMockInitialValues({
      _recentKey: ['北京', '上海'],
    });
    await _pumpSearch(tester);

    expect(find.text('最近搜索'), findsOneWidget);
    expect(find.widgetWithText(InputChip, '北京'), findsOneWidget);
    expect(find.widgetWithText(InputChip, '上海'), findsOneWidget);

    await tester.tap(find.widgetWithText(InputChip, '北京'));
    await _pumpDebounce(tester);

    // 应用最近搜索后输入框有值，只应展示北京。
    expect(find.text('最近搜索'), findsNothing);
    expect(find.byType(DestinationCard), findsOneWidget);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getStringList(_recentKey)!.first, '北京');

    await tester.tap(find.byTooltip('清空搜索'));
    await _pumpDebounce(tester);
    expect(find.text('最近搜索'), findsOneWidget);

    // 单条删除只移除对应记录。
    await tester.tap(
      find.descendant(
        of: find.widgetWithText(InputChip, '上海'),
        matching: find.byTooltip('删除这条搜索记录'),
      ),
    );
    await tester.pump();
    expect(find.widgetWithText(InputChip, '上海'), findsNothing);
    expect(find.widgetWithText(InputChip, '北京'), findsOneWidget);
    expect((await SharedPreferences.getInstance()).getStringList(_recentKey), [
      '北京',
    ]);

    // 清空全部后不再展示最近搜索区域。
    await tester.tap(find.widgetWithText(TextButton, '清空'));
    await tester.pump();
    expect(find.text('最近搜索'), findsNothing);
    expect((await SharedPreferences.getInstance()).getStringList(_recentKey),
        isNull);
  });

  testWidgets('搜索无结果时给出可操作建议', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await _pumpSearch(tester);

    await tester.enterText(find.byType(TextField), '不存在的关键词');
    await _pumpDebounce(tester);

    expect(find.text('没有找到目的地'), findsOneWidget);
    expect(find.text('试试热门目的地'), findsOneWidget);
    expect(find.widgetWithText(ActionChip, '北京'), findsOneWidget);
    expect(find.text('清空搜索'), findsOneWidget);

    await tester.tap(find.widgetWithText(ActionChip, '北京'));
    await _pumpDebounce(tester);

    expect(find.text('没有找到目的地'), findsNothing);
    expect(find.byType(DestinationCard), findsOneWidget);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getStringList(_recentKey), ['北京']);
  });

  testWidgets('收藏为空时可切换到全部目的地', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await _pumpSearch(tester, loadFavorites: true);

    await tester.tap(find.text('已收藏'));
    await tester.pump();

    expect(find.text('还没有收藏'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, '在全部目的地中搜索'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, '在全部目的地中搜索'));
    await tester.pump();

    expect(find.text('还没有收藏'), findsNothing);
    expect(find.byType(DestinationCard), findsWidgets);
  });
}

Future<void> _pumpSearch(
  WidgetTester tester, {
  bool loadFavorites = false,
}) async {
  final destinationProvider = DestinationProvider();
  final favorites = FavoritesProvider();
  if (loadFavorites) {
    await tester.runAsync(favorites.load);
  }

  await tester.pumpWidget(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<DestinationProvider>.value(
          value: destinationProvider,
        ),
        ChangeNotifierProvider<FavoritesProvider>.value(value: favorites),
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
        home: const DestinationSearchScreen(),
      ),
    ),
  );
  await _pumpDebounce(tester);
}

/// 推进历史加载与 280ms 输入防抖。
Future<void> _pumpDebounce(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 320));
}
