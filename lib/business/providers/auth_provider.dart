import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/core/network/token_store.dart';
import 'package:meditour_app/core/services/storage_service.dart';
import 'package:meditour_app/data/models/user_profile.dart';

/// 登录态管理：登录/注册/登出，启动时恢复会话。
class AuthProvider extends ChangeNotifier {
  UserProfile? _user;
  bool _isInitialized = false;

  UserProfile? get user => _user;

  bool get isLoggedIn => _user != null;

  bool get isInitialized => _isInitialized;

  /// 启动恢复：先标记初始化完成，避免阻塞首屏；会话恢复在后台完成后再通知。
  /// 本地有 token 则请求 /auth/me 恢复用户，失败静默清除（401 语义不变）。
  Future<void> init() async {
    _isInitialized = true;
    notifyListeners();

    await TokenStore.restore();
    final token = TokenStore.current;
    if (token == null) {
      return;
    }
    try {
      final data = await ApiService.instance.getMe();
      // 恢复期间用户可能已登录或登出，避免旧请求覆盖新会话。
      if (TokenStore.current != token) {
        return;
      }
      _user = UserProfile.fromJson(data);
      await StorageService.setCachedUser(jsonEncode(_user!.toJson()));
    } on ApiException {
      // 仅当 token 未被登录/登出替换时，才按失效处理。
      if (TokenStore.current != token) {
        return;
      }
      await _clearSession();
    }
    notifyListeners();
  }

  /// 登录；失败抛 [ApiException]，由 UI 捕获展示。
  Future<void> login({
    required String email,
    required String password,
  }) async {
    final token =
        await ApiService.instance.login(email: email, password: password);
    await TokenStore.save(token);
    final data = await ApiService.instance.getMe();
    _user = UserProfile.fromJson(data);
    await StorageService.setCachedUser(jsonEncode(_user!.toJson()));
    notifyListeners();
  }

  /// 注册，成功后自动登录。
  Future<void> register({
    required String email,
    required String password,
    String? fullName,
    String preferredLanguage = 'en',
  }) async {
    await ApiService.instance.register(
      email: email,
      password: password,
      fullName: fullName,
      preferredLanguage: preferredLanguage,
    );
    await login(email: email, password: password);
  }

  Future<void> logout() async {
    await _clearSession();
    notifyListeners();
  }

  Future<void> _clearSession() async {
    _user = null;
    await TokenStore.clear();
    await StorageService.clearCachedUser();
  }
}
