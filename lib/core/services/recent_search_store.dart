import 'package:shared_preferences/shared_preferences.dart';

/// 目的地搜索的本地历史记录。
///
/// 只保存用户主动提交过的关键词（按最新的在前去重，最多 8 条），
/// 输入过程中的半成品关键词不会写入。
class RecentSearchStore {
  RecentSearchStore._();

  static const _key = 'recent_destination_searches';

  /// 最多保留的条数，避免历史列表无限增长。
  static const int maxEntries = 8;

  static Future<List<String>> load() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList(_key) ?? const [];
  }

  /// 写入一条记录并返回最新列表。
  static Future<List<String>> add(String query) async {
    final normalized = _normalize(query);
    if (normalized.isEmpty) {
      return load();
    }
    final prefs = await SharedPreferences.getInstance();
    final current = prefs.getStringList(_key) ?? const <String>[];
    final lower = normalized.toLowerCase();
    final updated = [
      normalized,
      ...current.where((item) => item.toLowerCase() != lower),
    ].take(maxEntries).toList();
    await prefs.setStringList(_key, updated);
    return updated;
  }

  /// 删除单条记录并返回最新列表。
  static Future<List<String>> remove(String query) async {
    final prefs = await SharedPreferences.getInstance();
    final current = prefs.getStringList(_key) ?? const <String>[];
    final updated = current.where((item) => item != query).toList();
    await prefs.setStringList(_key, updated);
    return updated;
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  /// 去掉首尾空白并把连续空白折叠成一个空格。
  static String _normalize(String query) {
    return query.trim().replaceAll(RegExp(r'\s+'), ' ');
  }
}
