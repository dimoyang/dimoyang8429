import 'dart:io' show Platform;

/// Android 模拟器中 localhost 指向模拟器自身，需用 10.0.2.2 访问宿主。
String resolveApiBaseUrl() {
  if (Platform.isAndroid) {
    return 'http://10.0.2.2:8000/api/v1';
  }
  return 'http://localhost:8000/api/v1';
}
