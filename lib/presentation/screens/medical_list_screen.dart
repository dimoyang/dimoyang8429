import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/data/models/medical_service.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/service_card.dart';

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

  /// 加载失败时的错误态：提示具体原因并支持重试。
  Widget _buildErrorState(AppLocalizations l10n, Object? error) {
    final message = error is ApiException
        ? error.toLocalizedMessage(l10n)
        : l10n.errorUnknown;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              size: 46,
              color: AppColors.ink3,
            ),
            const SizedBox(height: 14),
            Text(
              l10n.medicalLoadFailed,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: AppColors.ink,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 13,
                height: 1.5,
                color: AppColors.ink2,
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => _refresh(),
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
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _buildErrorState(l10n, snapshot.error);
          }
          final services = snapshot.data ?? const <MedicalService>[];
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
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
                      const Text('💚', style: TextStyle(fontSize: 14)),
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
