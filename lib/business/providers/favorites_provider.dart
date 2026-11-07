import 'package:flutter/foundation.dart';
import 'package:meditour_app/core/services/storage_service.dart';

/// 管理用户收藏的目的地，并将结果保存到本地。
class FavoritesProvider extends ChangeNotifier {
  Set<String> _destinationIds = {};
  bool _isLoaded = false;
  bool _loadFailed = false;

  bool get isLoaded => _isLoaded;

  /// 本地存储读取失败（页面应展示错误态而不是一直加载）。
  bool get loadFailed => _loadFailed;

  Set<String> get destinationIds => Set.unmodifiable(_destinationIds);

  bool isFavorite(String destinationId) {
    return _destinationIds.contains(destinationId);
  }

  Future<void> load() async {
    if (_loadFailed) {
      _loadFailed = false;
      notifyListeners();
    }

    try {
      _destinationIds =
          (await StorageService.getFavoriteDestinationIds()).toSet();
      _isLoaded = true;
      _loadFailed = false;
    } catch (_) {
      _loadFailed = true;
    }

    notifyListeners();
  }

  Future<void> toggleDestination(String destinationId) async {
    if (_destinationIds.contains(destinationId)) {
      _destinationIds.remove(destinationId);
    } else {
      _destinationIds.add(destinationId);
    }
    notifyListeners();
    await StorageService.setFavoriteDestinationIds(_destinationIds);
  }
}
