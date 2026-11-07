import 'package:flutter/material.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart';

/// 显示「加入行程」底部面板：选择已有行程或快速新建。
Future<void> showAddToItinerarySheet(
  BuildContext context, {
  required Destination destination,
}) {
  final l10n = AppLocalizations.of(context);
  final langCode = Localizations.localeOf(context).languageCode;

  return showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.white,
    showDragHandle: true,
    builder: (sheetContext) {
      return SafeArea(
        child: Consumer<ItineraryProvider>(
          builder: (consumerContext, provider, _) {
            if (provider.loadFailed) {
              return Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      l10n.medicalLoadFailed,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.ink,
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: provider.load,
                      child: Text(l10n.retry),
                    ),
                  ],
                ),
              );
            }

            if (!provider.isLoaded) {
              return const Padding(
                padding: EdgeInsets.symmetric(vertical: 32),
                child: Center(child: CircularProgressIndicator()),
              );
            }

            final itineraries = provider.itineraries;
            return ListView(
              shrinkWrap: true,
              padding: const EdgeInsets.only(bottom: 12),
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                  child: Text(
                    l10n.btnItinerary,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: AppColors.ink,
                    ),
                  ),
                ),
                ...itineraries.map((itinerary) {
                  final alreadyAdded =
                      itinerary.destinationIds.contains(destination.id);
                  return ListTile(
                    leading: const Icon(
                      Icons.route_outlined,
                      color: AppColors.primary,
                    ),
                    title: Text(
                      itinerary.title,
                      style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600,
                        color: alreadyAdded ? AppColors.ink3 : AppColors.ink,
                      ),
                    ),
                    subtitle: Text(
                      l10n.itineraryDays(itinerary.dayCount),
                      style: const TextStyle(
                        fontSize: 12.5,
                        color: AppColors.ink3,
                      ),
                    ),
                    trailing: alreadyAdded
                        ? const Icon(
                            Icons.check_circle,
                            color: AppColors.primary,
                            size: 20,
                          )
                        : null,
                    onTap: alreadyAdded
                        ? null
                        : () async {
                            await provider.addDestination(
                              itinerary.id,
                              destination.id,
                            );
                            if (sheetContext.mounted) {
                              Navigator.of(sheetContext).pop();
                            }
                            if (context.mounted) {
                              _showAddedSnackBar(context, l10n);
                            }
                          },
                  );
                }),
                ListTile(
                  leading: const Icon(
                    Icons.add_circle_outline,
                    color: AppColors.primary,
                  ),
                  title: Text(
                    l10n.addToTripCreateNew,
                    style: const TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w600,
                      color: AppColors.primary,
                    ),
                  ),
                  onTap: () async {
                    await _createTripAndAdd(
                      provider,
                      destination,
                      langCode,
                    );
                    if (sheetContext.mounted) {
                      Navigator.of(sheetContext).pop();
                    }
                    if (context.mounted) {
                      _showAddedSnackBar(context, l10n);
                    }
                  },
                ),
              ],
            );
          },
        ),
      );
    },
  );
}

Future<void> _createTripAndAdd(
  ItineraryProvider provider,
  Destination destination,
  String langCode,
) async {
  final days = _parseSuggestDays(destination.suggestDays);
  final today = DateTime.now();
  final startDate = DateTime(today.year, today.month, today.day + 7);
  final endDate = startDate.add(Duration(days: days - 1));

  await provider.create(
    title: destination.getName(langCode),
    startDate: startDate,
    endDate: endDate,
    destinationIds: [destination.id],
    notes: '',
  );
}

int _parseSuggestDays(String suggestDays) {
  final match = RegExp(r'\d+').firstMatch(suggestDays);
  if (match == null) {
    return 3;
  }
  return int.tryParse(match.group(0)!) ?? 3;
}

void _showAddedSnackBar(BuildContext context, AppLocalizations l10n) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(l10n.addToTripAdded),
      behavior: SnackBarBehavior.floating,
    ),
  );
}
