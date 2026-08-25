import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/app/app.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'language_code': 'zh'});
  });

  testWidgets('main shell navigates across four travel tabs', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MeditourApp());
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('发现'), findsOneWidget);
    expect(find.text('特色服务 · 健康之旅'), findsNothing);

    await tester.tap(find.text('行程'));
    await tester.pumpAndSettle();
    expect(find.text('还没有行程'), findsOneWidget);

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
