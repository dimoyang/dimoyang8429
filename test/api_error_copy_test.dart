import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/l10n/app_localizations.dart';

void main() {
  test('4xx 业务错误不展示后端原始 detail', () {
    const exception = ApiBusinessException(
      statusCode: 422,
      detail: 'ensure this value is a valid integer',
    );
    final l10n = lookupAppLocalizations(const Locale('zh'));

    final message = exception.toLocalizedMessage(l10n);

    expect(message, l10n.errorRequest);
    expect(message, isNot(contains('ensure this value')));
  });

  test('网络异常相关文案四种语言均已提供', () {
    for (final code in ['en', 'zh', 'de', 'fr']) {
      final l10n = lookupAppLocalizations(Locale(code));
      expect(l10n.medicalOfflineHint, isNotEmpty);
      expect(l10n.medicalLoadFailed, isNotEmpty);
      expect(l10n.retry, isNotEmpty);
      expect(l10n.errorNetwork, isNotEmpty);
      expect(l10n.errorRequest, isNotEmpty);
      expect(l10n.errorServer, isNotEmpty);
      expect(l10n.errorUnknown, isNotEmpty);
    }
  });
}
