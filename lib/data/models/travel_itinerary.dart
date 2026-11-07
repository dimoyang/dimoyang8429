/// A single day within a saved itinerary.
class ItineraryDay {
  final int dayNumber;
  final List<String> destinationIds;
  final String notes;

  const ItineraryDay({
    required this.dayNumber,
    this.destinationIds = const [],
    this.notes = '',
  });

  ItineraryDay copyWith({
    int? dayNumber,
    List<String>? destinationIds,
    String? notes,
  }) {
    return ItineraryDay(
      dayNumber: dayNumber ?? this.dayNumber,
      destinationIds: destinationIds ?? this.destinationIds,
      notes: notes ?? this.notes,
    );
  }

  Map<String, Object> toJson() {
    return {
      'dayNumber': dayNumber,
      'destinationIds': destinationIds,
      'notes': notes,
    };
  }

  factory ItineraryDay.fromJson(Map<String, dynamic> json) {
    final rawIds = json['destinationIds'];
    return ItineraryDay(
      dayNumber: json['dayNumber'] as int? ?? 1,
      destinationIds:
          rawIds is List ? List<String>.from(rawIds) : const <String>[],
      notes: json['notes'] as String? ?? '',
    );
  }
}

/// A locally saved, editable China travel plan.
class TravelItinerary {
  final String id;
  final String title;
  final DateTime startDate;
  final DateTime endDate;
  final List<String> destinationIds;
  final List<ItineraryDay> days;
  final String notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  const TravelItinerary({
    required this.id,
    required this.title,
    required this.startDate,
    required this.endDate,
    required this.destinationIds,
    this.days = const [],
    required this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  int get dayCount => endDate.difference(startDate).inDays + 1;

  TravelItinerary copyWith({
    String? title,
    DateTime? startDate,
    DateTime? endDate,
    List<String>? destinationIds,
    List<ItineraryDay>? days,
    String? notes,
    DateTime? updatedAt,
  }) {
    return TravelItinerary(
      id: id,
      title: title ?? this.title,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      destinationIds: destinationIds ?? this.destinationIds,
      days: days ?? this.days,
      notes: notes ?? this.notes,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  Map<String, Object> toJson() {
    return {
      'id': id,
      'title': title,
      'startDate': startDate.toIso8601String(),
      'endDate': endDate.toIso8601String(),
      'destinationIds': destinationIds,
      'days': days.map((day) => day.toJson()).toList(),
      'notes': notes,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }

  factory TravelItinerary.fromJson(Map<String, dynamic> json) {
    final rawDays = json['days'];
    final days = <ItineraryDay>[];
    if (rawDays is List) {
      for (final rawDay in rawDays) {
        if (rawDay is Map) {
          days.add(ItineraryDay.fromJson(Map<String, dynamic>.from(rawDay)));
        }
      }
    }

    return TravelItinerary(
      id: json['id'] as String,
      title: json['title'] as String,
      startDate: DateTime.parse(json['startDate'] as String),
      endDate: DateTime.parse(json['endDate'] as String),
      destinationIds: List<String>.from(
        json['destinationIds'] as List<dynamic>,
      ),
      days: days,
      notes: json['notes'] as String? ?? '',
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
    );
  }
}
