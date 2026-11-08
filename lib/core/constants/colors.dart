import 'package:flutter/material.dart';

/// 应用配色常量（与设计稿保持一致）
class AppColors {
  AppColors._();

  /// 主色：青绿
  static const Color primary = Color(0xFF0D9488);

  /// 主色加深
  static const Color primaryDark = Color(0xFF0F766E);

  /// 主色浅
  static const Color primaryLight = Color(0xFFCCFBF1);

  /// 主色极浅背景
  static const Color primaryBg = Color(0xFFF0FDFA);

  /// 正文墨色
  static const Color ink = Color(0xFF1E293B);

  /// 次要文字（在 pageBg 上对比度 ≥ 4.5:1）
  static const Color ink2 = Color(0xFF5F7086);

  /// 弱化文字（白底对比度 ≥ 4.5:1，用于小字号辅助信息）
  static const Color ink3 = Color(0xFF5F6D80);

  /// 页面背景
  static const Color pageBg = Color(0xFFF6F8FA);

  /// 卡片描边
  static const Color line = Color(0xFFE8EDF2);

  /// 贴士卡背景
  static const Color tipBg = Color(0xFFFFF7E0);

  /// 危险色（表单错误；白底对比度 ≥ 4.5:1）
  static const Color danger = Color(0xFFDC2626);
}
