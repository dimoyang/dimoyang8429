/// A locally saved, editable China travel plan.
class TravelItinerary {
  final String id;
  final String title;
  final DateTime startDate;
  final DateTime endDate;
  final List<String> destinationIds;
  final String notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  const TravelItinerary({
    required this.id,
    required this.title,
    required this.startDate,
    required this.endDate,
    required this.destinationIds,
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
    String? notes,
    DateTime? updatedAt,
  }) {
    return TravelItinerary(
      id: id,
      title: title ?? this.title,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      destinationIds: destinationIds ?? this.destinationIds,
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
      'notes': notes,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }

  factory TravelItinerary.fromJson(Map<String, dynamic> json) {
    return TravelItinerary(
      id: json['id'] as String,
      title: json['title'] as String,
      startDate: DateTime.parse(json['startDate'] as String),
      endDate: DateTime.parse(json['endDate'] as String),
      destinationIds: List<String>.from(
        json['destinationIds'] as List<dynamic>,
      ),
      notes: json['notes'] as String? ?? '',
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
    );
  }
}
