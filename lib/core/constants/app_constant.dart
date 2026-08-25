import 'package:flutter/material.dart';

/// 应用级常量
class AppConstants {
  AppConstants._();

  /// 应用名称
  static const String appName = 'Meditour';

  /// 支持的语言代码（与 assets/translations 下的 arb 文件对应）
  static const List<String> supportedLanguageCodes = ['en', 'de', 'fr', 'zh'];

  /// 支持的 Locale 列表
  static List<Locale> get supportedLocales =>
      supportedLanguageCodes.map((code) => Locale(code)).toList();

  /// 默认语言
  static const String defaultLanguageCode = 'en';
}
