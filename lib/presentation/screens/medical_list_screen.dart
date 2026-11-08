import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/data/models/medical_service.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
import 'package:meditour_app/presentation/widgets/service_card.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';

/// 价格筛选区间。
enum _PriceFilter { all, under5000, between5000And10000, over10000 }

/// 排序方式。
enum _SortOption { recommended, priceAsc, priceDesc }

/// 健康之旅列表页（医疗服务隐藏入口）
///
/// 筛选与排序只作用于当前已加载的一页数据（后端 `page_size` 上限 100），
/// 不额外请求后端参数，因此页面会明确提示这一限制。
class MedicalListScreen extends StatefulWidget {
  const MedicalListScreen({super.key});

  @override
  State<MedicalListScreen> createState() => _MedicalListScreenState();
}

class _MedicalListScreenState extends State<MedicalListScreen> {
  late Future<List<MedicalService>> _future = ServiceRepository.getServices();

  /// 筛选状态保存在页面 State 中：进入详情再返回、下拉刷新都不会重置。
  String? _category;
  _PriceFilter _priceFilter = _PriceFilter.all;
  _SortOption _sortOption = _SortOption.recommended;

  bool get _hasActiveFilters =>
      _category != null ||
      _priceFilter != _PriceFilter.all ||
      _sortOption != _SortOption.recommended;

  Future<void> _refresh() async {
    setState(() {
      _future = ServiceRepository.getServices(forceRemote: true);
    });
    try {
      await _future;
    } catch (_) {
      // 错误由 FutureBuilder 以错误态呈现。
    }
  }

  void _clearFilters() {
    setState(() {
      _category = null;
      _priceFilter = _PriceFilter.all;
      _sortOption = _SortOption.recommended;
    });
  }

  /// 加载骨架：间距、卡片高度与真实列表一致，避免加载完成时大幅跳动。
  Widget _buildSkeleton(AppLocalizations l10n) {
    return SkeletonArea(
      label: l10n.loading,
      child: ListView(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 26),
        children: [
          const SkeletonBox(height: 68, radius: 14),
          const SizedBox(height: 16),
          for (var i = 0; i < 3; i++) ...[
            const _SkeletonServiceCard(),
            if (i < 2) const SizedBox(height: 14),
          ],
        ],
      ),
    );
  }

  /// 后端返回空列表时的空数据态，避免整页只剩留白。
  Widget _buildEmptyState(AppLocalizations l10n) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.local_hospital_outlined,
              size: 46,
              color: AppColors.ink3,
            ),
            const SizedBox(height: 14),
            Text(
              l10n.medicalEmptyTitle,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: AppColors.ink,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              l10n.medicalEmptyBody,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 13,
                height: 1.5,
                color: AppColors.ink2,
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _refresh,
              child: Text(l10n.retry),
            ),
          ],
        ),
      ),
    );
  }

  /// 有数据但被筛选为空：与「本来就没有数据」区分，并给出清除入口。
  Widget _buildFilteredEmptyState(AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 34),
      child: Column(
        children: [
          const Icon(
            Icons.filter_alt_off_outlined,
            size: 46,
            color: AppColors.ink3,
          ),
          const SizedBox(height: 14),
          Text(
            l10n.medicalFilteredEmptyTitle,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: AppColors.ink,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            l10n.medicalFilteredEmptyBody,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 13,
              height: 1.5,
              color: AppColors.ink2,
            ),
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: _clearFilters,
            icon: const Icon(Icons.filter_alt_off_outlined, size: 18),
            label: Text(l10n.medicalClearFilters),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.medicalListTitle),
        centerTitle: false,
      ),
      body: FutureBuilder<List<MedicalService>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return _buildSkeleton(l10n);
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return ErrorState(
              title: l10n.medicalLoadFailed,
              message: error is ApiException
                  ? error.toLocalizedMessage(l10n)
                  : l10n.errorUnknown,
              onRetry: _refresh,
            );
          }
          final services = snapshot.data ?? const <MedicalService>[];
          if (services.isEmpty) {
            return _buildEmptyState(l10n);
          }

          final categories = _categoriesOf(services);
          final visible = _applyFilters(services);

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              // 样例数据不足一屏时也允许下拉刷新。
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 26),
              children: [
                _buildFilterBar(l10n, categories),
                if (services.length >= 100) ...[
                  const SizedBox(height: 8),
                  Text(
                    l10n.medicalPageLimitHint,
                    style: const TextStyle(
                      fontSize: 12,
                      height: 1.5,
                      color: AppColors.ink3,
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.primaryBg,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const ExcludeSemantics(
                        child: Text('💚', style: TextStyle(fontSize: 14)),
                      ),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          l10n.medicalListInfo,
                          style: const TextStyle(
                            fontSize: 12.5,
                            height: 1.65,
                            color: AppColors.primaryDark,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                if (ServiceRepository.lastLoadWasSample) ...[
                  const SizedBox(height: 10),
                  Text(
                    l10n.medicalOfflineHint,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.ink3,
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                if (visible.isEmpty)
                  _buildFilteredEmptyState(l10n)
                else
                  ...visible.map(
                    (service) => Padding(
                      padding: const EdgeInsets.only(bottom: 14),
                      child: ServiceCard(service: service),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  /// 分类筛选、价格区间筛选与排序控件。
  Widget _buildFilterBar(
    AppLocalizations l10n,
    List<String> categories,
  ) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (categories.isNotEmpty)
            _FilterChipRow(
              label: l10n.medicalFilterCategory,
              children: [
                ChoiceChip(
                  label: Text(l10n.medicalFilterAll),
                  selected: _category == null,
                  onSelected: (_) => setState(() => _category = null),
                ),
                for (final category in categories)
                  ChoiceChip(
                    label: Text(_categoryLabel(l10n, category)),
                    selected: _category == category,
                    onSelected: (_) => setState(() => _category = category),
                  ),
              ],
            ),
          _FilterChipRow(
            label: l10n.medicalPriceFilter,
            children: [
              ChoiceChip(
                label: Text(l10n.medicalPriceAll),
                selected: _priceFilter == _PriceFilter.all,
                onSelected: (_) =>
                    setState(() => _priceFilter = _PriceFilter.all),
              ),
              ChoiceChip(
                label: Text(l10n.medicalPriceUnder5000),
                selected: _priceFilter == _PriceFilter.under5000,
                onSelected: (_) =>
                    setState(() => _priceFilter = _PriceFilter.under5000),
              ),
              ChoiceChip(
                label: Text(l10n.medicalPriceBetween),
                selected: _priceFilter == _PriceFilter.between5000And10000,
                onSelected: (_) => setState(
                  () => _priceFilter = _PriceFilter.between5000And10000,
                ),
              ),
              ChoiceChip(
                label: Text(l10n.medicalPriceOver10000),
                selected: _priceFilter == _PriceFilter.over10000,
                onSelected: (_) =>
                    setState(() => _priceFilter = _PriceFilter.over10000),
              ),
            ],
          ),
          _FilterChipRow(
            label: l10n.medicalSortFilter,
            children: [
              ChoiceChip(
                label: Text(l10n.medicalSortRecommended),
                selected: _sortOption == _SortOption.recommended,
                onSelected: (_) =>
                    setState(() => _sortOption = _SortOption.recommended),
              ),
              ChoiceChip(
                label: Text(l10n.medicalSortPriceAsc),
                selected: _sortOption == _SortOption.priceAsc,
                onSelected: (_) =>
                    setState(() => _sortOption = _SortOption.priceAsc),
              ),
              ChoiceChip(
                label: Text(l10n.medicalSortPriceDesc),
                selected: _sortOption == _SortOption.priceDesc,
                onSelected: (_) =>
                    setState(() => _sortOption = _SortOption.priceDesc),
              ),
            ],
          ),
          if (_hasActiveFilters)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: _clearFilters,
                icon: const Icon(Icons.clear, size: 16),
                label: Text(l10n.medicalClearFilters),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.primaryDark,
                  minimumSize: const Size(0, 36),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ),
        ],
      ),
    );
  }

  /// 保留原始顺序的分类列表。
  List<String> _categoriesOf(List<MedicalService> services) {
    final seen = <String>{};
    final result = <String>[];
    for (final service in services) {
      if (service.category.isEmpty || !seen.add(service.category)) {
        continue;
      }
      result.add(service.category);
    }
    return result;
  }

  /// 已知分类码走本地化名称，未知分类回退后端标签。
  String _categoryLabel(AppLocalizations l10n, String category) {
    return switch (category) {
      'orthopedics' => l10n.medicalCategoryOrthopedics,
      'dentistry' => l10n.medicalCategoryDentistry,
      'checkup' => l10n.medicalCategoryCheckup,
      _ => category,
    };
  }

  List<MedicalService> _applyFilters(List<MedicalService> services) {
    final filtered = services.where((service) {
      if (_category != null && service.category != _category) {
        return false;
      }
      return switch (_priceFilter) {
        _PriceFilter.all => true,
        _PriceFilter.under5000 => service.basePrice < 5000,
        _PriceFilter.between5000And10000 =>
          service.basePrice >= 5000 && service.basePrice <= 10000,
        _PriceFilter.over10000 => service.basePrice > 10000,
      };
    }).toList();

    switch (_sortOption) {
      case _SortOption.recommended:
        break;
      case _SortOption.priceAsc:
        filtered.sort((a, b) => a.basePrice.compareTo(b.basePrice));
      case _SortOption.priceDesc:
        filtered.sort((a, b) => b.basePrice.compareTo(a.basePrice));
    }
    return filtered;
  }
}

/// 一行筛选标签（标题 + 可横向滚动的选项）。
class _FilterChipRow extends StatelessWidget {
  final String label;
  final List<Widget> children;

  const _FilterChipRow({required this.label, required this.children});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            Text(
              label,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppColors.ink2,
              ),
            ),
            const SizedBox(width: 10),
            ...children,
          ],
        ),
      ),
    );
  }
}

/// 与 ServiceCard 尺寸对齐的静态占位卡（图 140 + 文案区）。
class _SkeletonServiceCard extends StatelessWidget {
  const _SkeletonServiceCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SkeletonBox(height: 140, radius: 0),
          Padding(
            padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                SkeletonLine(widthFactor: 0.72, height: 14),
                SizedBox(height: 8),
                SkeletonLine(widthFactor: 0.45, height: 11),
                SizedBox(height: 12),
                Row(
                  children: [
                    SkeletonBox(width: 82, height: 13, radius: 6),
                    Spacer(),
                    SkeletonBox(width: 62, height: 13, radius: 6),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
