import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/medical_service.dart'
    show MedicalService, ProcessStep;
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/back_button.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';

/// 服务详情页
class ServiceDetailScreen extends StatelessWidget {
  final String serviceId;

  const ServiceDetailScreen({super.key, required this.serviceId});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final langCode = Localizations.localeOf(context).languageCode;
    final service = ServiceRepository.findById(serviceId);

    if (service == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.serviceNotFound)),
        body: Center(child: Text(l10n.serviceNotFound)),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      body: Stack(
        children: [
          ListView(
            padding: EdgeInsets.zero,
            children: [
              _buildHero(context, service, langCode),
              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildTitleRow(service, langCode),
                    const SizedBox(height: 14),
                    _buildStatsRow(l10n, service),
                    _buildSection(l10n.sectionIntro),
                    Text(
                      service.intro,
                      style: const TextStyle(
                        fontSize: 14,
                        height: 1.75,
                        color: AppColors.ink2,
                      ),
                    ),
                    _buildSection(l10n.sectionHighlights),
                    ...service.highlights.map(_buildHighlight),
                    _buildSection(l10n.sectionProcess),
                    ...service.process.map(_buildProcessStepItem),
                    const SizedBox(height: 96),
                  ],
                ),
              ),
            ],
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.92),
                border: const Border(top: BorderSide(color: AppColors.line)),
              ),
              child: SafeArea(
                top: false,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(52),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                  onPressed: () {
                    context.pushNamed('booking',
                        pathParameters: {'serviceId': service.id});
                  },
                  child: Text(
                    l10n.btnBookConsult,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHero(
      BuildContext context, MedicalService service, String langCode) {
    return Stack(
      children: [
        AspectRatio(
          aspectRatio: 4 / 3,
          child: RemoteImage(
            url: service.imageUrl,
            alt: service.getName(langCode),
            fallbackIcon: Icons.local_hospital_outlined,
          ),
        ),
        Positioned(
          top: MediaQuery.of(context).padding.top + 8,
          left: 16,
          child: AppBackButton(onPressed: () => Navigator.of(context).pop()),
        ),
      ],
    );
  }

  Widget _buildTitleRow(MedicalService service, String langCode) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Expanded(
          child: Text(
            service.getName(langCode),
            style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
          ),
        ),
      ],
    );
  }

  Widget _buildStatsRow(AppLocalizations l10n, MedicalService service) {
    return Row(
      children: [
        Expanded(
          child: _StatItem(
              label: l10n.statDuration,
              value: l10n.daysTreatment(service.durationDays)),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatItem(label: l10n.statBasePrice, value: service.priceFrom),
        ),
      ],
    );
  }

  Widget _buildSection(String title) {
    return Padding(
      padding: const EdgeInsets.only(top: 20, bottom: 10),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 15,
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 7),
          Text(
            title,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  Widget _buildHighlight(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Text('✓ ',
                style: TextStyle(
                    color: AppColors.primary, fontWeight: FontWeight.w700)),
          ),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                  fontSize: 13.5, height: 1.6, color: AppColors.ink2),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProcessStepItem(ProcessStep step) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 24,
            height: 24,
            margin: const EdgeInsets.only(top: 2),
            decoration: BoxDecoration(
              color: AppColors.primaryBg,
              borderRadius: BorderRadius.circular(7),
            ),
            child: Center(
              child: Text(
                step.step,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryDark,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  step.description,
                  style: const TextStyle(
                      fontSize: 13.5, height: 1.6, color: AppColors.ink2),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0F0F172A),
            blurRadius: 12,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 11, color: AppColors.ink3)),
          const SizedBox(height: 3),
          Text(
            value,
            style: const TextStyle(
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
              color: AppColors.primaryDark,
            ),
          ),
        ],
      ),
    );
  }
}
