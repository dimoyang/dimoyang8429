import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/app/app.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/data/models/travel_itinerary.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/destination_card.dart';
import 'package:meditour_app/presentation/widgets/service_card.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'language_code': 'zh'});
  });

  test('language provider honors the injected initial locale', () {
    expect(
      LanguageProvider(initialCode: 'zh').currentLocale.languageCode,
      'zh',
    );
    expect(
      LanguageProvider(initialCode: 'en').currentLocale.languageCode,
      'en',
    );
    expect(LanguageProvider().currentLocale.languageCode, 'en');
  });

  test('starting price drops decimals and groups thousands', () {
    final service = ServiceRepository.sampleServices.first;

    expect(service.basePrice, 15000);
    expect(service.priceFrom, 'EUR 15,000');
  });

  testWidgets('app assembles providers and renders English when injected', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MeditourApp(initialLanguageCode: 'en'));
    await tester.pumpAndSettle();

    expect(find.text('Discover'), findsOneWidget);

    final context = tester.element(find.byType(NavigationBar));
    expect(context.read<LanguageProvider>().currentLocale.languageCode, 'en');
    expect(context.read<AuthProvider>(), isNotNull);
    expect(context.read<ItineraryProvider>(), isNotNull);
    expect(context.read<FavoritesProvider>(), isNotNull);
    expect(context.read<DestinationProvider>(), isNotNull);
  });

  testWidgets('service card lays out under unbounded ListView height', (
    WidgetTester tester,
  ) async {
    final service = ServiceRepository.sampleServices.first;

    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('zh'),
        supportedLocales: AppConstants.supportedLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: ListView(children: [ServiceCard(service: service)]),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text(service.nameZh), findsOneWidget);
  });

  test('favorite destinations persist across provider instances', () async {
    final firstProvider = FavoritesProvider();
    await firstProvider.load();
    await firstProvider.toggleDestination('beijing');

    final restoredProvider = FavoritesProvider();
    await restoredProvider.load();

    expect(restoredProvider.isFavorite('beijing'), isTrue);
  });

  testWidgets('main shell navigates across four travel tabs', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MeditourApp(initialLanguageCode: 'zh'));
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('发现'), findsOneWidget);
    expect(find.text('特色服务 · 健康之旅'), findsNothing);

    await tester.tap(find.text('搜索目的地、景点、美食…'));
    await tester.pumpAndSettle();
    expect(find.byType(TextField), findsOneWidget);

    // 搜索输入有 280ms 防抖，等待防抖窗口过去再断言筛选结果。
    await tester.enterText(find.byType(TextField), 'Great Wall');
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(DestinationCard), findsOneWidget);

    await tester.enterText(find.byType(TextField), '上海');
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(DestinationCard), findsOneWidget);

    await tester.tap(find.byTooltip('收藏目的地'));
    await tester.pump();
    await tester.tap(find.text('已收藏'));
    await tester.pump();
    expect(find.byType(DestinationCard), findsOneWidget);
    expect(find.byTooltip('取消收藏'), findsOneWidget);

    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();

    await tester.tap(find.text('行程'));
    await tester.pumpAndSettle();
    expect(find.text('还没有行程'), findsOneWidget);

    await tester.tap(find.byKey(const Key('createItineraryButton')));
    await tester.pumpAndSettle();
    expect(find.text('创建行程'), findsOneWidget);
    expect(find.byKey(const Key('itineraryTitleField')), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const Key('itinerarySaveButton')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const Key('itinerarySaveButton')));
    await tester.pump();
    expect(find.text('请选择旅行日期'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('请输入行程名称'),
      -300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('请输入行程名称'), findsOneWidget);
    expect(find.text('请至少选择一个目的地'), findsOneWidget);

    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();

    await tester.tap(find.text('旅行工具'));
    await tester.pumpAndSettle();
    expect(find.text('签证与入境'), findsOneWidget);
    expect(find.text('支付准备'), findsOneWidget);

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();
    expect(find.text('偏好设置'), findsOneWidget);
    expect(find.text('特色服务 · 健康之旅'), findsOneWidget);
  });

  testWidgets('itinerary editor keeps per-day place arrangement on save', (
    WidgetTester tester,
  ) async {
    final start = DateTime(2026, 12, 1);
    final end = DateTime(2026, 12, 2);
    final seeded = TravelItinerary(
      id: 'trip_test',
      title: '测试行程',
      startDate: start,
      endDate: end,
      destinationIds: const ['beijing', 'shanghai'],
      days: const [
        ItineraryDay(dayNumber: 1, destinationIds: ['beijing']),
        ItineraryDay(dayNumber: 2),
      ],
      notes: '',
      createdAt: start,
      updatedAt: start,
    );
    SharedPreferences.setMockInitialValues({
      'language_code': 'zh',
      'travel_itineraries': [jsonEncode(seeded.toJson())],
    });

    await tester.pumpWidget(const MeditourApp(initialLanguageCode: 'zh'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('行程'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('测试行程'));
    await tester.pumpAndSettle();

    expect(find.text('第 1 天'), findsOneWidget);

    // 第一天已有北京，从弹层里把上海加入这一天。
    await tester.tap(find.text('添加地点').first);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, '上海'));
    await tester.pumpAndSettle();
    expect(find.text('上海'), findsNWidgets(2));

    // 把上海上移到北京之前，再保存，确认按天顺序被持久化。
    await tester.tap(find.byTooltip('下移').first);
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.byKey(const Key('itinerarySaveButton')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const Key('itinerarySaveButton')));
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(NavigationBar));
    final saved = context.read<ItineraryProvider>().findById('trip_test');
    expect(saved, isNotNull);
    expect(saved!.days.first.destinationIds, ['shanghai', 'beijing']);
    expect(saved.days[1].destinationIds, isEmpty);
  });
}
