import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 应用主题配置（Material 3）
class AppTheme {
  AppTheme._();

  /// 与品牌主色 #0D9488 保持一致，避免 AppBar 与其他控件出现色相漂移。
  static const Color seedColor = AppColors.primary;

  /// 默认支持的语言列表
  static const List<String> supportedLanguageCodes = ['en', 'de', 'fr', 'zh'];

  static ThemeData light() {
    // 用品牌色作为种子生成同色系配色；控件主色固定为加深青绿，
    // 保证 AppBar/按钮上的白色文字对比度达到 4.5:1（品牌亮色仅作装饰）。
    final colorScheme = ColorScheme.fromSeed(seedColor: seedColor).copyWith(
      primary: AppColors.primaryDark,
      onPrimary: Colors.white,
    );
    return _base(colorScheme);
  }

  static ThemeData _base(ColorScheme colorScheme) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      appBarTheme: AppBarTheme(
        backgroundColor: colorScheme.primary,
        foregroundColor: colorScheme.onPrimary,
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}
