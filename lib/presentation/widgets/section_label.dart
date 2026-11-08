import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 设置分组标题。
class SectionLabel extends StatelessWidget {
  final String text;

  const SectionLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.ink2,
        fontSize: 12,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}
