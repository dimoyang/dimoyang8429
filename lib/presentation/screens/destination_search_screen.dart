import 'package:flutter/material.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/destination_card.dart';
import 'package:provider/provider.dart';

/// 支持关键词和收藏筛选的目的地搜索页。
class DestinationSearchScreen extends StatefulWidget {
  const DestinationSearchScreen({super.key});

  @override
  State<DestinationSearchScreen> createState() =>
      _DestinationSearchScreenState();
}

class _DestinationSearchScreenState extends State<DestinationSearchScreen> {
  final _searchController = TextEditingController();
  bool _favoritesOnly = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final favorites = context.watch<FavoritesProvider>();
    final destinations = _filterDestinations(favorites);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.destinationSearchTitle),
        centerTitle: false,
      ),
      body: Column(
        children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  autofocus: true,
                  textInputAction: TextInputAction.search,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: l10n.searchHint,
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchController.text.isEmpty
                        ? null
                        : IconButton(
                            tooltip: l10n.clearSearch,
                            onPressed: () {
                              _searchController.clear();
                              setState(() {});
                            },
                            icon: const Icon(Icons.close),
                          ),
                    filled: true,
                    fillColor: AppColors.pageBg,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: SizedBox(
                    width: 320,
                    child: SegmentedButton<bool>(
                      expandedInsets: EdgeInsets.zero,
                      showSelectedIcon: false,
                      segments: [
                        ButtonSegment(
                          value: false,
                          icon: const Icon(Icons.public, size: 18),
                          label: Text(l10n.destinationFilterAll),
                        ),
                        ButtonSegment(
                          value: true,
                          icon: const Icon(Icons.favorite_outline, size: 18),
                          label: Text(l10n.destinationFilterFavorites),
                        ),
                      ],
                      selected: {_favoritesOnly},
                      onSelectionChanged: (selection) {
                        setState(() => _favoritesOnly = selection.first);
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _favoritesOnly && !favorites.isLoaded
                ? const Center(child: CircularProgressIndicator())
                : destinations.isEmpty
                    ? _EmptySearchResult(favoritesOnly: _favoritesOnly)
                    : LayoutBuilder(
                        builder: (context, constraints) {
                          final columns = constraints.maxWidth >= 900
                              ? 4
                              : constraints.maxWidth >= 600
                                  ? 3
                                  : 2;
                          return GridView.builder(
                            padding: const EdgeInsets.all(20),
                            gridDelegate:
                                SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: columns,
                              mainAxisSpacing: 12,
                              crossAxisSpacing: 12,
                              childAspectRatio: 4 / 5,
                            ),
                            itemCount: destinations.length,
                            itemBuilder: (context, index) => DestinationCard(
                              destination: destinations[index],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }

  List<Destination> _filterDestinations(FavoritesProvider favorites) {
    final query = _searchController.text.trim().toLowerCase();

    return DestinationRepository.destinations.where((destination) {
      if (_favoritesOnly && !favorites.isFavorite(destination.id)) {
        return false;
      }
      if (query.isEmpty) {
        return true;
      }

      final searchableText = [
        destination.id,
        destination.name,
        destination.nameEn,
        destination.tagline,
        ...destination.searchTerms,
        ...destination.experiences.map((experience) => experience.title),
      ].join(' ').toLowerCase();
      return searchableText.contains(query);
    }).toList();
  }
}

class _EmptySearchResult extends StatelessWidget {
  final bool favoritesOnly;

  const _EmptySearchResult({required this.favoritesOnly});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              favoritesOnly ? Icons.favorite_outline : Icons.search_off,
              size: 42,
              color: AppColors.ink3,
            ),
            const SizedBox(height: 14),
            Text(
              favoritesOnly
                  ? l10n.favoriteEmptyTitle
                  : l10n.searchNoResultsTitle,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.ink,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              favoritesOnly ? l10n.favoriteEmptyBody : l10n.searchNoResultsBody,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.ink2,
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
