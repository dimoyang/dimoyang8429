import 'package:flutter/foundation.dart';
import 'package:meditour_app/core/services/storage_service.dart';

/// 管理用户收藏的目的地，并将结果保存到本地。
class FavoritesProvider extends ChangeNotifier {
  Set<String> _destinationIds = {};
  bool _isLoaded = false;

  bool get isLoaded => _isLoaded;

  Set<String> get destinationIds => Set.unmodifiable(_destinationIds);

  bool isFavorite(String destinationId) {
    return _destinationIds.contains(destinationId);
  }

  Future<void> load() async {
    _destinationIds =
        (await StorageService.getFavoriteDestinationIds()).toSet();
    _isLoaded = true;
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
