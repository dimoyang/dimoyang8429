import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/l10n/app_localizations.dart';

/// 应用级错误兜底。
///
/// - 构建异常：替换系统灰色错误块，展示用户能理解的提示界面；
/// - 框架异常与未捕获的异步异常：统一写入日志。
///
/// 界面只展示标题与说明，堆栈、异常类名等技术细节只进日志。
class AppErrorHandler {
  AppErrorHandler._();

  static void install() {
    ErrorWidget.builder = buildErrorWidget;
    FlutterError.onError = reportFlutterError;
    PlatformDispatcher.instance.onError = reportAsyncError;
  }

  /// 构建期兜底界面。语言资源尚不可用时退回英文提示。
  static Widget buildErrorWidget(FlutterErrorDetails details) {
    return const AppErrorView();
  }

  /// 框架异常统一入口：交给框架输出到控制台/崩溃采集。
  @visibleForTesting
  static void reportFlutterError(FlutterErrorDetails details) {
    FlutterError.presentError(details);
  }

  /// 未捕获的异步异常：记录后标记为已处理，避免进程直接退出。
  @visibleForTesting
  static bool reportAsyncError(Object error, StackTrace stack) {
    FlutterError.reportError(
      FlutterErrorDetails(
        exception: error,
        stack: stack,
        library: 'meditour',
        context: ErrorDescription('while running an asynchronous callback'),
      ),
    );
    return true;
  }
}

/// 友好错误界面：图标 + 标题 + 说明，不含任何技术细节。
class AppErrorView extends StatelessWidget {
  const AppErrorView({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = Localizations.of<AppLocalizations>(context, AppLocalizations);
    final title = l10n?.errorScreenTitle ?? "This page couldn't load";
    final body = l10n?.errorScreenBody ??
        'Something went wrong. Please try again in a moment.';

    return Directionality(
      textDirection: TextDirection.ltr,
      child: ColoredBox(
        color: AppColors.pageBg,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const ExcludeSemantics(
                  child: Icon(
                    Icons.cloud_off_outlined,
                    size: 44,
                    color: AppColors.ink3,
                  ),
                ),
                const SizedBox(height: 16),
                Semantics(
                  liveRegion: true,
                  child: Text(
                    title,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: AppColors.ink,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  body,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 13.5,
                    height: 1.6,
                    color: AppColors.ink2,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
