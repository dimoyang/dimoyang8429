class MedicalService {
  final String id;
  final String nameEn;
  final String nameDe;
  final String nameFr;

  /// 中文名称（当前应用以中文为主要语言）
  final String nameZh;

  /// 医院名称（当前以中文提供）
  final String hospital;

  /// 医院等级标签，如"三级甲等"
  final String hospitalLevel;
  final double basePrice;
  final String currency;
  final String category; // surgery, wellness, dental, etc.

  /// 分类中文名，如"骨科"
  final String categoryLabel;
  final int durationDays;
  final String imageUrl;

  /// 服务简介（当前以中文提供）
  final String intro;

  /// 英文简介（后端 description_en）
  final String introEn;

  /// 服务亮点列表（当前以中文提供）
  final List<String> highlights;

  /// 就诊流程（当前以中文提供）
  final List<ProcessStep> process;

  MedicalService({
    required this.id,
    required this.nameEn,
    required this.nameDe,
    required this.nameFr,
    required this.nameZh,
    required this.hospital,
    this.hospitalLevel = '三级甲等',
    required this.basePrice,
    this.currency = 'EUR',
    required this.category,
    required this.categoryLabel,
    required this.durationDays,
    required this.imageUrl,
    this.intro = '',
    this.introEn = '',
    this.highlights = const [],
    this.process = const [],
  });

  /// 格式化的起步价格字符串
  String get priceFrom => '$currency $basePrice';

  // 根据当前语言获取名称
  String getName(String languageCode) {
    switch (languageCode) {
      case 'zh':
        return nameZh.isNotEmpty ? nameZh : nameEn;
      case 'de':
        return nameDe;
      case 'fr':
        return nameFr;
      default:
        return nameEn;
    }
  }

  /// 根据当前语言获取简介
  String getIntro(String languageCode) {
    if (languageCode == 'zh') {
      return intro;
    }
    return introEn.isNotEmpty ? introEn : intro;
  }

  // 从 JSON 创建对象
  factory MedicalService.fromJson(Map<String, dynamic> json) {
    return MedicalService(
      id: json['id'] ?? '',
      nameEn: json['name_en'] ?? '',
      nameDe: json['name_de'] ?? json['name_en'] ?? '',
      nameFr: json['name_fr'] ?? json['name_en'] ?? '',
      nameZh: json['name_zh'] ?? '',
      hospital: json['hospital'] ?? '',
      hospitalLevel: json['hospital_level'] ?? '三级甲等',
      basePrice: (json['base_price'] ?? 0).toDouble(),
      currency: json['currency'] ?? 'EUR',
      category: json['category'] ?? '',
      categoryLabel: json['category_label'] ?? '',
      durationDays: json['duration_days'] ?? 0,
      imageUrl: json['image_url'] ?? '',
      intro: json['intro'] ?? '',
      introEn: json['intro_en'] ?? '',
      highlights: List<String>.from(json['highlights'] as List? ?? const []),
      process: (json['process'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (step) => ProcessStep(
              step: step['step'] as String? ?? '',
              description: step['description'] as String? ?? '',
            ),
          )
          .toList(),
    );
  }

  /// 从后端 PackageResponse JSON 映射（后端无德/法译名，回退英文）。
  factory MedicalService.fromPackage(
    Map<String, dynamic> pkg, {
    String hospitalName = '',
    String hospitalLevel = '',
  }) {
    final name = pkg['name'] as String? ?? '';
    final nameEn = pkg['name_en'] as String? ?? name;
    final category = pkg['category'] as String? ?? '';
    return MedicalService(
      id: pkg['id'].toString(),
      nameEn: nameEn,
      nameDe: nameEn,
      nameFr: nameEn,
      nameZh: name,
      hospital: hospitalName,
      hospitalLevel: hospitalLevel.isNotEmpty ? hospitalLevel : '三级甲等',
      basePrice: (pkg['price'] as num? ?? 0).toDouble(),
      currency: pkg['currency'] as String? ?? 'CNY',
      category: category,
      categoryLabel: category,
      durationDays: pkg['duration_days'] as int? ?? 1,
      imageUrl: pkg['image_url'] as String? ?? '',
      intro: pkg['description'] as String? ?? '',
      introEn: pkg['description_en'] as String? ?? '',
    );
  }
}

/// 就诊流程步骤
class ProcessStep {
  final String step;
  final String description;

  const ProcessStep({required this.step, required this.description});
}
