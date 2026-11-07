import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/data/models/travel_itinerary.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('itineraries persist across create, update, and delete', () async {
    final firstProvider = ItineraryProvider();
    await firstProvider.load();

    final created = await firstProvider.create(
      title: 'China highlights',
      startDate: DateTime(2027, 4, 10),
      endDate: DateTime(2027, 4, 16),
      destinationIds: const ['beijing', 'shanghai'],
      notes: 'Book the train.',
    );

    final restoredProvider = ItineraryProvider();
    await restoredProvider.load();
    expect(restoredProvider.itineraries, hasLength(1));
    expect(restoredProvider.itineraries.single.title, 'China highlights');
    expect(restoredProvider.itineraries.single.dayCount, 7);
    expect(
      restoredProvider.itineraries.single.destinationIds,
      ['beijing', 'shanghai'],
    );

    await restoredProvider.update(
      created.copyWith(title: 'China spring trip'),
    );

    final updatedProvider = ItineraryProvider();
    await updatedProvider.load();
    expect(updatedProvider.itineraries.single.title, 'China spring trip');

    await updatedProvider.delete(created.id);

    final emptyProvider = ItineraryProvider();
    await emptyProvider.load();
    expect(emptyProvider.itineraries, isEmpty);
  });

  test('day plans round-trip through local storage', () async {
    final provider = ItineraryProvider();
    await provider.load();

    await provider.create(
      title: 'Day plan trip',
      startDate: DateTime(2027, 5, 1),
      endDate: DateTime(2027, 5, 3),
      destinationIds: const ['beijing', 'shanghai'],
      days: const [
        ItineraryDay(
          dayNumber: 1,
          destinationIds: ['beijing'],
          notes: 'Arrive and settle in.',
        ),
        ItineraryDay(
          dayNumber: 2,
          destinationIds: ['shanghai', 'beijing'],
          notes: 'High-speed train.',
        ),
        ItineraryDay(dayNumber: 3),
      ],
      notes: 'Overall plan.',
    );

    final restored = ItineraryProvider();
    await restored.load();
    final trip = restored.itineraries.single;

    expect(trip.dayCount, 3);
    expect(trip.days, hasLength(3));
    expect(trip.days[0].destinationIds, ['beijing']);
    expect(trip.days[0].notes, 'Arrive and settle in.');
    expect(trip.days[1].destinationIds, ['shanghai', 'beijing']);
    expect(trip.days[1].notes, 'High-speed train.');
    expect(trip.days[2].destinationIds, isEmpty);
    expect(trip.days[2].notes, '');
  });

  test('legacy records without day plans still load', () async {
    final legacyRecord = jsonEncode({
      'id': 'trip_legacy',
      'title': 'Legacy trip',
      'startDate': '2027-04-10T00:00:00.000',
      'endDate': '2027-04-12T00:00:00.000',
      'destinationIds': ['beijing'],
      'notes': 'Saved before day plans existed.',
      'createdAt': '2027-01-01T00:00:00.000',
      'updatedAt': '2027-01-01T00:00:00.000',
    });
    SharedPreferences.setMockInitialValues({
      'travel_itineraries': [legacyRecord],
    });

    final provider = ItineraryProvider();
    await provider.load();

    final trip = provider.itineraries.single;
    expect(trip.dayCount, 3);
    expect(trip.days, isEmpty);
    expect(trip.destinationIds, ['beijing']);
  });

  test('malformed local itinerary records are ignored', () async {
    SharedPreferences.setMockInitialValues({
      'travel_itineraries': ['not-json', '{"oldSchema":true}'],
    });

    final provider = ItineraryProvider();
    await provider.load();

    expect(provider.isLoaded, isTrue);
    expect(provider.itineraries, isEmpty);
  });
}
