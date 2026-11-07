import 'package:shared_preferences/shared_preferences.dart';

/// 本地存储服务
class StorageService {
  static const _keyLanguage = 'language_code';
  static const _keyFavoriteDestinations = 'favorite_destination_ids';
  static const _keyItineraries = 'travel_itineraries';
  static const _keyAuthToken = 'auth_token';
  static const _keyCachedUser = 'cached_user';

  static Future<String?> getLanguageCode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyLanguage);
  }

  static Future<void> setLanguageCode(String code) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyLanguage, code);
  }

  static Future<List<String>> getFavoriteDestinationIds() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList(_keyFavoriteDestinations) ?? const [];
  }

  static Future<void> setFavoriteDestinationIds(
    Set<String> destinationIds,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final sortedIds = destinationIds.toList()..sort();
    await prefs.setStringList(_keyFavoriteDestinations, sortedIds);
  }

  static Future<List<String>> getItineraryRecords() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList(_keyItineraries) ?? const [];
  }

  static Future<void> setItineraryRecords(List<String> records) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_keyItineraries, records);
  }

  static Future<String?> getAuthToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyAuthToken);
  }

  static Future<void> setAuthToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyAuthToken, token);
  }

  static Future<void> clearAuthToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyAuthToken);
  }

  static Future<String?> getCachedUser() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyCachedUser);
  }

  static Future<void> setCachedUser(String userJson) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyCachedUser, userJson);
  }

  static Future<void> clearCachedUser() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyCachedUser);
  }
}
