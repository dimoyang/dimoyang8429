import 'package:shared_preferences/shared_preferences.dart';

/// 本地存储服务
class StorageService {
  static const _keyLanguage = 'language_code';

  static Future<String?> getLanguageCode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyLanguage);
  }

  static Future<void> setLanguageCode(String code) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyLanguage, code);
  }
}
