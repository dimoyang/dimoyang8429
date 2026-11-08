import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/services/recent_search_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  test('最近搜索去重、置顶并限制条数', () async {
    SharedPreferences.setMockInitialValues({});

    for (var i = 0; i < 10; i++) {
      await RecentSearchStore.add('关键词$i');
    }
    var list = await RecentSearchStore.load();
    expect(list.length, RecentSearchStore.maxEntries);
    expect(list.first, '关键词9');

    list = await RecentSearchStore.add('关键词4');
    expect(list.first, '关键词4');
    expect(list.where((item) => item == '关键词4').length, 1);

    list = await RecentSearchStore.remove('关键词4');
    expect(list.contains('关键词4'), isFalse);

    await RecentSearchStore.clear();
    expect(await RecentSearchStore.load(), isEmpty);
  });

  test('空白关键词不写入历史', () async {
    SharedPreferences.setMockInitialValues({});
    expect(await RecentSearchStore.add('   '), isEmpty);
    expect(await RecentSearchStore.load(), isEmpty);
  });
}
