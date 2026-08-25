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
    );
  }
}

/// 就诊流程步骤
class ProcessStep {
  final String step;
  final String description;

  const ProcessStep({required this.step, required this.description});
}
