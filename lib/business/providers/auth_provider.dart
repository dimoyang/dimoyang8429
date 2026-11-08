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

  /// 会话代际：登录/登出/会话清除时自增，用于丢弃过期的启动恢复结果。
  /// （刷新令牌会让 token 变化，因此不能用 token 值判断。）
  int _sessionEpoch = 0;

  UserProfile? get user => _user;

  bool get isLoggedIn => _user != null;

  bool get isInitialized => _isInitialized;

  /// 启动恢复：先标记初始化完成，避免阻塞首屏；会话恢复在后台完成后再通知。
  /// 本地有 token 则请求 /auth/me 恢复用户，失败静默清除（401 语义不变）。
  Future<void> init() async {
    _isInitialized = true;
    // token 被拦截器清除（业务请求 401 / 刷新失败）时同步清空内存登录态。
    TokenStore.onSessionCleared = _handleSessionCleared;
    notifyListeners();

    await TokenStore.restore();
    final token = TokenStore.current;
    if (token == null) {
      return;
    }
    final epoch = _sessionEpoch;
    try {
      final data = await ApiService.instance.getMe();
      // 恢复期间用户可能已登录或登出，避免旧请求覆盖新会话。
      if (epoch != _sessionEpoch) {
        return;
      }
      _user = UserProfile.fromJson(data);
      await StorageService.setCachedUser(jsonEncode(_user!.toJson()));
    } on ApiException {
      if (epoch != _sessionEpoch) {
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
    final AuthTokens tokens;
    try {
      tokens =
          await ApiService.instance.login(email: email, password: password);
    } on UnauthorizedException {
      // 登录表单的 401 是凭据错误，不是会话过期。
      throw const InvalidCredentialsException();
    }
    _sessionEpoch++;
    await TokenStore.save(
      tokens.accessToken,
      refreshToken: tokens.refreshToken.isEmpty ? null : tokens.refreshToken,
    );
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

  /// 注销账号；成功后会话与本地缓存一并清除。
  Future<void> deleteAccount(String password) async {
    await ApiService.instance.deleteAccount(password);
    await _clearSession();
    notifyListeners();
  }

  /// 请求密码重置邮件。
  ///
  /// 后端无论邮箱是否注册都返回同一成功响应，因此这里不区分结果，
  /// UI 也只应提示"如果已注册会收到邮件"。
  Future<void> requestPasswordReset(String email) {
    return ApiService.instance.requestPasswordReset(email);
  }

  /// 用一次性令牌重置密码；成功后旧会话令牌已全部失效，本地一并清除。
  Future<void> confirmPasswordReset({
    required String token,
    required String newPassword,
  }) async {
    await ApiService.instance.confirmPasswordReset(
      token: token,
      newPassword: newPassword,
    );
    await _clearSession();
    notifyListeners();
  }

  /// 修改密码；后端会让所有旧令牌失效，因此成功后主动清会话回到登录页。
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    await ApiService.instance.changePassword(
      currentPassword: currentPassword,
      newPassword: newPassword,
    );
    await _clearSession();
    notifyListeners();
  }

  /// 导出本人数据（账号、订单、行程）的 JSON。
  Future<Map<String, dynamic>> exportData() {
    return ApiService.instance.exportMyData();
  }

  Future<void> logout() async {
    await _clearSession();
    notifyListeners();
  }

  Future<void> _clearSession() async {
    _sessionEpoch++;
    _user = null;
    await TokenStore.clear();
    await StorageService.clearCachedUser();
  }

  /// token 被外部清除（如业务请求 401、刷新失败）时，同步清空内存登录态。
  void _handleSessionCleared() {
    _sessionEpoch++;
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
