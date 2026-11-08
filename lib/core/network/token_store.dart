import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:meditour_app/core/services/storage_service.dart';

/// 内存 + 持久化的令牌仓库，供 dio 拦截器同步读取。
class TokenStore {
  TokenStore._();

  static String? _token;
  static String? _refreshToken;
  static bool _restored = false;

  /// 会话被清除时的同步回调，由 [AuthProvider] 注册，用于同步内存登录态。
  static void Function()? onSessionCleared;

  /// 当前访问令牌（未恢复持久化值前可能为 null）。
  static String? get current => _token;

  /// 刷新令牌；一次一换，使用后由后端轮换。
  static String? get refreshToken => _refreshToken;

  /// 启动时从本地恢复令牌。
  static Future<void> restore() async {
    if (_restored) {
      return;
    }
    _token = await StorageService.getAuthToken();
    _refreshToken = await StorageService.getRefreshToken();
    _restored = true;
  }

  /// 保存访问令牌；传入 [refreshToken] 时一并保存（刷新后轮换）。
  static Future<void> save(String token, {String? refreshToken}) async {
    _token = token;
    if (refreshToken != null) {
      _refreshToken = refreshToken;
    }
    _restored = true;
    await StorageService.setAuthToken(token);
    if (refreshToken != null) {
      await StorageService.setRefreshToken(refreshToken);
    }
  }

  static Future<void> clear() async {
    final hadToken = _token != null || _refreshToken != null;
    _token = null;
    _refreshToken = null;
    _restored = true;
    await StorageService.clearAuthToken();
    await StorageService.clearRefreshToken();
    if (hadToken) {
      onSessionCleared?.call();
    }
  }

  /// 仅测试用：清空内存态，模拟冷启动。
  @visibleForTesting
  static void resetForTesting() {
    _token = null;
    _refreshToken = null;
    _restored = false;
    onSessionCleared = null;
  }
}
