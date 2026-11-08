import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';

/// 目的地数据状态：提供加载/空/错误三态，供页面订阅。
class DestinationProvider extends ChangeNotifier {
  List<Destination> _destinations = DestinationRepository.sampleDestinations;
  bool _isLoading = false;
  Object? _lastError;
  bool _initialized = false;
  bool _initialLoadCompleted = false;
  bool _skeletonGraceElapsed = false;
  Timer? _skeletonTimer;
  String _languageCode = 'en';

  List<Destination> get destinations => _destinations;

  bool get isLoading => _isLoading;

  /// 首次远端加载尚未结束：首页据此展示骨架，而不是直接闪出内置样例。
  ///
  /// 骨架最多展示 [_skeletonGrace]，之后即使请求仍在重试也先展示本地数据，
  /// 避免后端很慢时出现“骨架一直转”的假死观感。
  bool get isInitialLoading =>
      _isLoading && !_initialLoadCompleted && !_skeletonGraceElapsed;

  bool get hasError => _lastError != null;

  /// 远程拉取失败且当前无任何数据时，才视为空态/错误态。
  bool get isEmpty =>
      !_isLoading && _lastError == null && _destinations.isEmpty;

  /// 是否没能从远端拿到最新数据、正在展示本地缓存/内置样例（用于离线提示）。
  bool get isOfflineFallback =>
      DestinationRepository.lastLoadWasSample || _lastError != null;

  String get heroImageUrl => DestinationRepository.heroImageUrl;

  Destination? findById(String id) {
    for (final destination in _destinations) {
      if (destination.id == id) {
        return destination;
      }
    }
    return null;
  }

  /// 启动时调用：先恢复持久缓存，再按当前语言后台刷新远端。
  Future<void> init({String? lang}) async {
    if (_initialized) {
      if (lang != null) {
        await syncLanguage(lang);
      }
      return;
    }
    _initialized = true;
    if (lang != null) {
      _languageCode = _baseLanguage(lang);
    }

    _destinations = await DestinationRepository.restoreCache();
    notifyListeners();

    await refresh(lang: _languageCode);
  }

  /// 语言切换时同步数据：未初始化则按新语言初始化，已初始化则重新拉取。
  ///
  /// 采用重新拉取而不是用单语言缓存切换：缓存只保留最近一次语言的文本，
  /// 无法同时覆盖 de/fr，重新请求才能拿到后端最新译文。
  Future<void> syncLanguage(String languageCode) async {
    final normalized = _baseLanguage(languageCode);
    if (!_initialized) {
      await init(lang: normalized);
      return;
    }
    if (normalized == _languageCode) {
      return;
    }
    _languageCode = normalized;
    // 该入口由 Provider 的 update 回调触发时正处于构建阶段，
    // 先让出一次事件循环，避免构建期间 notifyListeners。
    await Future<void>.value();
    await refresh(lang: normalized);
  }

  Future<void> refresh({String? lang}) async {
    final requestLang = _requestLanguage(lang ?? _languageCode);
    _isLoading = true;
    _lastError = null;
    notifyListeners();
    if (!_initialLoadCompleted) {
      _skeletonGraceElapsed = false;
      _skeletonTimer?.cancel();
      _skeletonTimer = Timer(_skeletonGrace, () {
        _skeletonGraceElapsed = true;
        notifyListeners();
      });
    }

    try {
      _destinations = await DestinationRepository.refresh(lang: requestLang);
    } catch (error) {
      _lastError = error;
    } finally {
      _skeletonTimer?.cancel();
      _skeletonTimer = null;
      _skeletonGraceElapsed = true;
      _isLoading = false;
      _initialLoadCompleted = true;
      notifyListeners();
    }
  }

  /// 传给后端的语言：中英文沿用不传 lang 的旧路径，其余语言按请求语言拉取。
  ///
  /// 中文主数据与英文名已由后端默认响应提供，传 `zh`/`en` 反而会把 `name`
  /// 覆盖成单一语言并丢失中文副标题。de/fr 需要后端译文；若后端将来不支持
  /// 某个语言并返回 422，[refresh] 会记录错误并保留现有数据，UI 回退英文名。
  static String? _requestLanguage(String languageCode) {
    final lang = _baseLanguage(languageCode);
    return lang == 'en' || lang == 'zh' ? null : lang;
  }

  static String _baseLanguage(String languageCode) {
    final separator = languageCode.indexOf(RegExp('[-_]'));
    final base =
        separator == -1 ? languageCode : languageCode.substring(0, separator);
    return base.toLowerCase();
  }

  /// 骨架展示上限；超过后先展示本地数据，请求结果到达再安静更新。
  static const Duration _skeletonGrace = Duration(seconds: 2);

  @override
  void dispose() {
    _skeletonTimer?.cancel();
    super.dispose();
  }
}
