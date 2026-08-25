import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/destination_card.dart';
import 'package:meditour_app/presentation/widgets/language_picker_sheet.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';

/// 首页：中国旅行门户。
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: AppColors.pageBg,
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            _buildHeader(context, l10n),
            const SizedBox(height: 16),
            _buildHero(context, l10n),
            const SizedBox(height: 16),
            _buildServiceChips(context, l10n),
            _buildSectionTitle(
                context, l10n.sectionDestinations, l10n.sectionDestinationsSub),
            _buildDestinationGrid(context),
            const SizedBox(height: 4),
            _buildSectionTitle(context, l10n.sectionTips, ''),
            _buildTravelTips(l10n),
            const SizedBox(height: 22),
            Center(
              child: Text(
                l10n.footerText,
                style: const TextStyle(fontSize: 11, color: AppColors.ink3),
              ),
            ),
            const SizedBox(height: 26),
          ],
        ),
      ),
    );
  }

  /* SECTION: header */
  Widget _buildHeader(BuildContext context, AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 16),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.primary, AppColors.primaryDark],
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Center(
                  child: Text('🐉', style: TextStyle(fontSize: 20)),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.appTitle,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 19,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1,
                      ),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      l10n.appSubtitle,
                      style:
                          const TextStyle(color: Colors.white70, fontSize: 11),
                    ),
                  ],
                ),
              ),
              _LanguageButton(),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            l10n.tagline,
            style: const TextStyle(color: Colors.white70, fontSize: 14),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.taglineSubtitle,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 21,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          // 搜索栏
          GestureDetector(
            onTap: () => context.pushNamed('destinationSearch'),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(999),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x1F0F172A),
                    blurRadius: 14,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  const Icon(Icons.search, size: 17, color: AppColors.ink3),
                  const SizedBox(width: 8),
                  Text(
                    l10n.searchHint,
                    style: const TextStyle(color: AppColors.ink3, fontSize: 14),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /* SECTION: hero */
  Widget _buildHero(BuildContext context, AppLocalizations l10n) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Stack(
          children: [
            const AspectRatio(
              aspectRatio: 16 / 10,
              child: RemoteImage(
                url: DestinationRepository.heroImageUrl,
                alt: 'Great Wall',
                fallbackIcon: Icons.landscape_outlined,
              ),
            ),
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black.withValues(alpha: 0.72),
                    ],
                    stops: const [0.35, 1.0],
                  ),
                ),
              ),
            ),
            Positioned(
              left: 16,
              right: 16,
              bottom: 14,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.heroTitle,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    l10n.heroSubtitle,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /* SECTION: service-chips */
  Widget _buildServiceChips(BuildContext context, AppLocalizations l10n) {
    final chips = [
      ('🛂', l10n.chipVisa),
      ('🚄', l10n.chipTransport),
      ('🏨', l10n.chipHotel),
      ('🗺️', l10n.chipItinerary),
    ];
    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 9),
        itemBuilder: (context, index) {
          final chip = chips[index];
          return GestureDetector(
            onTap: () {
              if (index == 0 || index == 1) {
                context.go('/travel-tools');
              } else if (index == 3) {
                context.go('/itinerary');
              } else {
                _showToast(context, l10n.chipComingSoon);
              }
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.line),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x0F0F172A),
                    blurRadius: 12,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Text(chip.$1, style: const TextStyle(fontSize: 13)),
                  const SizedBox(width: 6),
                  Text(
                    chip.$2,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.ink2,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  /* SECTION: destination-grid */
  Widget _buildSectionTitle(BuildContext context, String title, String sub) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          ),
          Text(sub,
              style: const TextStyle(fontSize: 12, color: AppColors.ink3)),
        ],
      ),
    );
  }

  Widget _buildDestinationGrid(BuildContext context) {
    final destinations = DestinationRepository.destinations;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 4 / 5,
        children:
            destinations.map((d) => DestinationCard(destination: d)).toList(),
      ),
    );
  }

  /* SECTION: travel-tips */
  Widget _buildTravelTips(AppLocalizations l10n) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: [
          _TipCard(icon: '💳', text: l10n.tipPayment),
          const SizedBox(height: 8),
          _TipCard(icon: '📱', text: l10n.tipSim),
        ],
      ),
    );
  }

  void _showToast(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }
}

/* SECTION: language-button */
class _LanguageButton extends StatelessWidget {
  const _LanguageButton();
  @override
  Widget build(BuildContext context) {
    final provider = context.watch<LanguageProvider>();
    final currentCode = provider.currentLocale.languageCode;
    final current = LanguageProvider.languageOptions.firstWhere(
      (o) => o.$1 == currentCode,
      orElse: () => LanguageProvider.languageOptions.first,
    );
    return GestureDetector(
      onTap: () => showLanguagePickerSheet(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.16),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          children: [
            Text(current.$3, style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 4),
            Text(
              current.$2,
              style: const TextStyle(color: Colors.white, fontSize: 11.5),
            ),
            const SizedBox(width: 2),
            const Icon(Icons.expand_more, color: Colors.white70, size: 14),
          ],
        ),
      ),
    );
  }
}

/* SECTION: tip-card */
class _TipCard extends StatelessWidget {
  final String icon;
  final String text;

  const _TipCard({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
      decoration: BoxDecoration(
        color: AppColors.tipBg,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(icon, style: const TextStyle(fontSize: 13)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
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
