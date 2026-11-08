import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/add_to_itinerary_sheet.dart';
import 'package:meditour_app/presentation/widgets/back_button.dart';
import 'package:meditour_app/presentation/widgets/destination_favorite_button.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';
import 'package:provider/provider.dart';
import 'package:meditour_app/presentation/widgets/stat_tile.dart';
import 'package:meditour_app/presentation/widgets/detail_bottom_bar.dart';

/// 目的地详情页
class DestinationDetailScreen extends StatelessWidget {
  final String destinationId;

  const DestinationDetailScreen({super.key, required this.destinationId});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final langCode = Localizations.localeOf(context).languageCode;
    final destination =
        context.watch<DestinationProvider>().findById(destinationId);

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
                          SizedBox(
                            height: 96 + MediaQuery.paddingOf(context).bottom,
                          ),
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
            child: DetailBottomBar(
              label: l10n.btnItinerary,
              onPressed: () => showAddToItinerarySheet(
                context,
                destination: destination,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHero(
      BuildContext context, Destination destination, String langCode) {
    // 横屏时限制 hero 高度，避免首屏只剩图片、看不到主内容。
    final screen = MediaQuery.sizeOf(context);
    final heroHeight = math.min(screen.width * 3 / 4, screen.height * 0.55);
    return Stack(
      children: [
        SizedBox(
          height: heroHeight,
          child: RemoteImage(
            url: destination.imageUrl,
            alt: destination.getName(langCode),
            fallbackIcon: Icons.location_city_outlined,
          ),
        ),
        Positioned(
          top: MediaQuery.of(context).padding.top + 8,
          left: MediaQuery.of(context).padding.left + 16,
          child: AppBackButton(onPressed: () => Navigator.of(context).pop()),
        ),
        Positioned(
          top: MediaQuery.of(context).padding.top + 8,
          right: MediaQuery.of(context).padding.right + 16,
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
        Flexible(
          child: Text(
            destination.getName(langCode),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
          ),
        ),
        if (langCode != 'zh') ...[
          const SizedBox(width: 10),
          Flexible(
            child: Text(
              destination.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13, color: AppColors.ink3),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStatsRow(AppLocalizations l10n, Destination destination) {
    return Row(
      children: [
        Expanded(
          child: StatTile(
              label: l10n.statBestSeason, value: destination.bestSeason),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatTile(
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
              child: ExcludeSemantics(
                child: Text(exp.icon, style: const TextStyle(fontSize: 18)),
              ),
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
          const ExcludeSemantics(
            child: Text('💡', style: TextStyle(fontSize: 13)),
          ),
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
