import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/service_card.dart';

/// 健康之旅列表页（医疗服务隐藏入口）
class MedicalListScreen extends StatelessWidget {
  const MedicalListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final services = ServiceRepository.sampleServices;

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.medicalListTitle),
        centerTitle: false,
      ),
      body: ListView(
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
  }
}
