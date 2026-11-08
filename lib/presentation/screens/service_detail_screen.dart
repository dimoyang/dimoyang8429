import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/data/models/medical_service.dart'
    show MedicalService, ProcessStep;
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/back_button.dart';
import 'package:meditour_app/presentation/widgets/detail_bottom_bar.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';
import 'package:meditour_app/presentation/widgets/stat_tile.dart';

/// 服务详情页
class ServiceDetailScreen extends StatefulWidget {
  final String serviceId;

  const ServiceDetailScreen({super.key, required this.serviceId});

  @override
  State<ServiceDetailScreen> createState() => _ServiceDetailScreenState();
}

class _ServiceDetailScreenState extends State<ServiceDetailScreen> {
  late Future<MedicalService?> _serviceFuture;

  @override
  void initState() {
    super.initState();
    _serviceFuture = ServiceRepository.getService(widget.serviceId);
  }

  void _reload() {
    setState(() {
      _serviceFuture = ServiceRepository.getService(widget.serviceId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return FutureBuilder<MedicalService?>(
      future: _serviceFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return _buildSkeleton(l10n);
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          final message = error is ApiException
              ? error.toLocalizedMessage(l10n)
              : l10n.errorUnknown;
          return ErrorScaffold(
            appBarTitle: l10n.medicalLoadFailed,
            title: l10n.medicalLoadFailed,
            message: message,
            onRetry: _reload,
          );
        }
        final service = snapshot.data;
        if (service == null) {
          return Scaffold(
            appBar: AppBar(title: Text(l10n.serviceNotFound)),
            body: Center(child: Text(l10n.serviceNotFound)),
          );
        }
        return _buildContent(context, service, l10n);
      },
    );
  }

  /// 详情加载骨架：hero、标题、统计块与正文段落的占位。
  ///
  /// 比例按真实布局估算，图片与统计块到位后不会出现明显跳动。
  Widget _buildSkeleton(AppLocalizations l10n) {
    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.medicalListTitle)),
      body: SkeletonArea(
        label: l10n.loading,
        child: ListView(
          physics: const NeverScrollableScrollPhysics(),
          padding: EdgeInsets.zero,
          children: [
            const AspectRatio(
              aspectRatio: 4 / 3,
              child: SkeletonBox(radius: 0),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  SkeletonLine(widthFactor: 0.62, height: 23),
                  SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(child: _SkeletonStatTile()),
                      SizedBox(width: 10),
                      Expanded(child: _SkeletonStatTile()),
                    ],
                  ),
                  SizedBox(height: 20),
                  SkeletonLine(widthFactor: 0.28, height: 15),
                  SizedBox(height: 12),
                  SkeletonLine(widthFactor: 1, height: 13),
                  SizedBox(height: 9),
                  SkeletonLine(widthFactor: 0.92, height: 13),
                  SizedBox(height: 9),
                  SkeletonLine(widthFactor: 0.86, height: 13),
                  SizedBox(height: 9),
                  SkeletonLine(widthFactor: 0.4, height: 13),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(
      BuildContext context, MedicalService service, AppLocalizations l10n) {
    final langCode = Localizations.localeOf(context).languageCode;

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
                      service.getIntro(langCode),
                      style: const TextStyle(
                        fontSize: 14,
                        height: 1.75,
                        color: AppColors.ink2,
                      ),
                    ),
                    if (service.highlights.isNotEmpty) ...[
                      _buildSection(l10n.sectionHighlights),
                      ...service.highlights.map(_buildHighlight),
                    ],
                    if (service.process.isNotEmpty) ...[
                      _buildSection(l10n.sectionProcess),
                      ...service.process.map(_buildProcessStepItem),
                    ],
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
            child: DetailBottomBar(
              label: l10n.btnBookConsult,
              onPressed: () {
                context.pushNamed('booking',
                    pathParameters: {'serviceId': service.id});
              },
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
          child: StatTile(
              label: l10n.statDuration,
              value: l10n.daysTreatment(service.durationDays)),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatTile(
            label: l10n.statBasePrice,
            value: l10n.startingFrom(service.priceFrom),
          ),
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
                    color: AppColors.primaryDark, fontWeight: FontWeight.w700)),
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

/// 与 StatTile 等高的静态占位块。
class _SkeletonStatTile extends StatelessWidget {
  const _SkeletonStatTile();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          SkeletonLine(widthFactor: 0.55, height: 10),
          SizedBox(height: 5),
          SkeletonLine(widthFactor: 0.72, height: 13),
        ],
      ),
    );
  }
}
