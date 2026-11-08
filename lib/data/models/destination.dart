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
  final List<String> searchTerms;
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
    required this.searchTerms,
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

  /// 从后端 /api/v1/destinations 响应解析。
  factory Destination.fromJson(Map<String, dynamic> json) {
    final rawExperiences = json['experiences'];
    final experiences = <DestinationExperience>[];
    if (rawExperiences is List) {
      for (final item in rawExperiences) {
        if (item is Map) {
          final map = Map<String, dynamic>.from(item);
          experiences.add(
            DestinationExperience(
              icon: map['icon'] as String? ?? '',
              title: map['title'] as String? ?? '',
              description: map['description'] as String? ?? '',
            ),
          );
        }
      }
    }

    return Destination(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      nameEn: json['name_en'] as String? ?? '',
      tagline: json['tagline'] as String? ?? '',
      imageUrl: json['image_url'] as String? ?? '',
      searchTerms: _stringList(json['search_terms']),
      bestSeason: json['best_season'] as String? ?? '',
      suggestDays: json['suggest_days'] as String? ?? '',
      intro: json['intro'] as String? ?? '',
      experiences: experiences,
      tips: _stringList(json['tips']),
    );
  }

  Map<String, Object> toJson() {
    return {
      'id': id,
      'name': name,
      'name_en': nameEn,
      'tagline': tagline,
      'image_url': imageUrl,
      'search_terms': searchTerms,
      'best_season': bestSeason,
      'suggest_days': suggestDays,
      'intro': intro,
      'experiences': experiences
          .map((item) => {
                'icon': item.icon,
                'title': item.title,
                'description': item.description,
              })
          .toList(),
      'tips': tips,
    };
  }

  static List<String> _stringList(Object? value) {
    if (value is List) {
      return value.whereType<String>().toList();
    }
    return const [];
  }
}
