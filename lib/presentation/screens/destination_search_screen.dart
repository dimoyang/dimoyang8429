import 'package:flutter/material.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/services/recent_search_store.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/destination_card.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';
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
  List<String> _recentSearches = const [];

  @override
  void initState() {
    super.initState();
    _loadRecentSearches();
  }

  Future<void> _loadRecentSearches() async {
    try {
      final searches = await RecentSearchStore.load();
      if (!mounted) {
        return;
      }
      setState(() => _recentSearches = searches);
    } catch (_) {
      // 本地历史读取失败不影响搜索本身。
    }
  }

  Future<void> _rememberQuery(String query) async {
    try {
      final searches = await RecentSearchStore.add(query);
      if (!mounted) {
        return;
      }
      setState(() => _recentSearches = searches);
    } catch (_) {
      // 历史写失败不影响当前搜索。
    }
  }

  Future<void> _removeRecent(String query) async {
    try {
      final searches = await RecentSearchStore.remove(query);
      if (!mounted) {
        return;
      }
      setState(() => _recentSearches = searches);
    } catch (_) {
      // 保持旧列表，不打断搜索。
    }
  }

  Future<void> _clearRecentSearches() async {
    setState(() => _recentSearches = const []);
    try {
      await RecentSearchStore.clear();
    } catch (_) {
      // 清理失败时列表已从界面移除，下次加载会重新读取。
    }
  }

  /// 选中最近搜索或建议词：填入输入框、立即应用并写入历史。
  void _applyQuery(String raw) {
    final query = raw.trim();
    if (query.isEmpty) {
      return;
    }
    _queryRevision++;
    _appliedQuery = query;
    _searchController.text = query;
    _searchController.selection = TextSelection.collapsed(offset: query.length);
    setState(() {});
    _rememberQuery(query);
  }

  void _clearQuery() {
    _queryRevision++;
    _appliedQuery = '';
    _searchController.clear();
    setState(() {});
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final favorites = context.watch<FavoritesProvider>();
    final destinationProvider = context.watch<DestinationProvider>();
    final destinations = _filterDestinations(favorites, destinationProvider);
    final hasQuery = _searchController.text.trim().isNotEmpty;

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
                  onChanged: _onQueryChanged,
                  onSubmitted: _applyQuery,
                  decoration: InputDecoration(
                    hintText: l10n.searchHint,
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchController.text.isEmpty
                        ? null
                        : IconButton(
                            tooltip: l10n.clearSearch,
                            onPressed: _clearQuery,
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
                if (!hasQuery && _recentSearches.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _buildRecentSearches(l10n),
                ],
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
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
              ],
            ),
          ),
          Expanded(
            child: _favoritesOnly && favorites.loadFailed
                ? ErrorState(
                    icon: Icons.favorite_border,
                    title: l10n.medicalLoadFailed,
                    message: l10n.errorUnknown,
                    onRetry: favorites.load,
                  )
                : _favoritesOnly && !favorites.isLoaded
                    ? _buildGridSkeleton(l10n)
                    : destinations.isEmpty
                        ? _EmptySearchResult(
                            favoritesOnly: _favoritesOnly,
                            hasQuery: hasQuery,
                            suggestions: hasQuery
                                ? _suggestions(
                                    destinationProvider.destinations,
                                  )
                                : const [],
                            onSuggestion: _applyQuery,
                            onClearQuery: _clearQuery,
                            onShowAll: () =>
                                setState(() => _favoritesOnly = false),
                          )
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
                                  childAspectRatio: destinationCardAspectRatio(
                                    context,
                                  ),
                                ),
                                itemCount: destinations.length,
                                itemBuilder: (context, index) =>
                                    DestinationCard(
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

  /// 最近搜索：仅在输入框为空时展示，可单条删除或清空。
  Widget _buildRecentSearches(AppLocalizations l10n) {
    return SizedBox(
      width: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                l10n.searchRecentTitle,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                  color: AppColors.ink2,
                ),
              ),
              const Spacer(),
              TextButton(
                onPressed: _clearRecentSearches,
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.ink2,
                  minimumSize: const Size(0, 32),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                ),
                child: Text(
                  l10n.searchRecentClear,
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              for (final term in _recentSearches)
                InputChip(
                  label: Text(term, style: const TextStyle(fontSize: 12.5)),
                  onPressed: () => _applyQuery(term),
                  onDeleted: () => _removeRecent(term),
                  deleteButtonTooltipMessage: l10n.searchRecentRemove,
                  visualDensity: VisualDensity.compact,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
            ],
          ),
        ],
      ),
    );
  }

  /// 无结果时的可点击建议：取当前语言下的热门目的地名称。
  List<String> _suggestions(List<Destination> destinations) {
    final langCode = Localizations.localeOf(context).languageCode;
    final names = <String>[];
    for (final destination in destinations) {
      final name = destination.getName(langCode).trim();
      if (name.isEmpty || names.contains(name)) {
        continue;
      }
      names.add(name);
      if (names.length == 4) {
        break;
      }
    }
    return names;
  }

  /// 收藏筛选加载骨架：卡片比例与 DestinationCard 一致，避免加载完成跳版。
  Widget _buildGridSkeleton(AppLocalizations l10n) {
    return SkeletonArea(
      label: l10n.loading,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final columns = constraints.maxWidth >= 900
              ? 4
              : constraints.maxWidth >= 600
                  ? 3
                  : 2;
          return GridView.builder(
            physics: const NeverScrollableScrollPhysics(),
            padding: const EdgeInsets.all(20),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: columns,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: destinationCardAspectRatio(context),
            ),
            itemCount: columns * 2,
            itemBuilder: (_, __) => const SkeletonDestinationCard(),
          );
        },
      ),
    );
  }

  List<Destination> _filterDestinations(
    FavoritesProvider favorites,
    DestinationProvider destinationProvider,
  ) {
    final query = _searchController.text.trim().toLowerCase();

    return destinationProvider.destinations.where((destination) {
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

  String _appliedQuery = '';
  int _queryRevision = 0;

  /// 输入防抖：停止输入约 280ms 后才触发一次列表重建。
  void _onQueryChanged(String value) {
    final revision = ++_queryRevision;
    Future<void>.delayed(const Duration(milliseconds: 280), () {
      if (!mounted || revision != _queryRevision) {
        return;
      }
      if (value == _appliedQuery) {
        return;
      }
      _appliedQuery = value;
      setState(() {});
    });
  }
}

class _EmptySearchResult extends StatelessWidget {
  final bool favoritesOnly;
  final bool hasQuery;
  final List<String> suggestions;
  final ValueChanged<String> onSuggestion;
  final VoidCallback onClearQuery;
  final VoidCallback onShowAll;

  const _EmptySearchResult({
    required this.favoritesOnly,
    required this.hasQuery,
    required this.suggestions,
    required this.onSuggestion,
    required this.onClearQuery,
    required this.onShowAll,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final onlyFavoritesEmpty = favoritesOnly && !hasQuery;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              onlyFavoritesEmpty ? Icons.favorite_outline : Icons.search_off,
              size: 42,
              color: AppColors.ink3,
            ),
            const SizedBox(height: 14),
            Text(
              onlyFavoritesEmpty
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
              onlyFavoritesEmpty
                  ? l10n.favoriteEmptyBody
                  : l10n.searchNoResultsBody,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.ink2,
                fontSize: 13,
                height: 1.5,
              ),
            ),
            if (favoritesOnly || hasQuery) ...[
              const SizedBox(height: 18),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (favoritesOnly)
                    OutlinedButton.icon(
                      onPressed: onShowAll,
                      icon: const Icon(Icons.public, size: 18),
                      label: Text(l10n.searchShowAll),
                    ),
                  if (hasQuery)
                    TextButton.icon(
                      onPressed: onClearQuery,
                      icon: const Icon(Icons.close, size: 18),
                      label: Text(l10n.clearSearch),
                    ),
                ],
              ),
            ],
            if (hasQuery && suggestions.isNotEmpty) ...[
              const SizedBox(height: 24),
              Text(
                l10n.searchSuggestionsLabel,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.ink2,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final suggestion in suggestions)
                    ActionChip(
                      label: Text(suggestion),
                      onPressed: () => onSuggestion(suggestion),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
