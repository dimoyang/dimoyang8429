import 'package:flutter_test/flutter_test.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
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
