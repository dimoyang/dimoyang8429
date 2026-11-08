import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:meditour_app/core/services/storage_service.dart';

/// 内存 + 持久化的 token 仓库，供 dio 拦截器同步读取。
class TokenStore {
  TokenStore._();

  static String? _token;
  static bool _restored = false;

  /// 会话被清除时的同步回调，由 [AuthProvider] 注册，用于同步内存登录态。
  static void Function()? onSessionCleared;

  /// 当前 token（未恢复持久化值前可能为 null）。
  static String? get current => _token;

  /// 启动时从本地恢复 token。
  static Future<void> restore() async {
    if (_restored) {
      return;
    }
    _token = await StorageService.getAuthToken();
    _restored = true;
  }

  static Future<void> save(String token) async {
    _token = token;
    _restored = true;
    await StorageService.setAuthToken(token);
  }

  static Future<void> clear() async {
    final hadToken = _token != null;
    _token = null;
    _restored = true;
    await StorageService.clearAuthToken();
    if (hadToken) {
      onSessionCleared?.call();
    }
  }

  /// 仅测试用：清空内存态，模拟冷启动。
  @visibleForTesting
  static void resetForTesting() {
    _token = null;
    _restored = false;
    onSessionCleared = null;
  }
}
