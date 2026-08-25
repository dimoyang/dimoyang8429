import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/medical_service.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';

/// 医疗服务卡片
class ServiceCard extends StatelessWidget {
  final MedicalService service;

  const ServiceCard({super.key, required this.service});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final langCode = Localizations.localeOf(context).languageCode;
    return GestureDetector(
      onTap: () => context.pushNamed('serviceDetail',
          pathParameters: {'serviceId': service.id}),
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
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
            SizedBox(
              height: 140,
              width: double.infinity,
              child: RemoteImage(
                url: service.imageUrl,
                alt: service.nameEn,
                fallbackIcon: Icons.local_hospital_outlined,
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      service.getName(langCode),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        const Text('🏥', style: TextStyle(fontSize: 11)),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            service.hospital,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 11.5, color: AppColors.ink3),
                          ),
                        ),
                      ],
                    ),
                    const Spacer(),
                    Row(
                      children: [
                        Icon(Icons.access_time,
                            size: 12, color: AppColors.ink3),
                        const SizedBox(width: 4),
                        Text(
                          l10n.daysTreatment(service.durationDays),
                          style: const TextStyle(
                              fontSize: 11.5, color: AppColors.ink3),
                        ),
                        const Spacer(),
                        Text(
                          '${l10n.startingFrom} ${service.priceFrom}',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
