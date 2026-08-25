import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/data/models/travel_itinerary.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart';

/// Lists locally saved itineraries and provides their management actions.
class ItineraryScreen extends StatelessWidget {
  const ItineraryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final provider = context.watch<ItineraryProvider>();

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.itineraryTitle),
        centerTitle: false,
        actions: [
          if (provider.itineraries.isNotEmpty)
            IconButton(
              tooltip: l10n.itineraryNewButton,
              onPressed: () => context.pushNamed('itineraryCreate'),
              icon: const Icon(Icons.add),
            ),
        ],
      ),
      body: SafeArea(
        top: false,
        child: !provider.isLoaded
            ? const Center(child: CircularProgressIndicator())
            : provider.itineraries.isEmpty
                ? const _EmptyItinerary()
                : _ItineraryList(itineraries: provider.itineraries),
      ),
      floatingActionButton: provider.isLoaded && provider.itineraries.isNotEmpty
          ? FloatingActionButton.extended(
              onPressed: () => context.pushNamed('itineraryCreate'),
              icon: const Icon(Icons.add),
              label: Text(l10n.itineraryNewButton),
            )
          : null,
    );
  }
}

class _EmptyItinerary extends StatelessWidget {
  const _EmptyItinerary();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 76,
                height: 76,
                decoration: const BoxDecoration(
                  color: AppColors.primaryBg,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.route_outlined,
                  size: 34,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                l10n.itineraryEmptyTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.ink,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n.itineraryEmptyBody,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.ink2,
                  fontSize: 13.5,
                  height: 1.6,
                ),
              ),
              const SizedBox(height: 22),
              FilledButton.icon(
                key: const Key('createItineraryButton'),
                onPressed: () => context.pushNamed('itineraryCreate'),
                icon: const Icon(Icons.add),
                label: Text(l10n.itineraryNewButton),
                style: FilledButton.styleFrom(
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ItineraryList extends StatelessWidget {
  final List<TravelItinerary> itineraries;

  const _ItineraryList({required this.itineraries});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 96),
      itemCount: itineraries.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: _ItineraryCard(itinerary: itineraries[index]),
        ),
      ),
    );
  }
}

class _ItineraryCard extends StatelessWidget {
  final TravelItinerary itinerary;

  const _ItineraryCard({required this.itinerary});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final languageCode = Localizations.localeOf(context).languageCode;
    final dateFormatter = MaterialLocalizations.of(context);
    final destinations = itinerary.destinationIds
        .map(DestinationRepository.findById)
        .whereType<Destination>()
        .toList();

    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        side: const BorderSide(color: AppColors.line),
        borderRadius: BorderRadius.circular(8),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.pushNamed(
          'itineraryEdit',
          pathParameters: {'id': itinerary.id},
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 8, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: AppColors.primaryBg,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.map_outlined,
                      color: AppColors.primaryDark,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          itinerary.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.ink,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${dateFormatter.formatMediumDate(itinerary.startDate)}'
                          ' - '
                          '${dateFormatter.formatMediumDate(itinerary.endDate)}'
                          ' · ${l10n.itineraryDays(itinerary.dayCount)}',
                          style: const TextStyle(
                            color: AppColors.ink2,
                            fontSize: 12.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                  PopupMenuButton<_ItineraryAction>(
                    tooltip: l10n.itineraryActions,
                    onSelected: (action) {
                      if (action == _ItineraryAction.edit) {
                        context.pushNamed(
                          'itineraryEdit',
                          pathParameters: {'id': itinerary.id},
                        );
                      } else {
                        _confirmDelete(context);
                      }
                    },
                    itemBuilder: (context) => [
                      PopupMenuItem(
                        value: _ItineraryAction.edit,
                        child: Row(
                          children: [
                            const Icon(Icons.edit_outlined, size: 19),
                            const SizedBox(width: 10),
                            Text(l10n.itineraryEditAction),
                          ],
                        ),
                      ),
                      PopupMenuItem(
                        value: _ItineraryAction.delete,
                        child: Row(
                          children: [
                            const Icon(
                              Icons.delete_outline,
                              size: 19,
                              color: AppColors.danger,
                            ),
                            const SizedBox(width: 10),
                            Text(
                              l10n.itineraryDeleteAction,
                              style: const TextStyle(color: AppColors.danger),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              if (destinations.isNotEmpty) ...[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: destinations
                      .map(
                        (destination) => Chip(
                          avatar: const Icon(
                            Icons.location_on_outlined,
                            size: 16,
                          ),
                          label: Text(destination.getName(languageCode)),
                          visualDensity: VisualDensity.compact,
                          side: const BorderSide(color: AppColors.line),
                          backgroundColor: AppColors.pageBg,
                        ),
                      )
                      .toList(),
                ),
              ],
              if (itinerary.notes.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  itinerary.notes,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.ink2,
                    fontSize: 13,
                    height: 1.45,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.itineraryDeleteTitle),
        content: Text(l10n.itineraryDeleteBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.danger,
            ),
            child: Text(l10n.itineraryDeleteAction),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      await context.read<ItineraryProvider>().delete(itinerary.id);
    }
  }
}

enum _ItineraryAction { edit, delete }
