import 'base_url_stub.dart'
    if (dart.library.js_interop) 'base_url_web.dart'
    if (dart.library.io) 'base_url_io.dart' as platform;

/// 通过 `--dart-define=API_BASE_URL=...` 显式注入的后端地址，优先级最高。
const String _apiBaseUrlOverride = String.fromEnvironment('API_BASE_URL');

/// 显式注入的地址优先，否则回退到各平台的默认地址。
String resolveApiBaseUrl() => _apiBaseUrlOverride.isNotEmpty
    ? _apiBaseUrlOverride
    : platform.resolveApiBaseUrl();
