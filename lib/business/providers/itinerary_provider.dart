import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:meditour_app/core/services/storage_service.dart';
import 'package:meditour_app/data/models/travel_itinerary.dart';

/// Manages locally saved itineraries.
class ItineraryProvider extends ChangeNotifier {
  List<TravelItinerary> _itineraries = [];
  bool _isLoaded = false;
  bool _loadFailed = false;

  List<TravelItinerary> get itineraries => List.unmodifiable(_itineraries);

  bool get isLoaded => _isLoaded;

  /// 本地存储读取失败（页面应展示错误态而不是一直加载）。
  bool get loadFailed => _loadFailed;

  TravelItinerary? findById(String id) {
    for (final itinerary in _itineraries) {
      if (itinerary.id == id) {
        return itinerary;
      }
    }
    return null;
  }

  Future<void> load() async {
    if (_loadFailed) {
      _loadFailed = false;
      notifyListeners();
    }

    try {
      final records = await StorageService.getItineraryRecords();
      final loaded = <TravelItinerary>[];

      for (final record in records) {
        try {
          final json = jsonDecode(record);
          if (json is Map<String, dynamic>) {
            loaded.add(TravelItinerary.fromJson(json));
          } else if (json is Map) {
            loaded.add(
              TravelItinerary.fromJson(Map<String, dynamic>.from(json)),
            );
          }
        } on FormatException {
          // Ignore malformed local records so one bad item does not block trips.
        } on TypeError {
          // Ignore records written with an incompatible schema.
        }
      }

      _itineraries = loaded;
      _sortItineraries();
      _isLoaded = true;
      _loadFailed = false;
    } catch (_) {
      _loadFailed = true;
    }

    notifyListeners();
  }

  Future<TravelItinerary> create({
    required String title,
    required DateTime startDate,
    required DateTime endDate,
    required List<String> destinationIds,
    List<ItineraryDay> days = const [],
    required String notes,
  }) async {
    final now = DateTime.now();
    final itinerary = TravelItinerary(
      id: 'trip_${now.microsecondsSinceEpoch}',
      title: title,
      startDate: startDate,
      endDate: endDate,
      destinationIds: List.unmodifiable(destinationIds),
      days: List.unmodifiable(days),
      notes: notes,
      createdAt: now,
      updatedAt: now,
    );

    _itineraries.add(itinerary);
    _sortItineraries();
    notifyListeners();
    await _persist();
    return itinerary;
  }

  Future<void> update(TravelItinerary itinerary) async {
    final index = _itineraries.indexWhere((item) => item.id == itinerary.id);
    if (index == -1) {
      return;
    }

    _itineraries[index] = itinerary.copyWith(updatedAt: DateTime.now());
    _sortItineraries();
    notifyListeners();
    await _persist();
  }

  /// 把目的地加入指定行程；已包含时返回 false。
  Future<bool> addDestination(String itineraryId, String destinationId) async {
    final itinerary = findById(itineraryId);
    if (itinerary == null || itinerary.destinationIds.contains(destinationId)) {
      return false;
    }

    await update(
      itinerary.copyWith(
        destinationIds: [...itinerary.destinationIds, destinationId],
      ),
    );
    return true;
  }

  Future<void> delete(String id) async {
    _itineraries.removeWhere((itinerary) => itinerary.id == id);
    notifyListeners();
    await _persist();
  }

  void _sortItineraries() {
    _itineraries.sort((a, b) => a.startDate.compareTo(b.startDate));
  }

  Future<void> _persist() {
    return StorageService.setItineraryRecords(
      _itineraries.map((item) => jsonEncode(item.toJson())).toList(),
    );
  }
}
