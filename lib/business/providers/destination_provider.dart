import 'package:flutter/foundation.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';

/// 目的地数据状态：提供加载/空/错误三态，供页面订阅。
class DestinationProvider extends ChangeNotifier {
  List<Destination> _destinations = DestinationRepository.destinations;
  bool _isLoading = false;
  Object? _lastError;
  bool _initialized = false;
  bool _initialLoadCompleted = false;

  List<Destination> get destinations => _destinations;

  bool get isLoading => _isLoading;

  /// 首次远端加载尚未结束：首页据此展示骨架，而不是直接闪出内置样例。
  bool get isInitialLoading => _isLoading && !_initialLoadCompleted;

  bool get hasError => _lastError != null;

  /// 远程拉取失败且当前无任何数据时，才视为空态/错误态。
  bool get isEmpty =>
      !_isLoading && _lastError == null && _destinations.isEmpty;

  /// 是否回退到了持久缓存或内置示例（用于离线提示）。
  bool get isOfflineFallback => DestinationRepository.lastLoadWasSample;

  String get heroImageUrl => DestinationRepository.heroImageUrl;

  Destination? findById(String id) {
    for (final destination in _destinations) {
      if (destination.id == id) {
        return destination;
      }
    }
    return null;
  }

  /// 启动时调用：先恢复持久缓存，再后台刷新远端。
  Future<void> init({String? lang}) async {
    if (_initialized) {
      return;
    }
    _initialized = true;

    await DestinationRepository.restoreCache();
    _destinations = DestinationRepository.destinations;
    notifyListeners();

    await refresh(lang: lang);
  }

  Future<void> refresh({String? lang}) async {
    _isLoading = true;
    _lastError = null;
    notifyListeners();

    try {
      _destinations = await DestinationRepository.refresh(lang: lang);
    } catch (error) {
      _lastError = error;
    } finally {
      _isLoading = false;
      _initialLoadCompleted = true;
      notifyListeners();
    }
  }
}
