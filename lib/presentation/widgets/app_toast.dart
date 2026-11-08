import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 提示语义类型。
enum AppToastKind {
  success,
  info,
  error,
}

/// 应用统一的轻提示入口。
///
/// 成功、信息、错误三类共用位置、时长与排版，避免各页面自行实现导致
/// 提示位置和停留时间不一致。SnackBar 以 live region 呈现内容，错误提示
/// 出现时屏幕阅读器会立即播报。
class AppToast {
  AppToast._();

  /// 统一停留时长：足够读完一行提示，又不会长时间遮挡内容。
  static const Duration duration = Duration(seconds: 3);

  static void success(BuildContext context, String message) {
    _show(context, message, AppToastKind.success);
  }

  static void info(BuildContext context, String message) {
    _show(context, message, AppToastKind.info);
  }

  static void error(BuildContext context, String message) {
    _show(context, message, AppToastKind.error);
  }

  static void _show(
    BuildContext context,
    String message,
    AppToastKind kind,
  ) {
    final (IconData icon, Color background) = switch (kind) {
      AppToastKind.success => (
          Icons.check_circle_outline,
          AppColors.primaryDark
        ),
      AppToastKind.info => (Icons.info_outline, AppColors.ink),
      AppToastKind.error => (Icons.error_outline, AppColors.danger),
    };

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        duration: duration,
        backgroundColor: background,
        // SnackBar 自身以 live region 呈现内容，错误提示出现时读屏会立即播报。
        content: Row(
          children: [
            ExcludeSemantics(
              child: Icon(icon, size: 20, color: Colors.white),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13.5,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
