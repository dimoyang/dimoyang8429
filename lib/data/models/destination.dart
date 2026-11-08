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
/// [contentLanguage] 记录名称/简介等文本来自后端哪种语言：
/// 请求 `lang=de|fr` 时后端会返回对应译文，缓存后也能按语言正确展示；
/// `null` 表示未指定语言（内置样例或旧缓存），沿用中文主名 + 英文名旧行为。
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
  final String? contentLanguage;

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
    this.contentLanguage,
  });

  /// 根据当前语言获取名称。
  ///
  /// 数据按某语言拉取时（[contentLanguage] 非空），若与界面语言一致则直接
  /// 使用后端返回的译文（de/fr 即为此路径）；不一致说明刚切换语言、刷新
  /// 还未完成或失败，没有对应译文，回退英文名而不是残留上一语言的名称。
  /// 未指定语言时保持既有行为：中文取主名，其他语言取英文名。
  String getName(String languageCode) {
    final lang = _baseLanguage(languageCode);
    final dataLang = contentLanguage;
    if (dataLang == null) {
      return lang == 'zh' ? name : nameEn;
    }
    if (lang == dataLang) {
      return name;
    }
    return nameEn.isNotEmpty ? nameEn : name;
  }

  static String _baseLanguage(String languageCode) {
    final separator = languageCode.indexOf(RegExp('[-_]'));
    final base =
        separator == -1 ? languageCode : languageCode.substring(0, separator);
    return base.toLowerCase();
  }

  static String? _normalizeLanguage(String? value) {
    if (value == null || value.isEmpty) {
      return null;
    }
    return _baseLanguage(value);
  }

  /// 从后端 /api/v1/destinations 响应解析。
  ///
  /// [lang] 为本次请求传给后端的语言；缓存恢复时不传，改为读取
  /// `content_language`，保证缓存数据仍能按语言展示。
  factory Destination.fromJson(Map<String, dynamic> json, {String? lang}) {
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
      contentLanguage: _normalizeLanguage(
        lang ??
            (json['content_language'] is String
                ? json['content_language'] as String
                : null),
      ),
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
      if (contentLanguage != null) 'content_language': contentLanguage!,
    };
  }

  static List<String> _stringList(Object? value) {
    if (value is List) {
      return value.whereType<String>().toList();
    }
    return const [];
  }
}
