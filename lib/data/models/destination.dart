/// 目的地必玩体验
class DestinationExperience {
  final String icon;
  final String title;
  final String description;

  const DestinationExperience({
    required this.icon,
    required this.title,
    required this.description,
  });
}

/// 旅行目的地
///
/// 当前内容以中文提供；多语言内容待接入数据层后按语言返回。
class Destination {
  final String id;
  final String name;
  final String nameEn;
  final String tagline;
  final String imageUrl;
  final String bestSeason;
  final String suggestDays;
  final String intro;
  final List<DestinationExperience> experiences;
  final List<String> tips;

  const Destination({
    required this.id,
    required this.name,
    required this.nameEn,
    required this.tagline,
    required this.imageUrl,
    required this.bestSeason,
    required this.suggestDays,
    required this.intro,
    required this.experiences,
    required this.tips,
  });

  /// 根据当前语言获取名称
  String getName(String languageCode) {
    switch (languageCode) {
      case 'zh':
        return name;
      default:
        return nameEn;
    }
  }
}
