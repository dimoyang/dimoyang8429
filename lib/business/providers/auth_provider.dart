import 'dart:async';
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
    // token 被拦截器清除（业务请求 401）时同步清空内存登录态。
    TokenStore.onSessionCleared = _handleSessionCleared;
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
    final String token;
    try {
      token = await ApiService.instance.login(email: email, password: password);
    } on UnauthorizedException {
      // 登录表单的 401 是凭据错误，不是会话过期。
      throw const InvalidCredentialsException();
    }
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
    try {
      await ApiService.instance.register(
        email: email,
        password: password,
        fullName: fullName,
        preferredLanguage: preferredLanguage,
      );
    } on UnauthorizedException {
      throw const InvalidCredentialsException();
    }
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

  /// token 被外部清除（如业务请求 401）时，同步清空内存登录态。
  void _handleSessionCleared() {
    if (_user == null) {
      return;
    }
    _user = null;
    unawaited(StorageService.clearCachedUser());
    notifyListeners();
  }

  @override
  void dispose() {
    if (TokenStore.onSessionCleared == _handleSessionCleared) {
      TokenStore.onSessionCleared = null;
    }
    super.dispose();
  }
}
