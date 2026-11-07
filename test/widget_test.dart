import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/app/app.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/presentation/widgets/destination_card.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'language_code': 'zh'});
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

    await tester.enterText(find.byType(TextField), 'Great Wall');
    await tester.pump();
    expect(find.byType(DestinationCard), findsOneWidget);

    await tester.enterText(find.byType(TextField), '上海');
    await tester.pump();
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

    await tester.tap(find.byKey(const Key('itinerarySaveButton')));
    await tester.pump();
    expect(find.text('请输入行程名称'), findsOneWidget);
    expect(find.text('请至少选择一个目的地'), findsOneWidget);
    expect(find.text('请选择旅行日期'), findsOneWidget);

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
}
