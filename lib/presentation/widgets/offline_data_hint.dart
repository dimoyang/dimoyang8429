import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 内联离线提示：不遮挡内容、不弹窗，只说明当前展示的是本地兜底数据。
class OfflineDataHint extends StatelessWidget {
  final String message;

  const OfflineDataHint({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.primaryBg,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              size: 16,
              color: AppColors.ink3,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  fontSize: 12,
                  height: 1.4,
                  color: AppColors.ink3,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
