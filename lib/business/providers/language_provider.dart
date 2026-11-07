import 'package:flutter/material.dart';
import 'package:meditour_app/core/services/storage_service.dart';

class LanguageProvider extends ChangeNotifier {
  Locale _currentLocale;

  Locale get currentLocale => _currentLocale;

  LanguageProvider({String? initialCode})
      : _currentLocale = Locale(initialCode ?? 'en');

  /// 语言列表（代码 → 原生名称）
  static const languageOptions = [
    ('en', 'English', '🇬🇧'),
    ('de', 'Deutsch', '🇩🇪'),
    ('fr', 'Français', '🇫🇷'),
    ('zh', '中文', '🇨🇳'),
  ];

  void setLanguage(String languageCode) {
    _currentLocale = Locale(languageCode);
    StorageService.setLanguageCode(languageCode);
    notifyListeners();
  }
}
