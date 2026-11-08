import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/data/models/medical_service.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
import 'package:meditour_app/presentation/widgets/service_card.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';

/// 健康之旅列表页（医疗服务隐藏入口）
class MedicalListScreen extends StatefulWidget {
  const MedicalListScreen({super.key});

  @override
  State<MedicalListScreen> createState() => _MedicalListScreenState();
}

class _MedicalListScreenState extends State<MedicalListScreen> {
  late Future<List<MedicalService>> _future = ServiceRepository.getServices();

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
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              // 样例数据不足一屏时也允许下拉刷新。
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 26),
              children: [
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
                ...services.map(
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
