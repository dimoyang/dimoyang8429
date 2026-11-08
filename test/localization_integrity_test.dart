import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 四语 ARB 完整性检查：
/// - 任一语言缺少模板键、或出现模板没有的多余键，测试失败；
/// - 带占位符的文案在各语言中的占位符集合必须一致，否则测试失败。
const _locales = ['en', 'zh', 'de', 'fr'];

void main() {
  test('四语 ARB 键集合与模板一致', () {
    final arbs = _loadAll();
    final templateKeys = _messageKeys(arbs['en']!);
    expect(templateKeys, isNotEmpty);

    for (final code in _locales.skip(1)) {
      final keys = _messageKeys(arbs[code]!);
      expect(
        templateKeys.difference(keys),
        isEmpty,
        reason: '$code 缺少这些键：${templateKeys.difference(keys)}',
      );
      expect(
        keys.difference(templateKeys),
        isEmpty,
        reason: '$code 存在模板未定义的键：${keys.difference(templateKeys)}',
      );
    }
  });

  test('四语文案非空', () {
    final arbs = _loadAll();
    for (final code in _locales) {
      for (final key in _messageKeys(arbs[code]!)) {
        final value = arbs[code]![key];
        expect(
          value,
          isA<String>().having((v) => v.trim(), 'trimmed', isNotEmpty),
          reason: '$code 的 $key 为空',
        );
      }
    }
  });

  test('四语占位符与模板一致', () {
    final arbs = _loadAll();
    for (final code in _locales.skip(1)) {
      for (final key in _messageKeys(arbs['en']!)) {
        final expected = _placeholders(arbs['en']![key]);
        if (expected.isEmpty) {
          continue;
        }
        expect(
          _placeholders(arbs[code]![key]),
          expected,
          reason: '$code 的 $key 占位符不匹配',
        );
      }
    }
  });
}

Map<String, Map<String, dynamic>> _loadAll() {
  return {
    for (final code in _locales) code: _readArb(code),
  };
}

Map<String, dynamic> _readArb(String code) {
  final file = File('assets/translations/app_$code.arb');
  if (!file.existsSync()) {
    fail('缺少 ${file.path}');
  }
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

Set<String> _messageKeys(Map<String, dynamic> arb) {
  return arb.keys.where((key) => !key.startsWith('@')).toSet();
}

Set<String> _placeholders(Object? value) {
  final matches = RegExp(r'\{(\w+)\}').allMatches(value as String? ?? '');
  return {for (final match in matches) match.group(1)!};
}
