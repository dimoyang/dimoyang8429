import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/base_url.dart';

/// 应用级常量
class AppConstants {
  AppConstants._();

  /// 应用名称
  static const String appName = 'Meditour';

  /// 后端 API 基址（可用 --dart-define=API_BASE_URL 覆盖；默认按平台感知，Android 模拟器走 10.0.2.2）
  static String get apiBaseUrl => resolveApiBaseUrl();

  /// 支持的语言代码（与 assets/translations 下的 arb 文件对应）
  static const List<String> supportedLanguageCodes = ['en', 'de', 'fr', 'zh'];

  /// 支持的 Locale 列表
  static List<Locale> get supportedLocales =>
      supportedLanguageCodes.map((code) => Locale(code)).toList();

  /// 默认语言
  static const String defaultLanguageCode = 'en';
}
