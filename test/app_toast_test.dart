import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/presentation/widgets/app_toast.dart';

void main() {
  testWidgets('成功提示使用统一位置与时长', (tester) async {
    await tester.pumpWidget(
      _ToastHost(onPressed: (context) => AppToast.success(context, '已保存')),
    );
    await tester.tap(find.text('show'));
    await tester.pump();

    expect(find.text('已保存'), findsOneWidget);
    final snackBar = tester.widget<SnackBar>(find.byType(SnackBar));
    expect(snackBar.behavior, SnackBarBehavior.floating);
    expect(snackBar.duration, AppToast.duration);
  });

  testWidgets('错误提示出现时读屏可播报', (tester) async {
    final semantics = tester.ensureSemantics();
    await tester.pumpWidget(
      _ToastHost(onPressed: (context) => AppToast.error(context, '保存失败')),
    );
    await tester.tap(find.text('show'));
    await tester.pump();

    expect(find.text('保存失败'), findsOneWidget);
    // SnackBar 以 live region 呈现，出现即触发读屏播报。
    expect(_hasLiveRegion(), findsOneWidget);
    semantics.dispose();
  });

  testWidgets('信息提示展示传入文案', (tester) async {
    await tester.pumpWidget(
      _ToastHost(onPressed: (context) => AppToast.info(context, '功能即将上线')),
    );
    await tester.tap(find.text('show'));
    await tester.pump();

    expect(find.text('功能即将上线'), findsOneWidget);
  });
}

/// 查找声明了 live region 的 Semantics 组件。
Finder _hasLiveRegion() {
  return find.byWidgetPredicate(
    (widget) => widget is Semantics && widget.properties.liveRegion == true,
  );
}

class _ToastHost extends StatelessWidget {
  final void Function(BuildContext context) onPressed;

  const _ToastHost({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => Center(
            child: FilledButton(
              onPressed: () => onPressed(context),
              child: const Text('show'),
            ),
          ),
        ),
      ),
    );
  }
}
