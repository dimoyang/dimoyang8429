import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/back_button.dart';
import 'package:meditour_app/presentation/widgets/destination_favorite_button.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';

/// 目的地详情页
class DestinationDetailScreen extends StatelessWidget {
  final String destinationId;

  const DestinationDetailScreen({super.key, required this.destinationId});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final langCode = Localizations.localeOf(context).languageCode;
    final destination = DestinationRepository.findById(destinationId);

    if (destination == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.destinationNotFound)),
        body: Center(child: Text(l10n.destinationNotFound)),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      body: Stack(
        children: [
          Column(
            children: [
              Expanded(
                child: ListView(
                  padding: EdgeInsets.zero,
                  children: [
                    _buildHero(context, destination, langCode),
                    Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildTitleRow(destination, langCode),
                          const SizedBox(height: 6),
                          Text(
                            destination.tagline,
                            style: const TextStyle(
                              fontSize: 13.5,
                              color: AppColors.ink2,
                            ),
                          ),
                          const SizedBox(height: 14),
                          _buildStatsRow(l10n, destination),
                          _buildSection(l10n.sectionImpression),
                          Text(
                            destination.intro,
                            style: const TextStyle(
                              fontSize: 14,
                              height: 1.75,
                              color: AppColors.ink2,
                            ),
                          ),
                          _buildSection(l10n.sectionExperiences),
                          ...destination.experiences
                              .map((e) => _buildExperience(e)),
                          _buildSection(l10n.sectionTravelTips),
                          ...destination.tips.map(_buildTip),
                          const SizedBox(height: 96),
                        ],
                      ),
                    ),
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
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(l10n.itineraryComingSoon),
                        behavior: SnackBarBehavior.floating,
                      ),
                    );
                  },
                  child: Text(
                    l10n.btnItinerary,
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
      BuildContext context, Destination destination, String langCode) {
    return Stack(
      children: [
        AspectRatio(
          aspectRatio: 4 / 3,
          child: RemoteImage(
            url: destination.imageUrl,
            alt: destination.getName(langCode),
            fallbackIcon: Icons.location_city_outlined,
          ),
        ),
        Positioned(
          top: MediaQuery.of(context).padding.top + 8,
          left: 16,
          child: AppBackButton(onPressed: () => Navigator.of(context).pop()),
        ),
        Positioned(
          top: MediaQuery.of(context).padding.top + 8,
          right: 16,
          child: DestinationFavoriteButton(destinationId: destination.id),
        ),
      ],
    );
  }

  Widget _buildTitleRow(Destination destination, String langCode) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Text(
          destination.getName(langCode),
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
        ),
        if (langCode != 'zh') ...[
          const SizedBox(width: 10),
          Text(
            destination.name,
            style: const TextStyle(fontSize: 13, color: AppColors.ink3),
          ),
        ],
      ],
    );
  }

  Widget _buildStatsRow(AppLocalizations l10n, Destination destination) {
    return Row(
      children: [
        Expanded(
          child: _StatChip(
              label: l10n.statBestSeason, value: destination.bestSeason),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatChip(
              label: l10n.statSuggestDays, value: destination.suggestDays),
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

  Widget _buildExperience(DestinationExperience exp) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(13),
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
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: AppColors.primaryBg,
              borderRadius: BorderRadius.circular(11),
            ),
            child: Center(
              child: Text(exp.icon, style: const TextStyle(fontSize: 18)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  exp.title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.ink,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  exp.description,
                  style: const TextStyle(
                    fontSize: 12.5,
                    color: AppColors.ink2,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTip(String tip) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
      decoration: BoxDecoration(
        color: AppColors.tipBg,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('💡', style: TextStyle(fontSize: 13)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              tip,
              style: const TextStyle(
                fontSize: 13,
                color: AppColors.ink2,
                height: 1.6,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label;
  final String value;

  const _StatChip({required this.label, required this.value});

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
